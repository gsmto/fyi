#!/usr/bin/env python3
"""Validate or upsert one brief; stdlib only, no network or credentials."""
import argparse, copy, datetime, ipaddress, json, pathlib, re
from urllib.parse import urlsplit
ROOT = pathlib.Path(__file__).resolve().parents[1]

def read(p):
    return json.loads(p.read_text(encoding='utf-8'))

def write(p, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def require(ok, message):
    if not ok: raise ValueError(message)

def valid_http_url(value, *, https_only=False):
    """Check complete public-link syntax, without DNS or network requests."""
    # Check the original string first: urlsplit can silently strip tabs/newlines.
    # In a raw regex, \s is whitespace; \\s would instead match a literal backslash/s.
    if not isinstance(value, str) or not re.fullmatch(
        r'https?://[^\s\x00-\x1f\x7f\\<>"`{}|^]+', value, re.IGNORECASE
    ):
        return False
    if re.search(r'%(?![0-9a-fA-F]{2})', value):
        return False
    try:
        parts = urlsplit(value)
        if parts.scheme not in (('https',) if https_only else ('http', 'https')):
            return False
        if not parts.hostname or parts.username is not None or parts.password is not None:
            return False
        # Also reject junk after a bracketed host and empty/non-numeric ports.
        if not re.fullmatch(r'(?:\[[0-9a-fA-F:.]+\]|[^:\[\]]+)(?::[0-9]+)?', parts.netloc):
            return False
        if parts.port is not None and not 1 <= parts.port <= 65535:
            return False
        host = parts.hostname
        if parts.netloc.startswith('['):
            ipaddress.IPv6Address(host)
        else:
            host = host.encode('idna').decode('ascii')
            host = host[:-1] if host.endswith('.') else host
            if len(host) > 253 or not all(
                re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', label, re.IGNORECASE)
                for label in host.split('.')
            ):
                return False
            if re.fullmatch(r'[0-9]+(?:\.[0-9]+){3}', host):
                ipaddress.IPv4Address(host)
    except (ValueError, UnicodeError):
        return False
    return True

def validate_brief(b, cid, month):
    require(isinstance(b, dict), 'brief must be an object')
    for k in ['id','collectionId','date','title','summary','analysis','rawText','completeness','sourceConversation','provenance']:
        require(isinstance(b.get(k), str), 'missing string: ' + k)
    require(re.fullmatch(r'\d{4}-\d{2}-\d{2}', b['date']), 'invalid date format')
    datetime.date.fromisoformat(b['date'])
    require(b['date'][:7] == month and b['collectionId'] == cid, 'month/collection mismatch')
    require(b['id'] == cid + '-' + b['date'], 'unstable brief ID')
    require(bool(b['title'].strip()), 'empty title')
    require(b['completeness'] in ['full','partial','summary'], 'invalid completeness')
    require(b['completeness'] != 'full' or bool(b['rawText'].strip()), 'full brief missing rawText')
    require('score' in b and (b['score'] is None or type(b['score']) is int and 1 <= b['score'] <= 5), 'invalid score')
    require(isinstance(b.get('items'),list) and len(b['items']) <= 100, 'invalid items')
    ids = set()
    for i in b['items']:
        for k in ['id','title','category','summary','analysis']:
            require(isinstance(i.get(k),str), 'missing item string: '+k)
        require(i['id'].startswith(b['id']+'-') and i['id'] not in ids, 'duplicate/unscoped item ID')
        ids.add(i['id'])
        require('importance' in i and (i['importance'] is None or type(i['importance']) is int and 1 <= i['importance'] <= 5), 'invalid importance')
        require(isinstance(i.get('tags'),list) and all(isinstance(t,str) for t in i['tags']), 'invalid tags')
        require(isinstance(i.get('sources'),list), 'invalid sources')
        for s in i['sources']:
            require(isinstance(s, dict) and isinstance(s.get('title'),str) and valid_http_url(s.get('url')), 'invalid source URL')

        images = i.get('images', [])
        require(isinstance(images, list) and len(images) <= 5, 'invalid images')
        for image in images:
            require(isinstance(image, dict), 'image must be an object')
            require(valid_http_url(image.get('url'), https_only=True), 'invalid image URL')
            require(isinstance(image.get('alt'), str) and 1 <= len(image['alt']) <= 500, 'invalid image alt')
            require('sourceUrl' not in image or valid_http_url(image['sourceUrl']), 'invalid image source URL')
            require('caption' not in image or isinstance(image['caption'], str) and len(image['caption']) <= 1000, 'invalid image caption')

def catalog():
    c=read(ROOT/'catalog.json')
    require(c.get('schemaVersion') == 1 and c.get('timezone') == 'Asia/Shanghai', 'invalid catalog')
    categories={x['id'] for x in c['categories']}
    require(len(categories)==len(c['categories']), 'duplicate category')
    ids=set();paths=set()
    for col in c['collections']:
        require(col['id'] not in ids and col['path'] not in paths, 'duplicate collection/path')
        require(col['categoryId'] in categories, 'unknown category')
        require(re.fullmatch(r'content/[a-z0-9_-]+(?:/[a-z0-9_-]+)+',col['path']), 'invalid path')
        ids.add(col['id']);paths.add(col['path'])
    return c

def validate():
    total=items=0; all_ids=set()
    for col in catalog()['collections']:
        base=ROOT/col['path'];idx=read(base/'index.json')
        require(idx['schemaVersion']==1 and idx['collectionId']==col['id'], 'index mismatch')
        paths=set();months=set()
        for shard in idx['shards']:
            month=shard['month'];path=shard['path']
            require(re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])',month), 'invalid month')
            require(path==month.replace('-','/')+'.json' and path not in paths and month not in months, 'invalid/duplicate shard')
            paths.add(path);months.add(month)
            m=read(base/path)
            require(m['schemaVersion']==1 and m['collectionId']==col['id'] and m['month']==month, 'shard mismatch')
            require(shard['briefCount']==len(m['briefs']) and shard['itemCount']==sum(len(b['items']) for b in m['briefs']), 'index counts mismatch')
            require(len(m['briefs'])<=31, 'too many daily briefs')
            for b in m['briefs']:
                validate_brief(b,col['id'],month)
                require(b['id'] not in all_ids, 'duplicate brief ID');all_ids.add(b['id'])
                total+=1;items+=len(b['items'])
        actual={p.relative_to(base).as_posix() for p in base.glob('[0-9][0-9][0-9][0-9]/*.json')}
        require(actual==paths, 'unindexed or missing month file')
    return {'briefs':total,'items':items}

def upsert(path):
    validate()
    b=read(pathlib.Path(path));cid=b.get('collectionId');month=b.get('date','')[:7]
    col=next((c for c in catalog()['collections'] if c['id']==cid),None)
    require(col is not None,'unregistered collection')
    validate_brief(b,cid,month)
    base=ROOT/col['path'];rel=month.replace('-','/')+'.json';target=base/rel
    idx=read(base/'index.json')
    m=read(target) if target.exists() else {'schemaVersion':1,'collectionId':cid,'month':month,'briefs':[]}
    old=next((x for x in m['briefs'] if x['id']==b['id']),None)
    require(not old or old['completeness']!='full' or b['completeness']=='full','cannot downgrade full original')
    if old==b:return {'unchanged':True}
    before=(target.read_bytes() if target.exists() else None,(base/'index.json').read_bytes())
    now=datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00','Z')
    m['briefs']=sorted([x for x in m['briefs'] if x['id']!=b['id']]+[b],key=lambda x:x['date'],reverse=True);m['updatedAt']=now
    shard={'month':month,'path':rel,'briefCount':len(m['briefs']),'itemCount':sum(len(x['items']) for x in m['briefs'])}
    idx['shards']=sorted([s for s in idx['shards'] if s['month']!=month]+[shard],key=lambda s:s['month'],reverse=True);idx['updatedAt']=now
    try:
        write(target,m);write(base/'index.json',idx);result=validate()
    except Exception:
        if before[0] is None:target.unlink(missing_ok=True)
        else:target.write_bytes(before[0])
        (base/'index.json').write_bytes(before[1]);raise
    return {**result,'files':[target.relative_to(ROOT).as_posix(),(base/'index.json').relative_to(ROOT).as_posix()]}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['validate','upsert']);p.add_argument('brief',nargs='?');a=p.parse_args()
    try:
        if a.command=='upsert' and not a.brief:p.error('upsert requires one brief JSON file')
        print(json.dumps(validate() if a.command=='validate' else upsert(a.brief),ensure_ascii=False))
    except (ValueError,KeyError,TypeError,OSError) as e:p.exit(1,str(e)+'\n')
