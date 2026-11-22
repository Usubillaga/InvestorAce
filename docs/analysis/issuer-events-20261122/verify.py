"""Offline fixed-generation checks; not a source-authentication or valuation certificate."""
import copy
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
import engine as e
import evidence
import source_review


def run():
    base_text = subprocess.check_output(['git', 'show', 'cb6e102:source_reviews.json'], cwd=ROOT).decode()
    old = source_review.load(base_text)
    new = source_review.load((ROOT / 'source_reviews.json').read_text())
    # Every authoritative numerical boundary is unchanged, including typed blockers.
    fields = ('financial_packet', 'common_equity_bridge', 'input_conflicts', 'dcf')
    for ticker in old['entries'].keys() | new['entries'].keys():
        a, b = old['entries'].get(ticker, {}).get('valuation', {}), new['entries'].get(ticker, {}).get('valuation', {})
        assert all(a.get(k) == b.get(k) for k in fields), ticker
    b = evidence.current_build(ROOT / 'history')
    rows = copy.deepcopy(b['record']['_evidence']['inputs'])
    assert set(rows) == set(e.DATA) and len(rows) == 125
    e.DATA = rows
    macro = copy.deepcopy(b['record']['_evidence']['macro'])
    def capture(register):
        e.SOURCE_REVIEW.load = lambda *args, **kwargs: copy.deepcopy(register)
        return dict(rows={t: dict(score=e.score(d), ngv=e.ngv(d), reverse=e.implied_growth(d),
                                 cover=e.cover(d), cushion=e.cushion(d), risk=e.risk(d),
                                 verdict=e.verdict(t, d), fit=e.regime_scores(d)) for t, d in rows.items()},
                    books={r: e.regime_book(r) for r in e.REGIMES},
                    screens={p: e.screen(p, regime=e.REGIMES[0] if p == 'regime' else None,
                                         reviewed_only=False) for p in ('quality', 'regime', 'duration')},
                    proposals={r: e.portfolio_proposal(r) for r in e.REGIMES})
    original = e.SOURCE_REVIEW.load
    try:
        before, after = capture(old), capture(new)
    finally:
        e.SOURCE_REVIEW.load = original
    assert before == after
    bundle = evidence.model_bundle(ROOT)
    record = e.observation(macro, bundle, '2026-11-22T08:03:19+00:00')
    assert record['_source_reviews'] == new
    assert record['_evidence']['model_source_sha256'] == bundle['sha256']
    html = e.build_html(macro=macro, write=False, reviews=record['_source_reviews'])
    assert 'Event/payment monitoring: PARTIAL' in html
    for ticker in ('OXY','ENB','CRWV','MRNA','NBIS','OPEN','AVGO','BYRN','INTU','NVDA'):
        assert new['entries'][ticker]['monitoring']['summary'] in html
    assert e.regime_regression_errors() == []
    print(json.dumps(dict(frozen_run=b['manifest']['run_id'], rows=len(rows),
                          identical=['score','NGV','reverseDCF','cover','cushion','risk','verdict',
                                     'five raw regime books','three screens','five portfolio proposals'],
                          register_observation_html_same_generation=True,
                          golden_master_unchanged=True, network_calls=0), indent=2))


if __name__ == '__main__':
    run()
