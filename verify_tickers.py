#!/usr/bin/env python3
"""Verify ticker-library symbols, names, currencies and prices against Yahoo."""
import sys, json, re, time

try:
    import yfinance as yf
except ImportError:
    raise SystemExit('pip install yfinance')


def load(path):
    src = open(path, encoding='utf-8').read()
    m = re.search(r'const\s+tickerLibrary\s*=\s*(\[.*\])\s*;?\s*$', src, re.S)
    if not m:
        raise ValueError('Could not find `const tickerLibrary = [...]` in file')
    # This library is valid JSON-compatible JS: keys/strings use JSON syntax.
    return json.loads(m.group(1))


def norm(s):
    s = (s or '').lower()
    for junk in (' inc',' corp',' corporation',' plc',' sa',' se',' nv',' n.v.',' ag',' ltd',
                 ' limited',' holding',' holdings',' group',' co',' company',' the ','.',',','&'):
        s = s.replace(junk, ' ')
    return ' '.join(s.split())


def match(lib_name, yahoo_name):
    a, b = norm(lib_name), norm(yahoo_name)
    if not b:
        return None
    if a in b or b in a:
        return True
    at, bt = set(a.split()), set(b.split())
    # Ignore tiny/common tokens when deciding plausibility.
    common = {'and', 'the', 'of'}
    return bool((at - common) & (bt - common))


def yahoo_currency(tk, info):
    fi = info or {}
    cur = str(fi.get('currency') or '').strip()
    if cur:
        return cur
    try:
        return str((tk.get_info() or {}).get('currency') or '').strip()
    except Exception:
        return ''


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else 'tickers.js'
    fix = '--fix' in sys.argv
    lib = load(path)
    print(f'{len(lib)} entries in {path}\n')

    bad, warn, ok = [], [], 0
    changed = False

    for i, e in enumerate(lib, 1):
        sym = e['yf']
        try:
            tk = yf.Ticker(sym)
            fi = {}
            try:
                fi = dict(tk.fast_info) or {}
            except Exception:
                pass

            px = fi.get('last_price')
            cur = yahoo_currency(tk, fi)
            try:
                name = (tk.get_info() or {}).get('longName') or ''
            except Exception:
                name = ''

            if px is None and not cur and not name:
                bad.append((sym, e['name'], 'DOES NOT RESOLVE'))
                continue

            m = match(e['name'], name)
            if m is False:
                bad.append((sym, e['name'], f'NAME MISMATCH -> Yahoo says "{name}"'))
                continue

            declared = e['cur']
            # Yahoo commonly reports London prices as GBp. Treat declared GBp as
            # compatible with Yahoo GBP only for .L tickers; do not rewrite it.
            compatible = cur.upper() == declared.upper()
            if sym.endswith('.L') and declared.lower() == 'gbp' and cur.upper() == 'GBP':
                compatible = True

            if cur and not compatible:
                bad.append((sym, e['name'], f'CURRENCY {declared} -> Yahoo says {cur}'))
                if fix:
                    e['cur'] = 'GBp' if sym.endswith('.L') and cur.upper() == 'GBP' else cur
                    changed = True
                continue

            if px is None:
                warn.append((sym, e['name'], 'resolves but no price'))
                continue

            ok += 1
        except Exception as ex:
            bad.append((sym, e['name'], f'{type(ex).__name__}: {ex}'))

        if i % 25 == 0:
            print(f'  ...{i}/{len(lib)}')
            time.sleep(1)

    print(f'\nOK       {ok}')
    print(f'WARN     {len(warn)}')
    for s, n, r in warn:
        print(f'   {s:12} {n[:28]:30} {r}')
    print(f'BAD      {len(bad)}   <- fix these before trusting the library')
    for s, n, r in bad:
        print(f'   {s:12} {n[:28]:30} {r}')

    if fix and changed:
        out = 'const tickerLibrary = ' + json.dumps(lib, indent=1, ensure_ascii=False) + ';\n'
        open(path, 'w', encoding='utf-8').write(out)
        print(f'\nCurrencies rewritten into {path}. Name mismatches are NOT auto-fixed.')

    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
