#!/usr/bin/env python3
"""htmlq - A command-line utility for querying HTML documents with CSS selectors."""

import sys
import os
import re
from html.parser import HTMLParser
from html import entities
from urllib.parse import urljoin

VERSION_STR = "htmlq 0.4.0"

class Node:
    def __init__(self, tag=None, attrs=None, text=None):
        self.tag = tag
        self.attrs = attrs or []
        self.children = []
        self.text = text
        self.parent = None
        self._order = 0
    def is_element(self):
        return self.tag is not None

BLOCK_ELEMENTS = {
    "address","article","aside","blockquote","br","caption","dd","details",
    "dialog","div","dl","dt","fieldset","figcaption","figure","footer","form",
    "h1","h2","h3","h4","h5","h6","header","hgroup","hr","legend","li",
    "main","menu","nav","ol","p","pre","section","summary","table","tbody",
    "td","tfoot","th","thead","tr","ul",
}
HTML_VOID_ELEMENTS = {
    "area","base","br","col","embed","hr","img","input",
    "link","meta","param","source","track","wbr",
}
AUTO_CLOSE_IN = {
    "li":("li",), "optgroup":("optgroup",), "option":("option","optgroup"),
    "tr":("th","td","tr"), "td":("td","th"), "th":("td","th"),
    "dt":("dt","dd"), "dd":("dt","dd"), "p":("p",),
    "rp":("rp","rt"), "rt":("rp","rt"),
}

class DOMBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node(tag="__root__")
        self.current = self.root
        self.stack = []
    def _add_child(self, node):
        self.current.children.append(node)
        node.parent = self.current
    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        self._auto_close(tag)
        node = Node(tag=tag, attrs=list(attrs))
        self._add_child(node)
        if tag not in HTML_VOID_ELEMENTS:
            self.stack.append((tag, node))
            self.current = node
    def _auto_close(self, tag):
        if tag in AUTO_CLOSE_IN:
            while self.stack:
                if self.stack[-1][0] in AUTO_CLOSE_IN[tag]:
                    self.stack.pop()
                    self.current = self.stack[-1][1] if self.stack else self.root
                else:
                    break
    def handle_endtag(self, tag):
        tag = tag.lower()
        while self.stack:
            if self.stack[-1][0] == tag:
                self.stack.pop()
                self.current = self.stack[-1][1] if self.stack else self.root
                return
            self.stack.pop()
            self.current = self.stack[-1][1] if self.stack else self.root
    def handle_data(self, data):
        self._add_child(Node(text=data))
    def handle_entityref(self, name):
        self._add_child(Node(text=entities.html5.get(name, f"&{name};")))
    def handle_charref(self, name):
        try:
            code = int(name[1:], 16) if name.lower().startswith("x") else int(name)
            self._add_child(Node(text=chr(code)))
        except:
            self._add_child(Node(text=f"&#{name};"))
    def handle_comment(self, data): pass
    def handle_decl(self, decl): pass
    def handle_pi(self, data): pass

def parse_html(s):
    b = DOMBuilder()
    try: b.feed(s)
    except: pass
    return b.root

def force_html_structure(document):
    rc = list(document.children)
    if not rc:
        return document
    html_node = None
    for c in rc:
        if c.is_element() and c.tag == "html":
            html_node = c
            break
    if html_node is None:
        html_node = Node(tag="html")
        html_node.parent = document
        document.children = [html_node]
        for c in rc:
            c.parent = html_node
        html_node.children.extend(rc)

    # Find head and body
    h = b = None
    for c in html_node.children:
        if c.is_element():
            if c.tag == "head" and h is None: h = c
            elif c.tag == "body" and b is None: b = c

    if h is None:
        eh = Node(tag="head")
        eh.parent = html_node
        if b is not None:
            idx = html_node.children.index(b)
            html_node.children.insert(idx, eh)
        else:
            html_node.children.insert(0, eh)
        h = eh

    if b is None:
        eb = Node(tag="body")
        eb.parent = html_node
        # Find position for body (after head)
        h_idx = html_node.children.index(h)
        html_node.children.insert(h_idx + 1, eb)
        # Move all non-head elements into body
        to_move = [c for c in list(html_node.children) if c is not h and c is not eb]
        for c in to_move:
            html_node.children.remove(c)
            if c.parent: c.parent = eb
            eb.children.append(c)
    else:
        # Move any elements not in head or body into body
        to_move = [c for c in list(html_node.children) if c is not h and c is not b]
        for c in to_move:
            old_parent = c.parent
            if old_parent: old_parent.children.remove(c)
            html_node.children.remove(c)
            c.parent = b
            b.children.append(c)

    return document

# ── CSS Selector Engine ──
class SimpleSelector:
    def __init__(self):
        self.tag = None
        self.ids = set()
        self.classes = set()
        self.attr_checks = []
        self.is_universal = False
    def match(self, node):
        if not node.is_element(): return False
        if self.tag is not None and self.tag != node.tag.lower(): return False
        if self.ids:
            nid = None
            for k, v in node.attrs:
                if k.lower() == "id": nid = v.lower(); break
            if nid is None or not self.ids.issubset({nid}): return False
        if self.classes:
            nc = set()
            for k, v in node.attrs:
                if k.lower() == "class" and v:
                    nc.update(tc.strip().lower() for tc in v.split() if tc.strip())
            if not self.classes.issubset(nc): return False
        for check in self.attr_checks:
            cname = check[0]
            if len(check) == 1:
                if not any(k.lower() == cname for k, _ in node.attrs): return False
                continue
            op, val, ci = check[1], check[2], check[3] if len(check) > 3 else False
            aval = None
            for k, v in node.attrs:
                if k.lower() == cname: aval = v; break
            if aval is None:
                if op != "!=": return False
                continue
            if ci: aval = aval.lower(); val = val.lower()
            if op == "=" and aval != val: return False
            if op == "~=" and val not in aval.split(): return False
            if op == "|=" and aval != val and not aval.startswith(val + "-"): return False
            if op == "^=" and not aval.startswith(val): return False
            if op == "$=" and not aval.endswith(val): return False
            if op == "*=" and val not in aval: return False
            if op == "!=" and aval == val: return False
        return True

def _tokenize_attr(s):
    s = s.strip()
    if not s: return None, None, None, False
    ci = False
    if s.endswith(' i'): ci = True; s = s[:-2].strip()
    elif s.endswith(' I'): ci = True; s = s[:-2].strip()
    for op in ['~=', '|=', '!=', '^=', '$=', '*=', '=']:
        idx = s.find(op)
        if idx >= 0:
            name = s[:idx].strip().lower()
            raw = s[idx+len(op):].strip()
            if len(raw)>=2 and raw[0] in ('"',"'") and raw[0]==raw[-1]: raw=raw[1:-1]
            return name, op, raw, ci
    return s.strip().lower(), None, None, False

def parse_simple_selector(token):
    ss = SimpleSelector()
    s, i = token, 0
    while i < len(s):
        c = s[i]
        if c == '#':
            j = i+1
            while j<len(s) and (s[j].isalnum() or s[j] in '-_@'): j+=1
            if j>i+1: ss.ids.add(s[i+1:j].lower())
            i = j
        elif c == '.':
            j = i+1
            while j<len(s) and (s[j].isalnum() or s[j] in '-_@'): j+=1
            if j>i+1: ss.classes.add(s[i+1:j].lower())
            i = j
        elif c == '[':
            d, j = 1, i+1
            while j<len(s) and d>0:
                if s[j]=='[': d+=1
                elif s[j]==']': d-=1
                j+=1
            inner = s[i+1:j-1]
            name, op, val, ci = _tokenize_attr(inner)
            if op is not None: ss.attr_checks.append((name,op,val,ci))
            else: ss.attr_checks.append((name,))
            i = j
        elif c == '*': ss.is_universal = True; i += 1
        elif c.isalnum() or c == '_':
            j = i
            while j<len(s) and (s[j].isalnum() or s[j] in '-_@'): j+=1
            if ss.tag is None: ss.tag = s[i:j].lower()
            i = j
        else: i += 1
    return ss

def find_all(document, ss):
    result = []
    def w(n):
        if n.is_element() and ss.match(n): result.append(n)
        for c in n.children: w(c)
    w(document)
    return result

def split_comma(s):
    parts, depth, buf, in_sq, in_dq = [], 0, [], False, False
    for c in s:
        if c == '"' and not in_sq: in_dq = not in_dq
        elif c == "'" and not in_dq: in_sq = not in_sq
        elif not in_sq and not in_dq:
            if c in '([{': depth += 1
            elif c in ')]}': depth -= 1
            elif c == ',' and depth == 0:
                r = ''.join(buf).strip()
                if r: parts.append(r)
                buf = []; continue
        buf.append(c)
    r = ''.join(buf).strip()
    if r: parts.append(r)
    return parts

def split_compound(part):
    tokens, depth, buf, in_sq, in_dq = [], 0, [], False, False
    for c in part:
        if c == '"' and not in_sq: in_dq = not in_dq
        elif c == "'" and not in_dq: in_sq = not in_sq
        elif not in_sq and not in_dq:
            if c in '([{': depth += 1
            elif c in ')]}': depth -= 1
            elif c == ' ' and depth == 0:
                t = ''.join(buf).strip()
                if t: tokens.append(t)
                buf = []; continue
        buf.append(c)
    t = ''.join(buf).strip()
    if t: tokens.append(t)
    return [parse_simple_selector(tok) for tok in tokens]

def find_compound(document, compound_str):
    sels = split_compound(compound_str)
    if not sels: return []
    if len(sels) == 1: return find_all(document, sels[0])
    results = []
    for m in find_all(document, sels[0]):
        results.extend(_desc(m, sels[1:]))
    return results

def _desc(ancestor, rest):
    if not rest: return [ancestor]
    ss = rest[0]; res = []
    for ch in ancestor.children:
        if ch.is_element() and ss.match(ch):
            if len(rest) == 1: res.append(ch)
            else: res.extend(_desc(ch, rest[1:]))
    return res

# ── Ordering ──
def assign_orders(node):
    ctr = [0]
    _ao(node, ctr)
def _ao(n, ctr):
    if n.is_element():
        n._order = ctr[0]; ctr[0] += 1
    for c in n.children: _ao(c, ctr)

# ── Serialization ──
esc_map = str.maketrans({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'})
def esc(s): return str(s).translate(esc_map)

def ser(node, pretty=False):
    if not node.is_element():
        return esc(node.text) if node.text is not None else ""
    tag = node.tag; a = ""
    for k, v in node.attrs:
        if v is None: a += f" {k}"
        else: a += f' {k}="{esc(v)}"'
    if tag in HTML_VOID_ELEMENTS:
        return f"<{tag}{a}>"
    inner = "".join(ser(c, pretty) for c in node.children)
    if pretty:
        return _pp(tag, a, inner, 0)
    return f"<{tag}{a}>{inner}</{tag}>"

def _pp(tag, a, inner, level):
    if tag in BLOCK_ELEMENTS:
        pre = "\n"
        lead = "  " * level
        if inner.strip():
            return f"{pre}<{tag}{a}>\n{lead}{inner}\n{pre}</{tag}>"
        else:
            return f"{pre}<{tag}{a}></{tag}>"
    return f"<{tag}{a}>{inner}</{tag}>"

# ── Utilities ──
def extract_text(node, ignore_ws=False):
    parts = []
    for c in node.children:
        if c.is_element():
            parts.append(extract_text(c, ignore_ws))
        else:
            t = c.text if c.text else ""
            if ignore_ws and not t.strip(): continue
            parts.append(t)
    return ''.join(parts)

def get_attr(node, name):
    nl = name.lower()
    for k, v in node.attrs:
        if k.lower() == nl: return v
    return None

def find_base(document):
    def w(n):
        if not n.is_element(): return None
        if n.tag == "base":
            for k, v in n.attrs:
                if k.lower() == "href" and v: return v
        for c in n.children:
            r = w(c)
            if r: return r
        return None
    return w(document)

def resolve_url(base, href): return urljoin(base, href) if base else href

def remove_from(document, sel_strs):
    for ss in sel_strs:
        for cp in split_comma(ss):
            for m in find_compound(document, cp.strip()):
                if m.parent:
                    m.parent.children = [c for c in m.parent.children if c is not m]

# ── Main ──
def main():
    args = sys.argv[1:]
    sels, text_flag, pretty_flag, ignore_ws, detect_base = [], False, False, False, False
    attr_name = base_url = filename = output_file = None
    removes = []
    i = 0
    while i < len(args):
        a = args[i]
        if a in ('-h','--help'): _help(); sys.exit(0)
        elif a in ('-V','--version'): print(VERSION_STR); sys.exit(0)
        elif a in ('-t','--text'): text_flag = True
        elif a in ('-p','--pretty'): pretty_flag = True
        elif a in ('-w','--ignore-whitespace'): ignore_ws = True
        elif a in ('-B','--detect-base'): detect_base = True
        elif a in ('-a','--attribute'): i += 1; attr_name = args[i]
        elif a in ('-b','--base'): i += 1; base_url = args[i]
        elif a in ('-f','--filename'): i += 1; filename = args[i]
        elif a in ('-o','--output'): i += 1; output_file = args[i]
        elif a in ('-r','--remove-nodes'): i += 1; removes.append(args[i])
        elif a == '--': i += 1; sels.extend(args[i:]); break
        else: sels.append(a)
        i += 1
    sel_str = ", ".join(sels) if sels else "html"
    if filename:
        try:
            with open(filename) as f: html_str = f.read()
        except OSError as e:
            err_detail = str(e)
            m2 = re.search(r'message: "([^"]*)"', err_detail)
            if m2: msg = m2.group(1)
            else: msg = err_detail
            sys.stderr.write(
                f"\nthread 'main' ({os.getpid()}) panicked at src/main.rs:196:37:\n"
                f'should have opened input file: Os {{ code: 2, kind: NotFound, message: "{msg}" }}\n'
                'note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace\n'
            )
            sys.exit(101)
    else:
        html_str = sys.stdin.read()
    doc = parse_html(html_str)
    assign_orders(doc)
    force_html_structure(doc)
    assign_orders(doc)
    if detect_base:
        db = find_base(doc)
        eff_base = db if db else base_url
    else:
        eff_base = base_url
    if removes: remove_from(doc, removes)
    results, seen = [], set()
    for sel in split_comma(sel_str):
        for m in find_compound(doc, sel):
            oid = id(m)
            if oid not in seen: seen.add(oid); results.append(m)
    results.sort(key=lambda n: n._order)
    lines = []
    for node in results:
        if text_flag: lines.append(extract_text(node, ignore_ws))
        elif attr_name:
            v = get_attr(node, attr_name)
            if v is not None:
                if eff_base: v = resolve_url(eff_base, v)
                lines.append(v)
        else: lines.append(ser(node, pretty_flag))
    out = '\n'.join(lines)
    if out: out += '\n'
    if output_file:
        with open(output_file, 'w') as f: f.write(out)
    else:
        sys.stdout.write(out)

def _help():
    print("""htmlq 0.4.0
Michael Maclean <michael@mgdm.net>
Runs CSS selectors on HTML

USAGE:
    executable [FLAGS] [OPTIONS] [--] [selector]...

FLAGS:
    -B, --detect-base          Try to detect the base URL from the <base> tag in the document. If not found, default to
                               the value of --base, if supplied
    -h, --help                 Prints help information
    -w, --ignore-whitespace    When printing text nodes, ignore those that consist entirely of whitespace
    -p, --pretty               Pretty-print the serialised output
    -t, --text                 Output only the contents of text nodes inside selected elements
    -V, --version              Prints version information

OPTIONS:
    -a, --attribute <attribute>         Only return this attribute (if present) from selected elements
    -b, --base <base>                   Use this URL as the base for links
    -f, --filename <FILE>               The input file. Defaults to stdin
    -o, --output <FILE>                 The output file. Defaults to stdout
    -r, --remove-nodes <SELECTOR>...    Remove nodes matching this expression before output. May be specified multiple
                                        times

ARGS:
    <selector>...    The CSS expression to select [default: html]""")

if __name__ == "__main__":
    main()
