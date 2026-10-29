"""Build a local UI replay from committed facts; fetches no current market data."""
import copy
import io
import json
import sys
from contextlib import redirect_stderr
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
import engine  # noqa: E402
import evidence  # noqa: E402
import i18n  # noqa: E402
import live_analysis  # noqa: E402
import market_scanner  # noqa: E402
import source_review  # noqa: E402


def generate(destination):
    destination.mkdir(parents=True,exist_ok=True)
    source=evidence.current_build(ROOT/'history')['record']
    rows=copy.deepcopy(source['_evidence']['inputs'])
    macro=source['_evidence']['macro']
    rates=source['_rates'];facts=json.loads((ROOT/'history/_dynamic_cache.json').read_text())['entries']
    now=datetime.now(timezone.utc)
    reviews=source_review.load()
    engine.WACC.set_risk_free(rates['risk_free'],rates.get('source'),rates.get('asof'))
    engine.LIVE_10Y=rates.get('live_10y')
    for ticker,row in rows.items():
        packet=facts.get(row.get('yf',ticker))
        if not packet or not row.get('dynamic_analysis'):
            continue
        packet=live_analysis.prefer_primary(packet,
            reviews['entries'].get(ticker,{}).get('valuation',{}).get('financial_packet'),as_of=now)
        analysis=live_analysis.calculate(dict(packet,midcycle=bool(row.get('midcycle'))),
            quote=dict(price=row.get('price'),observed_at=row.get('quote_observed_at')),
            risk_free=rates['risk_free']/100,mrp=rates['mrp']/100,as_of=now)
        row.update(analysis['overlay']);row['dynamic_analysis']=analysis
    with patch.object(engine,'DATA',rows),patch.object(engine,'sector_performance',return_value={}), \
         patch.object(engine,'regime_history',return_value=([],{})), \
         patch.object(engine,'forward_run',return_value={}),redirect_stderr(io.StringIO()):
        record=engine.observation(macro,evidence.model_bundle(ROOT),captured_at=now.isoformat())
        html=engine.build_html(macro=macro,write=False,
            assessments={ticker:record[ticker]['assessment'] for ticker in rows})
    for language in ('en','de','es'):
        (destination/f'index.{language}.html').write_text(i18n.localize(html,language))
    scan=market_scanner.build_scan(record,as_of=now,market=market_scanner.load_market(ROOT))
    (destination/'scanner.html').write_text(market_scanner.render_scan(scan))
    (destination/'scanner.json').write_text(json.dumps(scan,ensure_ascii=False,allow_nan=False))
    print(f'Replayed {len(rows)} companies; automatic labels: '+str(sum(
        record[ticker]['opportunity']['label'] is not None for ticker in rows)))


if __name__=='__main__':
    generate(Path(sys.argv[1]))
