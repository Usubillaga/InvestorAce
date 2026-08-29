import sys
import yfinance as yf
import re

if len(sys.argv) < 4:
    sys.exit(0)

ticker = sys.argv[1].upper()
fcf = sys.argv[2] if sys.argv[2] else 'None'
shares = sys.argv[3] if sys.argv[3] else 'None'

try:
    info = yf.Ticker(ticker).info
    sector = info.get('sector', 'Unknown')
    currency = info.get('currency', 'USD')
except:
    sector = 'Unknown'
    currency = 'USD'

# Formatiere den neuen Eintrag
new_entry = f"'{ticker}': dict(yf='{ticker}', fcf={fcf}, shares={shares}, r=.080, cur='{currency}', deliver=None, dl='', sub=None, pr=None, dil=6.0, clock='CONC', ins='', held=False, sector='{sector}', built='exact'),\n"

# Füge ihn in die build_scoreboard.py ein
with open('build_scoreboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Suche das Ende des DATA Dictionaries und füge den Ticker hinzu
content = re.sub(r'(DATA\s*=\s*\{.*?)(^\})', r'\1' + new_entry + r'\2', content, flags=re.DOTALL | re.MULTILINE)

with open('build_scoreboard.py', 'w', encoding='utf-8') as f:
    f.write(content)

print(f"Ticker {ticker} added successfully.")

