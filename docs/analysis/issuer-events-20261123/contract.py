"""Explicitly unavailable price judgments; the evidence packet is separate."""
import json
from datetime import datetime, timezone
from pathlib import Path

HERE=Path(__file__).parent
tickers=('VNT','ALLE','ADT','OXY','CRWV','ALC','ALM','AMD','ANT','B')
at=datetime.now(timezone.utc).isoformat()
doc=dict(mode='live',as_of=at,run_at=at,max_quote_age_hours=96,evidence=[],issues=[],methodology=None,
    issuers=[dict(ticker=t,currency='EUR' if t=='ALM' else 'USD',quote=None,
        checks={k:'open' for k in ('source_tieout','comparability','per_share_basis','calculations','framework')},
        metrics=[dict(id=t+'-ngv',name='ngv',value=None,unit='currency/share',period='current',
            basis='No completed sustainable common-equity/discount-rate tie-out',price_dependent=True,evidence_ids=[],
            reason='Partial source review; no current audited price judgment or replacement valuation.')],
        decision='blocked_data',decision_basis='data_gap') for t in tickers])
(HERE/'review-run.json').write_text(json.dumps(doc,indent=2)+'\n')
