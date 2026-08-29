#!/usr/bin/env python3
"""
verify_tickers.py · run the library against Yahoo and report every entry that is wrong

  python verify_tickers.py tickers.js
  python verify_tickers.py tickers.js --fix     # rewrite currencies from Yahoo

WHY THIS EXISTS
---------------
A curated ticker list is the most dangerous file in this project, because a wrong
symbol returns a REAL price for the WRONG company and nothing downstream can tell.
Three examples already found by hand:

  SAN.MC   labelled Sanofi      -> is Banco Santander   (~10x price difference)
  ENGI.PA  labelled Enagas      -> is ENGIE             (different company)
  MUVG.DE  labelled Munich Re   -> does not exist
  NVO      labelled DKK         -> quotes USD           (ADR, not the Copenhagen line)
  ENB      labelled CAD         -> quotes USD           (NYSE line, not .TO)

That is roughly a 5% error rate in a hand-checked 62-entry list. At 600 entries a
5% rate is thirty wrong tickers. THIS is what makes a large library safe to build —
not care, which demonstrably is not enough. Run it after every expansion.

WHAT IT CHECKS
  1 does the symbol resolve at all
  2 does Yahoo's long name plausibly match the name in the library
  3 does Yahoo's currency match the declared currency
  4 is a price actually available
"""
import sys, json, re, time

try:
    import yfinance as yf
except ImportError:
    sys.exit('pip install yfinance')

def load(path):
    src = open(path, encoding='utf-8').read()
    body = src[src.index('['): src.rindex(']')+1]
    body = re.sub(r'//[^\n]*', '', body)                  # strip comments
    body = re.sub(r'(\w+)\s*:', r'"\1":', body)           # bare keys -> json keys
    body = re.sub(r',\s*([\]\}])', r'\1', body)           # trailing commas
    return json.loads(body)

def norm(s):
    s = (s or '').lower()
    for junk in (' inc',' corp',' corporation',' plc',' sa',' se',' nv',' n.v.',' ag',' ltd',
                 ' limited',' holding',' holdings',' group',' co',' company',' the ','.',',','&'):
        s = s.replace(junk,' ')
    return ' '.join(s.split())

def match(lib_name, yahoo_name):
    a, b = norm(lib_name), norm(yahoo_name)
    if not b: return None                                  # nothing to compare against
    if a in b or b in a: return True
    at, bt = set(a.split()), set(b.split())
    return bool(at & bt)                                   # any shared significant word

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else 'tickers.js'
    fix  = '--fix' in sys.argv
    lib  = load(path)
    print(f'{len(lib)} entries in {path}\n')
    bad, warn, ok = [], [], 0
    for i, e in enumerate(lib, 1):
        sym = e['yf']
        try:
            tk = yf.Ticker(sym)
            fi = {}
            try: fi = dict(tk.fast_info) or {}
            except Exception: pass
            px  = fi.get('last_price')
            cur = str(fi.get('currency') or '').strip()
            name = ''
            try: name = (tk.get_info() or {}).get('longName') or ''
            except Exception: pass

            if px is None and not cur and not name:
                bad.append((sym, e['name'], 'DOES NOT RESOLVE')); continue
            m = match(e['name'], name)
            if m is False:
                bad.append((sym, e['name'], f'NAME MISMATCH -> Yahoo says "{name}"')); continue
            if cur and cur.upper() != e['cur'].upper():
                bad.append((sym, e['name'], f'CURRENCY {e["cur"]} -> Yahoo says {cur}'))
                if fix: e['cur'] = cur
                continue
            if px is None:
                warn.append((sym, e['name'], 'resolves but no price')); continue
            ok += 1
        except Exception as ex:
            bad.append((sym, e['name'], f'{type(ex).__name__}'))
        if i % 25 == 0:
            print(f'  ...{i}/{len(lib)}'); time.sleep(1)     # be polite to Yahoo

    print(f'\nOK       {ok}')
    print(f'WARN     {len(warn)}')
    for s,n,r in warn: print(f'   {s:12} {n[:28]:30} {r}')
    print(f'BAD      {len(bad)}   <- fix these before trusting the library')
    for s,n,r in bad:  print(f'   {s:12} {n[:28]:30} {r}')

    if fix and bad:
        out = 'const tickerLibrary = ' + json.dumps(lib, indent=1, ensure_ascii=False) + ';\n'
        open(path,'w',encoding='utf-8').write(out)
        print(f'\ncurrencies rewritten into {path}. Name mismatches are NOT auto-fixed — '
              f'a wrong symbol needs a human, not a script.')
    return 1 if bad else 0

if __name__ == '__main__':
    sys.exit(main())

