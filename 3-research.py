#!/usr/bin/env python3
"""Connector research workbench. No dependencies; no credentials required for replay.

Sources are untrusted data, never commands. This program only reads public HTTPS
pages from a reviewed manifest. It never signs in, creates accounts or calls app
business APIs. Candidate labels are review hints, not verified findings.
"""
from __future__ import annotations
import argparse, collections, csv, datetime as dt, hashlib, html, ipaddress, json
import pathlib, re, socket, time, urllib.error, urllib.parse, urllib.request
from html.parser import HTMLParser
ROOT = pathlib.Path(__file__).resolve().parent


def read_json(path):
    return json.loads(pathlib.Path(path).read_text(encoding='utf-8'))


def write_json(path, obj):
    path = pathlib.Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


class TextOnly(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts = []; self.hidden = 0
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'noscript'): self.hidden += 1
        if tag in ('p', 'div', 'li', 'h1', 'h2', 'h3', 'br', 'tr'): self.parts.append('\n')
    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript'): self.hidden = max(0, self.hidden-1)
    def handle_data(self, data):
        if not self.hidden: self.parts.append(data)
    def text(self):
        return '\n'.join(re.sub(r'\s+', ' ', x).strip() for x in ''.join(self.parts).splitlines() if x.strip())


def public_url(url):
    """Reject credentials, non-HTTPS destinations and private/local IPs."""
    p = urllib.parse.urlsplit(url)
    if p.scheme != 'https' or not p.hostname or p.username or p.password or p.port not in (None, 443):
        raise ValueError('Public HTTPS URL required')
    for info in socket.getaddrinfo(p.hostname, 443):
        if not ipaddress.ip_address(info[4][0]).is_global:
            raise ValueError('Private or non-global destination rejected')
    return url


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        public_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


LAST_HOST = {}

def fetch(url, timeout=20):
    public_url(url)
    host = urllib.parse.urlsplit(url).hostname
    time.sleep(max(0, 1.0 - (time.monotonic() - LAST_HOST.get(host, 0))))
    LAST_HOST[host] = time.monotonic()
    request = urllib.request.Request(url, headers={'User-Agent':'ConnectorReadinessResearch/1.0 (public documentation only)', 'Accept':'text/html,text/plain,application/json'})
    opener = urllib.request.build_opener(SafeRedirect())
    with opener.open(request, timeout=timeout) as response:
        raw = response.read(2_000_001)
        if len(raw) > 2_000_000: raise ValueError('Source exceeds 2 MB cap')
        text = raw.decode('utf-8', errors='replace')
        if 'html' in response.headers.get('Content-Type',''):
            parser = TextOnly(); parser.feed(text); text = parser.text()
        return {'url':url, 'final_url':response.url, 'status':'fetched', 'http_status':response.status,
                'fetched_at':now(), 'content_quality':'sparse' if len(text.strip())<200 else 'not_semantically_verified', 'sha256':hashlib.sha256(raw).hexdigest(), 'text':text}


def refresh(args):
    """One bounded fetch per unique reviewed source; failures become review items."""
    rows = read_json(ROOT/'data/reviewed.json')
    urls = sorted({e['url'] for row in rows for e in row['evidence']})
    if args.limit: urls = urls[:args.limit]
    if getattr(args, 'missing_only', False):
        urls = [u for u in urls if not (ROOT/'cache'/(hashlib.sha256(u.encode()).hexdigest()[:20]+'.json')).exists()]
    results = []
    for index,url in enumerate(urls,1):
        key = hashlib.sha256(url.encode()).hexdigest()[:20]
        target = ROOT/'cache'/f'{key}.json'
        if target.exists() and not args.force:
            item = read_json(target)
        else:
            try: item = fetch(url)
            except (OSError,ValueError,urllib.error.URLError) as exc:
                item = {'url':url,'status':'fetch_failed','fetched_at':now(),'error':str(exc)[:300],'text':''}
            write_json(target,item)
        results.append(item)
        print(f"{index}/{len(urls)} {item['status']}: {url}")
    write_json(ROOT/'runs/fetch_index.json', [{k:v for k,v in r.items() if k!='text'} for r in results])
    print('Fetch results saved. A fetched page is not a verified claim.')


AUTH_PATTERNS = {
 'OAuth2':r'\boauth\s*2(?:\.0)?\b',
 'API key':r'\bapi[ _-]?keys?\b|\bx-api-key\b',
 'Basic':r'\b(?:http\s+)?basic\s+auth(?:entication)?\b',
 'Bearer token':r'\bbearer\s+(?:token|auth)|authorization\s*:\s*bearer',
 'Personal access token':r'\bpersonal access tokens?\b',
 'Signed key':r'\bHMAC\b|\bEd25519\b|\bRSA\b'
}
GATE_PATTERNS = {
 'sandbox':r'\bsandbox\b|\btest account\b',
 'paid':r'\bpaid plan\b|\bpaid tier\b|\bsubscription\b',
 'admin':r'\badmin(?:istrator)?\b',
 'partner':r'\bpartner(?:ship)?\b',
 'sales':r'\bcontact sales\b|\bcontact our sales\b',
 'review':r'\bapproval\b|\bapp review\b|\bverification\b',
 'free':r'\bfree plan\b|\bfree tier\b|\bno charge\b'
}


def snippets(text, pattern, limit=3):
    out=[]
    for m in re.finditer(pattern,text,re.I):
        out.append(re.sub(r'\s+',' ',text[max(0,m.start()-90):min(len(text),m.end()+160)]))
        if len(out)==limit: break
    return out


def candidates(args):
    """Conservative deterministic first pass; no semantic inference or decisions."""
    reviewed = read_json(ROOT/'data/reviewed.json')
    result=[]
    for row in reviewed:
        texts=[]; sources=[]
        for evidence in row['evidence']:
            key=hashlib.sha256(evidence['url'].encode()).hexdigest()[:20]
            path=ROOT/'cache'/f'{key}.json'
            if path.exists():
                item=read_json(path)
                if item['status']=='fetched' and len(item.get('text','').strip())>=200: texts.append(item['text']); sources.append(evidence['url'])
        text='\n'.join(texts)
        auth=[k for k,p in AUTH_PATTERNS.items() if re.search(p,text,re.I)]
        gates=[k for k,p in GATE_PATTERNS.items() if re.search(p,text,re.I)]
        result.append({'id':row['id'],'name':row['name'],'source_count':len(sources),'sources':sources,
          'auth_candidates':auth,'gate_candidates':gates,'mcp_mentioned':bool(re.search(r'\bMCP\b|Model Context Protocol',text,re.I)),
          'candidate_context':{k:snippets(text,p,1) for k,p in AUTH_PATTERNS.items() if k in auth},
          'status':'needs_evidence_review' if len(text.strip())>=200 else 'needs_browser_or_source_check',
          'warning':'Keyword mentions can describe an upstream service or a different product; not verified.'})
    target=ROOT/args.output
    if target.exists() and not args.overwrite: raise SystemExit('Snapshot exists. Use a new --output, or explicitly --overwrite.')
    write_json(target,{'created_at':now(),'method':'deterministic keyword triage, not semantic verification','rows':result})
    print(f'Saved {len(result)} candidate rows to {target.relative_to(ROOT)}')


def validate_rows(rows):
    errors=[]
    if len(rows)!=100: errors.append(f'Expected 100 apps, found {len(rows)}')
    if sorted(r.get('id',0) for r in rows)!=list(range(1,101)): errors.append('IDs must be unique and exactly 1..100')
    required=['id','name','category','description','auth_methods','access_gates','access_summary','api_surface','mcp_status','buildability','blocker','evidence','confidence','checked_at','readiness_stage','routing_reason','next_action']
    inputs={r['id']:r for r in read_json(ROOT/'data/apps.json')}
    for row in rows:
        ident=row.get('id','?')
        for field in required:
            if field not in row or row[field] is None or row[field]=='': errors.append(f'{ident}: missing {field}')
        if row.get('id') in inputs and row.get('name')!=inputs[row['id']]['name']: errors.append(f'{ident}: app name changed')
        if not isinstance(row.get('auth_methods'),list): errors.append(f'{ident}: auth must be an array')
        if not isinstance(row.get('access_gates'),list): errors.append(f'{ident}: gates must be an array')
        if not row.get('evidence'): errors.append(f'{ident}: no evidence')
        for evidence in row.get('evidence',[]):
            p=urllib.parse.urlsplit(evidence.get('url',''))
            if p.scheme!='https' or not p.hostname: errors.append(f'{ident}: invalid evidence URL')
    return errors


def decision(row):
    """Reviewed routing for a scoped prototype, not production certification."""
    allowed={'Prototype path','Validate','Access work','Local adapter','Resolve identity'}
    stage=row.get('readiness_stage','Validate')
    if stage not in allowed: raise ValueError('Unknown readiness stage')
    return stage


def metrics(rows):
    counts=lambda values:dict(collections.Counter(values).most_common())
    def families(row):
        text=' '.join(row['auth_methods']).lower(); out=[]
        for label,pattern in [('OAuth',r'oauth'),('API key / personal token',r'api.key|api.token|personal.access.token|personal.api.token|bot.token|internal.connection|workspace.access.token|private.app|private.integration'),('Basic',r'basic'),('Signed key / JWT',r'signed|hmac|rsa|ed25519|jwt'),('Local / no auth',r'none.*local|none for the core'),('Unknown / conditional',r'unknown|reference only')]:
            if re.search(pattern,text): out.append(label)
        return out
    return {'apps':len(rows),'categories':counts(r['category'] for r in rows),
      'readiness':counts(decision(r) for r in rows),'auth_families':counts(a for r in rows for a in families(r)),
      'confidence':counts(r['confidence'] for r in rows),
      'evidence_urls':len({e['url'] for r in rows for e in r['evidence']}),
      'rows_with_evidence':sum(bool(r['evidence']) for r in rows),
      'scope':'Documentation research only. Auth families are broad, multi-label, and include API plus MCP methods; counts may sum above 100.'}


def replay(args):
    rows=read_json(ROOT/'data/reviewed.json'); errors=validate_rows(rows)
    if errors: raise SystemExit('\n'.join(errors))
    write_json(ROOT/'output/metrics.json',metrics(rows))
    write_json(ROOT/'output/readiness.json',[dict(r,stage=decision(r)) for r in rows])
    fields=['id','name','category','description','auth_methods','access_gates','access_summary','api_surface','mcp_status','buildability','stage','blocker','routing_reason','next_action','confidence','checked_at','evidence_urls']
    with (ROOT/'output/readiness.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for r in rows:
            d={k:r.get(k,'') for k in fields};d['stage']=decision(r)
            d['auth_methods']='; '.join(r['auth_methods']);d['access_gates']='; '.join(r['access_gates'])
            d['evidence_urls']='; '.join(e['url'] for e in r['evidence']);writer.writerow(d)
    print(json.dumps(metrics(rows),indent=2))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('refresh',help='Fetch reviewed public evidence URLs, without account access')
    a.add_argument('--limit',type=int);a.add_argument('--force',action='store_true');a.add_argument('--missing-only',action='store_true');a.set_defaults(func=refresh)
    a=sub.add_parser('candidates',help='Save an immutable first-pass triage snapshot from the cache')
    a.add_argument('--output',default='runs/first_pass.json');a.add_argument('--overwrite',action='store_true');a.set_defaults(func=candidates)
    a=sub.add_parser('replay',help='Validate reviewed data and recompute readiness, CSV and metrics offline');a.set_defaults(func=replay)
    args=p.parse_args();args.func(args)

if __name__=='__main__': main()
