#!/usr/bin/env python3
import sys
import re
import os

def main():
    args = parse_cmdline(sys.argv[1:])
    if args is None: return
    if args.get('help'):
        (print_short_help if args.get('short_help') else print_long_help)()
        sys.exit(0)
    if args.get('version'):
        print('sd 1.0.0')
        sys.exit(0)
    find_pattern = args['find']
    replacement = args['replace']
    preview = args['preview']
    fixed_strings = args['fixed_strings']
    max_replacements = args['max_replacements']
    flags = args['flags']
    files = args['files']
    parsed_flags = parse_flag_chars(flags)
    regex = None
    if not fixed_strings:
        try:
            regex = build_regex(find_pattern, parsed_flags)
        except re.error as e:
            el = find_pattern.split('\n')[0]
            em = e.args[0] if e.args else str(e)
            p = e.pos if hasattr(e,'pos') and e.pos is not None else 0
            cl = ' ' * p + '^'
            sys.stderr.write('error: invalid regex regex parse error:\n    ' + el + '\n    ' + cl + '\nerror: ' + em + '\n')
            sys.exit(1)
    use_stdin = len(files) == 0
    if use_stdin:
        text = sys.stdin.read()
        result = process_text(text, find_pattern, replacement, fixed_strings, regex, parsed_flags, max_replacements)
        if result is None: sys.exit(1)
        sys.stdout.write(result)
    else:
        for fp in files:
            if not os.path.exists(fp):
                sys.stderr.write('error: invalid path: ' + fp + '\n')
                sys.exit(1)
            with open(fp, 'rb') as f:
                cb = f.read()
            try:
                ct = cb.decode('utf-8')
            except UnicodeDecodeError:
                ct = cb.decode('latin-1')
            result = process_text(ct, find_pattern, replacement, fixed_strings, regex, parsed_flags, max_replacements)
            if result is None: sys.exit(1)
            if preview:
                sys.stdout.write(result)
            else:
                with open(fp, 'wb') as f:
                    f.write(result.encode('utf-8'))

def parse_cmdline(argv):
    r = dict(help=False, short_help=False, version=False, preview=False,
             fixed_strings=False, max_replacements=0, flags='', find=None, replace=None, files=[])
    i = 0
    seen_mr = False
    seen_f = False
    eoo = False
    while i < len(argv):
        a = argv[i]
        if not eoo:
            if a == '--':
                eoo = True; i += 1; continue
            elif a in ('-h', '--help'):
                r['help'] = True; r['short_help'] = (a == '-h'); i += 1; continue
            elif a in ('-V', '--version'):
                r['version'] = True; i += 1; continue
            elif a in ('-p', '--preview'):
                r['preview'] = True; i += 1; continue
            elif a in ('-F', '--fixed-strings'):
                r['fixed_strings'] = True; i += 1; continue
            elif a in ('-n', '--max-replacements'):
                if seen_mr:
                    sys.stderr.write("error: the argument '--max-replacements <LIMIT>' cannot be used multiple times\n\nUsage: executable [OPTIONS] <FIND> <REPLACE_WITH> [FILES]...\n\nFor more information, try '--help'.\n")
                    sys.exit(2)
                seen_mr = True; i += 1
                if i >= len(argv):
                    sys.stderr.write("error: a value is required for '--max-replacements <LIMIT>' but none was supplied\n\nUsage: executable [OPTIONS] <FIND> <REPLACE_WITH> [FILES]...\n\nFor more information, try '--help'.\n")
                    sys.exit(2)
                v = argv[i]
                try:
                    r['max_replacements'] = int(v)
                except ValueError:
                    sys.stderr.write("error: invalid value '" + v + "' for '--max-replacements <LIMIT>': invalid digit found in string\n\nUsage: executable [OPTIONS] <FIND> <REPLACE_WITH> [FILES]...\n\nFor more information, try '--help'.\n")
                    sys.exit(2)
                i += 1; continue
            elif a in ('-f', '--flags'):
                if seen_f:
                    sys.stderr.write("error: the argument '--flags <FLAGS>' cannot be used multiple times\n\nUsage: executable [OPTIONS] <FIND> <REPLACE_WITH> [FILES]...\n\nFor more information, try '--help'.\n")
                    sys.exit(2)
                seen_f = True; i += 1
                if i >= len(argv):
                    sys.stderr.write("error: a value is required for '--flags <FLAGS>' but none was supplied\n\nUsage: executable [OPTIONS] <FIND> <REPLACE_WITH> [FILES]...\n\nFor more information, try '--help'.\n")
                    sys.exit(2)
                r['flags'] = argv[i]; i += 1; continue
            elif a.startswith('-'):
                if a.startswith('--'):
                    sys.stderr.write("error: unexpected argument '--" + a[2:] + "' found\n\n  tip: to pass '" + a + "' as a value, use '-- " + a + "'\n\nUsage: executable [OPTIONS] <FIND> <REPLACE_WITH> [FILES]...\n\nFor more information, try '--help'.\n")
                else:
                    sys.stderr.write("error: unexpected argument '" + a + "' found\n\n  tip: to pass '" + a + "' as a value, use '-- " + a + "'\n\nUsage: executable [OPTIONS] <FIND> <REPLACE_WITH> [FILES]...\n\nFor more information, try '--help'.\n")
                sys.exit(2)
        # Positional arguments
        if r['find'] is None:
            r['find'] = a
        elif r['replace'] is None:
            r['replace'] = a
        else:
            r['files'].append(a)
        i += 1
    
    # Skip required args check if help or version requested
    if r['help'] or r['version']:
        return r
    
    if r['find'] is None and r['replace'] is None:
        sys.stderr.write("error: the following required arguments were not provided:\n  <FIND>\n  <REPLACE_WITH>\n\nUsage: executable <FIND> <REPLACE_WITH> [FILES]...\n\nFor more information, try '--help'.\n")
        sys.exit(2)
    elif r['find'] is None:
        sys.stderr.write("error: the following required arguments were not provided:\n  <FIND>\n\nUsage: executable <FIND> <REPLACE_WITH> [FILES]...\n\nFor more information, try '--help'.\n")
        sys.exit(2)
    elif r['replace'] is None:
        sys.stderr.write("error: the following required arguments were not provided:\n  <REPLACE_WITH>\n\nUsage: executable <FIND> <REPLACE_WITH> [FILES]...\n\nFor more information, try '--help'.\n")
        sys.exit(2)
    return r

def parse_flag_chars(fs):
    r = dict(case_insensitive=False, multiline=True, dotall=False, word_match=False)
    for c in fs:
        if c == 'i': r['case_insensitive'] = True
        elif c == 'm': r['multiline'] = True
        elif c == 'e': r['multiline'] = False
        elif c == 's': r['dotall'] = True
        elif c == 'w': r['word_match'] = True
    return r

def build_regex(p, fl):
    f = 0
    if fl['case_insensitive']: f |= re.IGNORECASE
    if fl['multiline']: f |= re.MULTILINE
    if fl['dotall']: f |= re.DOTALL
    if fl['word_match']: p = r'\b' + p + r'\b'
    return re.compile(p, f)

def parse_replacement(repl, rx, fs):
    if fs: return [('l', repl)]
    toks = []
    i = 0
    while i < len(repl):
        c = repl[i]
        if c == '$' and i + 1 < len(repl) and repl[i + 1] == '$':
            toks.append(('l', '$')); i += 2
        elif c == '$':
            if i + 1 >= len(repl):
                toks.append(('l', '$')); i += 1; continue
            n = repl[i + 1]
            if n == '{':
                k = i + 2
                eb = repl.find('}', k)
                if eb == -1:
                    toks.append(('l', '$')); i += 1; continue
                inn = repl[k:eb]
                try:
                    toks.append(('cn', int(inn)))
                except ValueError:
                    toks.append(('na', inn))
                i = eb + 1; continue
            elif n.isdigit():
                k = i + 1
                while k < len(repl) and repl[k].isdigit():
                    k += 1
                ns = repl[i + 1:k]
                if k < len(repl) and (repl[k].isalpha() or repl[k] == '_'):
                    we = k
                    while we < len(repl) and (repl[we].isalnum() or repl[we] == '_'):
                        we += 1
                    suf = repl[k:we]
                    hint = '${' + ns + '}' + suf
                    ml = we - 1
                    mk = ' ' + '^' * ml
                    sys.stderr.write("error: The numbered capture group `$" + ns + "` in the replacement text is ambiguous.\nhint: Use curly braces to disambiguate it `" + hint + "`.\n" + repl + "\n" + mk + "\n")
                    return None
                toks.append(('cn', int(ns))); i = k; continue
            elif n.isalpha() or n == '_':
                k = i + 1
                while k < len(repl) and (repl[k].isalnum() or repl[k] == '_'):
                    k += 1
                toks.append(('na', repl[i + 1:k])); i = k; continue
            else:
                toks.append(('l', '$')); i += 1
        else:
            toks.append(('l', c)); i += 1
    return toks

def process_text(text, find_pat, repl, fs, rx, pf, mr):
    if fs:
        if mr > 0: return text.replace(find_pat, repl, mr)
        return text.replace(find_pat, repl)
    toks = parse_replacement(repl, rx, fs)
    if toks is None: return None
    def rf(m):
        pp = []
        for tt, tv in toks:
            if tt == 'cn':
                if 0 <= tv <= rx.groups:
                    pp.append(m.group(tv))
                else:
                    pp.append('')
            elif tt == 'na':
                if tv in rx.groupindex:
                    pp.append(m.group(tv))
                else:
                    pp.append('')
            else:
                pp.append(tv)
        return ''.join(pp)
    count = mr if mr > 0 else 0
    return rx.sub(rf, text, count=count)

SHELP = """sd v1.0.0
An intuitive find & replace CLI

Usage: executable [OPTIONS] <FIND> <REPLACE_WITH> [FILES]...

Arguments:
  <FIND>          The regexp or string (if using `-F`) to search for
  <REPLACE_WITH>  What to replace each match with. Unless in string mode, you may use captured
                  values like $1, $2, etc
  [FILES]...      The path to file(s). This is optional - sd can also read from STDIN

Options:
  -p, --preview                   Display changes in a human reviewable format (the specifics of the
                                  format are likely to change in the future)
  -F, --fixed-strings             Treat FIND and REPLACE_WITH args as literal strings
  -n, --max-replacements <LIMIT>  Limit the number of replacements that can occur per file. 0
                                  indicates unlimited replacements [default: 0]
  -f, --flags <FLAGS>             Regex flags. May be combined (like `-f mc`).
  -h, --help                      Print help (see more with '--help')
  -V, --version                   Print version"""

LHELP = """sd v1.0.0
An intuitive find & replace CLI

Usage: executable [OPTIONS] <FIND> <REPLACE_WITH> [FILES]...

Arguments:
  <FIND>
          The regexp or string (if using `-F`) to search for

  <REPLACE_WITH>
          What to replace each match with. Unless in string mode, you may use captured values like
          $1, $2, etc

  [FILES]...
          The path to file(s). This is optional - sd can also read from STDIN.
          
          Note: sd modifies files in-place by default. See documentation for examples.

Options:
  -p, --preview
          Display changes in a human reviewable format (the specifics of the format are likely to
          change in the future)

  -F, --fixed-strings
          Treat FIND and REPLACE_WITH args as literal strings

  -n, --max-replacements <LIMIT>
          Limit the number of replacements that can occur per file. 0 indicates unlimited
          replacements
          
          [default: 0]

  -f, --flags <FLAGS>
          Regex flags. May be combined (like `-f mc`).
          
          c - case-sensitive
          
          e - disable multi-line matching
          
          i - case-insensitive
          
          m - multi-line matching
          
          s - make `.` match newlines
          
          w - match full words only

  -h, --help
          Print help (see a summary with '-h')

  -V, --version
          Print version"""

def print_short_help():
    print(SHELP)

def print_long_help():
    print(LHELP)

if __name__ == '__main__':
    main()
