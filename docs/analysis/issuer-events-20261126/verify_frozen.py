import copy
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))

import engine as e
import evidence
import source_review

root = Path.cwd()
old = source_review.load(subprocess.check_output(['git','show','b2726f086a4fda64ad8ffbdb07b6e5cdae87307d:source_reviews.json'],text=True))
new = source_review.load()
build = evidence.current_build(root / 'history')
rows = copy.deepcopy(build['record']['_evidence']['inputs'])
macro = copy.deepcopy(build['record']['_evidence']['macro'])
at = datetime.fromisoformat(build['record']['_evidence']['captured_at'])
assert len(rows) == 132

def capture(register):
    with patch.object(e.SOURCE_REVIEW, 'load', return_value=register):
        return dict(
            scorecard={t: dict(score=e.score(d), ngv=e.ngv(d), reverse=e.implied_growth(d),
                              cover=e.cover(d), cushion=e.cushion(d), risk=e.risk(d),
                              verdict=e.verdict(t,d), opportunity=e.opportunity(
                                  d,regime=macro.get('regime'), weights=macro.get('regime_weights'),as_of=at))
                       for t,d in rows.items()},
            regimes={t:e.regime_scores(d) for t,d in rows.items()},
            books=[e.regime_book(r) for r in e.REGIMES],
            screens=[e.screen(p,regime=e.REGIMES[0] if p=='regime' else None,reviewed_only=False)
                     for p in ('quality','regime','duration')],
            portfolios=[e.portfolio_proposal(r) for r in e.REGIMES])

with patch.object(e,'DATA',rows):
    before,after=capture(old),capture(new)
    assert before==after, 'Metadata changed model outputs'
    bundle=evidence.model_bundle(root)
    record=e.observation(macro,bundle,build['record']['_evidence']['captured_at'])
    assert record['_source_reviews']==new
    assert json.loads(bundle['sources']['source_reviews.json'])==new
    with patch.object(e,'sector_performance',return_value={}),patch.object(e,'forward_run',return_value={'ok':False}):
        html=e.build_html(macro=macro,write=False,reviews=record['_source_reviews'])
    for t in ('VIS','JD','BIDU','FPS','PAYX'):
        assert new['entries'][t]['monitoring']['summary'] in html
    assert e.regime_regression_errors()==[]

result=dict(universe=132,fixture='Same latest verified market/fundamental/macro inputs for both runs',
            captured_at=build['record']['_evidence']['captured_at'],
            compared=['scorecard','regimes','books','screens','portfolios'],identical=True,
            frozen_register_model_observation_html=True,regime_golden_errors=0,
            numeric_updates=0)
Path('docs/analysis/issuer-events-20261126/comparison.json').write_text(json.dumps(result,indent=2)+'\n')
print(result)
