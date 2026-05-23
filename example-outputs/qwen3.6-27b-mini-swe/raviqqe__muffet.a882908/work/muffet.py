#!/usr/bin/env python3
import sys, os, re, json, threading, ssl
from collections import namedtuple
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.request import Request, build_opener, ProxyHandler, HTTPSHandler
from urllib.error import HTTPError, URLError
from concurrent.futures import ThreadPoolExecutor, as_completed

VERSION = "2.11.1"

HELP_TEXT = (
"Usage:\n"
"  executable [options] <url>\n"
"\n"
"Application Options:\n"
"      --accepted-status-codes=<codes>       Accepted HTTP response status codes\n"
"                                            (e.g. '200..300,403') (default:\n"
"                                            200..300)\n"
"  -b, --buffer-size=<size>                  HTTP response buffer size in bytes\n"
"                                            (default: 4096)\n"
"  -c, --max-connections=<count>             Maximum number of HTTP connections\n"
"                                            (default: 512)\n"
"      --max-connections-per-host=<count>    Maximum number of HTTP connections\n"
"                                            per host (default: 512)\n"
"      --max-response-body-size=<size>       Maximum response body size to read\n"
"                                            (default: 10000000)\n"
"  -e, --exclude=<pattern>...                Exclude URLs matched with given\n"
"                                            regular expressions\n"
"  -i, --include=<pattern>...                Include URLs matched with given\n"
"                                            regular expressions\n"
"      --follow-robots-txt                   Follow robots.txt when scraping\n"
"                                            pages\n"
"      --follow-sitemap-xml                  Scrape only pages listed in\n"
"                                            sitemap.xml (deprecated)\n"
"      --header=<header>...                  Custom headers\n"
"  -f, --ignore-fragments                    Ignore URL fragments\n"
"      --max-retries=<count>                 Maximum retry count for network\n"
"                                            errors (default: 0)\n"
"      --dns-resolver=<address>              Custom DNS resolver\n"
"      --format=[text|json|junit]            Output format (default: text)\n"
"      --json                                Output results in JSON (deprecated)\n"
"      --experimental-verbose-json           Include successful results in JSON\n"
"                                            (deprecated)\n"
"      --junit                               Output results as JUnit XML file\n"
"                                            (deprecated)\n"
"  -r, --max-redirections=<count>            Maximum number of redirections\n"
"                                            (default: 64)\n"
"      --rate-limit=<rate>                   Max requests per second\n"
"  -t, --timeout=<seconds>                   Timeout for HTTP requests in\n"
"                                            seconds (default: 10)\n"
"  -v, --verbose                             Show successful results too\n"
"      --proxy=<host>                        HTTP proxy host\n"
"      --skip-tls-verification               Skip TLS certificate verification\n"
"      --one-page-only                       Only check links found in the given\n"
"                                            URL\n"
"      --color=[auto|always|never]           Color output (default: auto)\n"
"  -h, --help                                Show this help\n"
"      --version                             Show version\n"
)

def read_val(argv, i):
    if i < len(argv) and '=' in argv[i] and len(argv[i]) > 1:
        eq = argv[i].find('=')
        return argv[i][eq+1:], i
    else:
        i += 1
        return argv[i] if i < len(argv) else '', i - 1

def parse_args(argv):
    r = dict(url=None, accepted_status_codes='200..300', buffer_size=4096,
             max_connections=512, max_connections_per_host=512,
             max_response_body_size=10000000, exclude=[], include=[],
             follow_robots_txt=False, follow_sitemap_xml=False, header=[],
             ignore_fragments=False, max_retries=0, dns_resolver=None,
             fmt='text', json_old=False, verbose_json=False, junit_old=False,
             max_redirections=64, rate_limit=0.0, timeout=10, verbose=False,
             proxy=None, skip_tls=False, one_page_only=False, color='auto',
             help=False, version=False)
    i, pos = 0, []
    while i < len(argv):
        a = argv[i]
        if a in ('-h', '--help'): r['help'] = True
        elif a == '--version': r['version'] = True
        elif a == '--accepted-status-codes' or a.startswith('--accepted-status-codes='):
            v, i = read_val(argv, i); r['accepted_status_codes'] = v
        elif a in ('-b', '--buffer-size') or a.startswith('--buffer-size='):
            v, i = read_val(argv, i); r['buffer_size'] = int(v)
        elif a in ('-c', '--max-connections') or a.startswith('--max-connections='):
            v, i = read_val(argv, i); r['max_connections'] = int(v)
        elif a == '--max-connections-per-host' or a.startswith('--max-connections-per-host='):
            v, i = read_val(argv, i); r['max_connections_per_host'] = int(v)
        elif a == '--max-response-body-size' or a.startswith('--max-response-body-size='):
            v, i = read_val(argv, i); r['max_response_body_size'] = int(v)
        elif a in ('-e', '--exclude') or a.startswith('--exclude='):
            v, i = read_val(argv, i); r['exclude'].append(v)
        elif a in ('-i', '--include') or a.startswith('--include='):
            v, i = read_val(argv, i); r['include'].append(v)
        elif a == '--follow-robots-txt': r['follow_robots_txt'] = True
        elif a == '--follow-sitemap-xml': r['follow_sitemap_xml'] = True
        elif a == '--header' or a.startswith('--header='):
            v, i = read_val(argv, i); r['header'].append(v)
        elif a in ('-f', '--ignore-fragments'): r['ignore_fragments'] = True
        elif a == '--max-retries' or a.startswith('--max-retries='):
            v, i = read_val(argv, i); r['max_retries'] = int(v)
        elif a == '--dns-resolver' or a.startswith('--dns-resolver='):
            v, i = read_val(argv, i); r['dns_resolver'] = v
        elif a == '--format' or a.startswith('--format='):
            v, i = read_val(argv, i); r['fmt'] = v
        elif a == '--json': r['json_old'] = True
        elif a == '--experimental-verbose-json': r['verbose_json'] = True
        elif a == '--junit': r['junit_old'] = True
        elif a in ('-r', '--max-redirections') or a.startswith('--max-redirections='):
            v, i = read_val(argv, i); r['max_redirections'] = int(v)
        elif a == '--rate-limit' or a.startswith('--rate-limit='):
            v, i = read_val(argv, i); r['rate_limit'] = float(v)
        elif a in ('-t', '--timeout') or a.startswith('--timeout='):
            v, i = read_val(argv, i); r['timeout'] = int(v)
        elif a in ('-v', '--verbose'): r['verbose'] = True
        elif a == '--proxy' or a.startswith('--proxy='):
            v, i = read_val(argv, i); r['proxy'] = v
        elif a == '--skip-tls-verification': r['skip_tls'] = True
        elif a == '--one-page-only': r['one_page_only'] = True
        elif a == '--color' or a.startswith('--color='):
            v, i = read_val(argv, i); r['color'] = v
        elif a.startswith('-'):
            print('flag provided but not defined:' + ' ' + a, file=sys.stderr)
            sys.exit(1)
        else:
            pos.append(a)
        i += 1
    if pos:
        r['url'] = pos[0]
        if len(pos) > 1:
            print('invalid number of arguments')
            sys.exit(1)
    return r

class LinkExtractor(HTMLParser):
    def __init__(self, base):
        super().__init__()
        self.base = base
        self.links = []
        self.base_href = None

    def handle_starttag(self, tag, attrs):
        ad = {}
        for n, v in attrs:
            if v is not None:
                ad[(n or '').lower()] = v
        if tag == 'base':
            self.base_href = ad.get('href')
            return
        if tag == 'a':
            if 'rel' in ad and 'nofollow' in ad['rel'].lower().split():
                return
            if 'href' in ad:
                self.links.append(ad['href'])
        elif tag == 'img' and 'src' in ad:
            self.links.append(ad['src'])
        elif tag == 'link' and 'href' in ad:
            self.links.append(ad['href'])
        elif tag == 'script' and 'src' in ad:
            self.links.append(ad['src'])
        elif tag == 'form' and 'action' in ad:
            self.links.append(ad['action'])
        elif tag == 'iframe' and 'src' in ad:
            self.links.append(ad['src'])
        elif tag == 'embed' and 'src' in ad:
            self.links.append(ad['src'])
        elif tag == 'source':
            if 'src' in ad:
                self.links.append(ad['src'])
            elif 'srcset' in ad:
                for p in ad['srcset'].split(','):
                    u = p.strip().split()[0]
                    if u:
                        self.links.append(u)
        elif tag == 'video':
            if 'src' in ad:
                self.links.append(ad['src'])
            if 'poster' in ad:
                self.links.append(ad['poster'])
        elif tag == 'audio' and 'src' in ad:
            self.links.append(ad['src'])
        elif tag == 'area' and 'href' in ad:
            self.links.append(ad['href'])
        elif tag == 'object' and 'data' in ad:
            self.links.append(ad['data'])
        elif tag == 'input' and ad.get('type', '').lower() == 'image' and 'src' in ad:
            self.links.append(ad['src'])

_SKIP = frozenset(('javascript:', 'mailto:', 'tel:', 'data:', 'git://', 'svn:'))

def resolve_href(base, href, base_href=None, ignore_frag=False):
    if not href or not href.strip():
        return None
    href = href.strip()
    lo = href.lower()
    for s in _SKIP:
        if lo.startswith(s):
            return None
    if lo.startswith('#'):
        return None
    if href.startswith('//'):
        p = urlparse(base)
        href = f'{p.scheme}:' + href
    if base_href:
        base = urljoin(base, base_href)
    r = urljoin(base, href)
    if ignore_frag:
        parts = list(urlparse(r))
        parts[4] = ''
        r = urlunparse(parts)
    return r

def same_host(url, host):
    try:
        return urlparse(url).hostname == host
    except:
        return False

def passes_filters(url, exc, inc):
    for p in exc:
        if p and re.search(p, url):
            return False
    if inc:
        for p in inc:
            if re.search(p, url):
                return True
        return False
    return True

def status_ok(code, codes):
    for part in codes.split(','):
        part = part.strip()
        if '..' in part:
            lo, hi = part.split('..')
            if int(lo) <= code <= int(hi):
                return True
        elif code == int(part):
            return True
    return False

def frag_key(url, ignore):
    if ignore and '#' in url:
        return url.split('#')[0]
    return url

def make_op(proxy, skip):
    o = build_opener()
    if proxy:
        o.add_handler(ProxyHandler({'http': proxy, 'https': proxy}))
    if skip:
        c = ssl.create_default_context()
        c.check_hostname = False
        c.verify_mode = ssl.CERT_NONE
        o.add_handler(HTTPSHandler(context=c))
    return o

def add_h(req, hl):
    for h in hl:
        if ':' in h:
            k, v = h.split(':', 1)
            req.add_header(k.strip(), v.strip())

def fetch_page(proxy, headers, skip, timeout, max_body, buf, url):
    try:
        o = make_op(proxy, skip)
        rq = Request(url)
        add_h(rq, headers)
        resp = o.open(rq, timeout=timeout)
        code = resp.getcode()
        raw = resp.read(max_body)
        resp.close()
        ct = ''
        try:
            ct = resp.headers.get('Content-Type', '')
        except:
            pass
        enc = 'utf-8'
        if 'charset=' in ct.lower():
            e = ct.lower().split('charset=')[-1].split(';')[0].strip()
            if e:
                enc = e
        return code, raw.decode(enc, errors='replace')
    except HTTPError as e:
        return e.code, ''
    except URLError as e:
        return None, str(e.reason)
    except Exception as e:
        return None, str(e)

def check_one(proxy, headers, skip, timeout, retries, max_body, buf, url):
    attempt = 0
    while attempt <= retries:
        try:
            o = make_op(proxy, skip)
            rq = Request(url)
            add_h(rq, headers)
            resp = o.open(rq, timeout=timeout)
            code = resp.getcode()
            sz = 0
            while sz < max_body:
                chunk = resp.read(min(buf, max_body - sz))
                if not chunk:
                    break
                sz += len(chunk)
            resp.close()
            return code, None
        except HTTPError as e:
            return e.code, None
        except URLError as e:
            err = str(e.reason)
            if attempt < retries:
                attempt += 1
                continue
            return None, err
        except Exception as e:
            err = str(e)
            if attempt < retries:
                attempt += 1
                continue
            return None, err
    return None, 'retries exhausted'

LCR = namedtuple('LCR', 'url status_or_error')

def process_single_page(page_url, hrefs, base_href, root_host, cfg):
    broken, ok, seen = [], [], set()
    for href in hrefs:
        resolved = resolve_href(page_url, href, base_href, cfg['ignore_fragments'])
        if resolved is None:
            continue
        if not same_host(resolved, root_host):
            continue
        if not passes_filters(resolved, cfg['exclude'], cfg['include']):
            continue
        k = frag_key(resolved, cfg['ignore_fragments'])
        if cfg['ignore_fragments']:
            if k in seen:
                continue
            seen.add(k)
        else:
            if resolved in seen:
                continue
            seen.add(resolved)
        status, err = check_one(cfg['proxy'], cfg['header'], cfg['skip_tls'],
                                cfg['timeout'], cfg['max_retries'],
                                cfg['max_response_body_size'], cfg['buffer_size'], resolved)
        if err:
            broken.append(LCR(resolved, err))
        elif not status_ok(status, cfg['accepted_status_codes']):
            broken.append(LCR(resolved, str(status)))
        else:
            ok.append(LCR(resolved, status))
    return broken, ok

def emit_junit(out, pu, brk, okl):
    total = len(brk) + len(okl)
    fails = len(brk)
    if total == 0:
        out.append(f'  <testsuite name="{pu}" tests="{total}" failures="{fails}" skipped="0"></testsuite>')
    else:
        out.append(f'  <testsuite name="{pu}" tests="{total}" failures="{fails}" skipped="0">')
        for lc in okl:
            out.append(f'    <testcase name="{lc.url}" classname="{pu}"></testcase>')
        for lc in brk:
            out.append(f'    <testcase name="{lc.url}" classname="{pu}">')
            out.append(f'      <failure message="{lc.status_or_error}"></failure>')
            out.append(f'    </testcase>')
        out.append(f'  </testsuite>')

def main():
    cfg = parse_args(sys.argv[1:])

    if cfg['help']:
        sys.stdout.write(HELP_TEXT)
        sys.exit(0)
    if cfg['version']:
        print(VERSION)
        sys.exit(0)
    if cfg['url'] is None:
        print('invalid number of arguments')
        sys.exit(1)

    fmt = cfg['fmt']
    if cfg['json_old']:
        fmt = 'json'
    if cfg['junit_old']:
        fmt = 'junit'

    root = cfg['url']
    if not root.startswith(('http://', 'https://')):
        root = 'http://' + root

    root_host = urlparse(root).hostname
    if not root_host:
        print('failed to fetch root page: missing port in address')
        sys.exit(1)

    rpath = urlparse(root).path
    if not rpath or rpath == '/':
        root = root.rstrip('/') + '/'

    code, body = fetch_page(cfg['proxy'], cfg['header'], cfg['skip_tls'],
                            cfg['timeout'], cfg['max_response_body_size'],
                            cfg['buffer_size'], root)
    if code is None:
        print(f'failed to fetch root page: {body}')
        sys.exit(1)
    if not status_ok(code, cfg['accepted_status_codes']):
        print(f'failed to fetch root page: {code}')
        sys.exit(1)

    if not body:
        if fmt == 'json':
            print('[]')
        elif fmt == 'junit':
            print('<?xml version="1.0" encoding="UTF-8"?>')
            print('<testsuites>')
            print(f'  <testsuite name="{root}" tests="0" failures="0" skipped="0"></testsuite>')
            print('</testsuites>')
        sys.exit(0)

    ext = LinkExtractor(root)
    ext.feed(body)
    bh = ext.base_href

    out_lock = threading.Lock()
    results_lock = threading.Lock()
    all_results = {}

    def put_line(ln):
        with out_lock:
            print(ln)

    def crawl_recursive():
        visited = {root}
        batch_list = [(root, ext, bh)]

        while batch_list:
            next_batch = []
            with ThreadPoolExecutor(max_workers=min(cfg['max_connections'], max(1, len(batch_list)))) as pool:
                futs = {}
                for (pu, pext, pbh) in batch_list:
                    f = pool.submit(process_single_page, pu, pext.links, pbh, root_host, cfg)
                    futs[f] = pu
                newly = []
                for f in as_completed(futs):
                    pu = futs[f]
                    try:
                        brk, ok = f.result()
                    except:
                        brk, ok = [], []
                    with results_lock:
                        all_results[pu] = (brk, ok)
                    if cfg['verbose'] and fmt == 'text':
                        put_line(pu)
                        for lc in ok:
                            put_line(f'\t{lc.status_or_error}\t{lc.url}')
                        for lc in brk:
                            put_line(f'\t{lc.status_or_error}\t{lc.url}')
                    for lc in ok:
                        c = frag_key(lc.url, cfg['ignore_fragments'])
                        need = False
                        with results_lock:
                            if c not in visited:
                                visited.add(c)
                                need = True
                        if need:
                            newly.append(c)
            for nd in newly:
                c2, b2 = fetch_page(cfg['proxy'], cfg['header'], cfg['skip_tls'],
                                    cfg['timeout'], cfg['max_response_body_size'],
                                    cfg['buffer_size'], nd)
                if c2 is not None and status_ok(c2, cfg['accepted_status_codes']) and b2:
                    e2 = LinkExtractor(nd)
                    e2.feed(b2)
                    next_batch.append((nd, e2, e2.base_href))
            batch_list = next_batch

    if cfg['one_page_only']:
        broken, ok = process_single_page(root, ext.links, bh, root_host, cfg)
        all_results[root] = (broken, ok)
    else:
        crawl_recursive()

    any_broken = False
    if fmt == 'text':
        if not cfg['verbose']:
            for pu, (broken, ok) in all_results.items():
                if broken:
                    any_broken = True
                    put_line(pu)
                    for lc in broken:
                        put_line(f'\t{lc.status_or_error}\t{lc.url}')
    elif fmt == 'json':
        vj = cfg['verbose'] or cfg['verbose_json']
        entries = []
        for pu in all_results:
            brk, ok = all_results[pu]
            links = []
            if vj:
                for lc in ok:
                    links.append({'url': lc.url, 'status': lc.status_or_error})
            for lc in brk:
                links.append({'url': lc.url, 'error': lc.status_or_error})
            if vj:
                entries.append({'url': pu, 'links': links})
            elif brk:
                entries.append({'url': pu, 'links': links})
                any_broken = True
        print(json.dumps(entries, separators=(',', ':')))
    elif fmt == 'junit':
        jl = ['<?xml version="1.0" encoding="UTF-8"?>', '<testsuites>']
        for pu in all_results:
            brk, ok = all_results[pu]
            if brk:
                any_broken = True
            emit_junit(jl, pu, brk, ok)
        jl.append('</testsuites>')
        print('\n'.join(jl))

    if cfg['verbose'] and fmt == 'text':
        any_broken = any(b for b, _ in all_results.values())
    sys.exit(1 if any_broken else 0)

if __name__ == '__main__':
    main()
