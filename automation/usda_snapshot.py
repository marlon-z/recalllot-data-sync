"""Fetch a validated, public USDA snapshot. No credentials or browser needed."""
import argparse
import datetime as dt
import gzip
import hashlib
import json
from pathlib import Path
import sys
import urllib.error
import urllib.parse
import urllib.request

URL = 'https://www.fsis.usda.gov/fsis/api/recall/v/1'
LIMIT = 25_000_000


def validate(rows):
    if not isinstance(rows,list) or not rows or any(not isinstance(r,dict) for r in rows):
        raise ValueError('The official API did not return a nonempty record list.')
    english=[r for r in rows if r.get('langcode')=='English']
    ids=set()
    for r in english:
        rid=r.get('field_recall_number')
        if not rid or rid in ids or not r.get('field_title') or not r.get('field_summary'):
            raise ValueError('USDA IDs or required full-text fields changed; previous snapshot retained.')
        ids.add(rid)
        if urllib.parse.urlparse(r.get('field_recall_url','')).hostname not in ('www.fsis.usda.gov','fsis.usda.gov'):
            raise ValueError('A recall URL is not on the official USDA host.')
        dt.date.fromisoformat(r.get('field_recall_date',''))
    if not english:
        raise ValueError('No complete English recall records were returned.')
    return sorted(english,key=lambda r:r['field_recall_number'])


def write_snapshot(rows,folder,*,now=None):
    english=validate(rows)
    folder=Path(folder)
    folder.mkdir(parents=True,exist_ok=True)
    previous=folder/'manifest.json'
    if previous.exists():
        old=json.loads(previous.read_text())
        if len(english)<old['record_count']*.9:
            raise ValueError('USDA record count dropped more than 10%; review before replacing data.')
    raw=json.dumps(english,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
    data=gzip.compress(raw,mtime=0)
    manifest={'schema_version':1,'source_url':URL,
              'fetched_at':now or dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
              'record_count':len(english),'sha256':hashlib.sha256(raw).hexdigest(),
              'compressed_sha256':hashlib.sha256(data).hexdigest(),
              'upstream_date':max(r.get('field_last_modified_date') or r['field_recall_date'] for r in english),
              'file':'usda.json.gz'}
    for name,body in (('usda.json.gz',data),('manifest.json',json.dumps(manifest,indent=2).encode())):
        temp=folder/(name+'.tmp')
        temp.write_bytes(body)
        temp.replace(folder/name)
    return manifest


def fetch_snapshot(folder):
    request=urllib.request.Request(URL,headers={'User-Agent':'RecallLot-data-sync/1.0 (official public recall data)','Accept':'application/json'})
    with urllib.request.urlopen(request,timeout=40) as response:
        raw=response.read(LIMIT+1)
        if len(raw)>LIMIT:raise ValueError('Official response exceeded the supported size.')
    return write_snapshot(json.loads(raw.decode('utf-8-sig')),folder)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default='snapshot')
    args=parser.parse_args()
    try:
        result=fetch_snapshot(args.output)
        print(json.dumps(result,indent=2))
    except urllib.error.HTTPError as exc:
        print('Official USDA endpoint returned HTTP '+str(exc.code)+'. No snapshot was replaced.',file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(type(exc).__name__+': '+str(exc)[:180],file=sys.stderr)
        sys.exit(1)
