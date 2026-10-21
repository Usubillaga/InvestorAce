"""Regressions from the final independent framework review."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd
import assessment
import autoscore
import market_scanner
import portfolio
import stock_compare
import test_assessment_integrity as fixtures
from test_framework_contract import engine


OBJECTION = dict(id='NEW', severity='critical', status='open', message='New financial conflict')
NOW = fixtures.NOW
complete_row = fixtures.complete_row


def approved():
    helper = fixtures.AssessmentIntegrity()
    row = complete_row()
    return row, helper.assess(row, reviews=helper.reviewed(row))


def packet(row, checked):
    return {'AAA': dict(score=8.225, assessment=checked), '_evidence': dict(
        captured_at=NOW.isoformat(), inputs={'AAA': row}, model_source_sha256='a' * 64)}


class FinalReviewRegressions(unittest.TestCase):
    def test_annual_revenue_cannot_form_ttm_margins(self):
        q = pd.to_datetime(['2026-09-30', '2026-06-30', '2026-03-31', '2025-12-31'])
        a = pd.to_datetime(['2025-12-31', '2024-12-31'])
        tk = SimpleNamespace(fast_info={'last_price': 100, 'shares': 10e6, 'currency': 'USD'},
            get_info=lambda: {}, quarterly_balance_sheet=pd.DataFrame(),
            quarterly_cashflow=pd.DataFrame([[10e6]*4], index=['Free Cash Flow'], columns=q),
            quarterly_income_stmt=pd.DataFrame([[10e6]*4], index=['Operating Income'], columns=q),
            income_stmt=pd.DataFrame([[100e6, 90e6]], index=['Total Revenue'], columns=a))
        with patch.object(autoscore.yf, 'Ticker', return_value=tk):
            row, _ = autoscore.auto_row('AAA')
        self.assertIsNone(row['draft_components']['p'])
        self.assertIsNone(row['draft_components']['c'])

    def test_different_quarter_endpoints_cannot_form_cash_margin(self):
        iq = pd.to_datetime(['2026-09-30', '2026-06-30', '2026-03-31', '2025-12-31'])
        cq = pd.to_datetime(['2026-06-30', '2026-03-31', '2025-12-31', '2025-09-30'])
        tk = SimpleNamespace(fast_info={'last_price': 100, 'shares': 10e6, 'currency': 'USD'},
            get_info=lambda: {}, quarterly_balance_sheet=pd.DataFrame(), income_stmt=pd.DataFrame(),
            quarterly_cashflow=pd.DataFrame([[10e6]*4], index=['Free Cash Flow'], columns=cq),
            quarterly_income_stmt=pd.DataFrame([[100e6]*4, [20e6]*4],
                index=['Total Revenue', 'Operating Income'], columns=iq))
        with patch.object(autoscore.yf, 'Ticker', return_value=tk):
            row, _ = autoscore.auto_row('AAA')
        self.assertEqual(row['draft_components']['p'], 7.5)
        self.assertIsNone(row['draft_components']['c'])

    def test_current_objection_withdraws_frozen_approval_in_all_consumers(self):
        row, checked = approved()
        frozen = copy.deepcopy(checked)
        notes = dict(schema_version=1, entries={'AAA': dict(objections=[OBJECTION])})
        current = assessment.project(checked, as_of=NOW, objections=[OBJECTION])
        self.assertFalse(current['quality_rank_eligible'])
        self.assertIsNone(current['rating'])
        record = packet(row, checked)
        scan = market_scanner.build_scan(record, as_of=NOW, notes=notes)['rows'][0]
        self.assertIsNone(scan['rating'])
        self.assertEqual(scan['review_status'], 'REVIEW_REQUIRED')
        with tempfile.TemporaryDirectory() as temp:
            Path(temp, 'scanner_notes.json').write_text(json.dumps(notes))
            payload = json.loads(dict(stock_compare.site_pages(temp, {'record': record}, now=NOW))[Path('compare.json')])
        self.assertTrue(payload['rows'][0]['model']['review_required'])
        self.assertIsNone(payload['rows'][0]['model']['rating'])
        self.assertEqual(checked, frozen)

    def test_approval_cannot_precede_quote_or_source_publication(self):
        helper = fixtures.AssessmentIntegrity()
        for changes, reviewed in (({}, '2026-10-20T15:00:00Z'),
                ({'financial_published_at': '2026-10-20T16:05:00Z'}, '2026-10-20T16:00:00Z'),
                ({'financial_published_at': '2026-10-20junk'}, '2026-10-20T16:00:00Z'),
                ({'shares_asof': '2026-10-20T14:00:00'}, '2026-10-20T16:00:00Z')):
            row = complete_row()
            row.update(changes)
            reviews = helper.reviewed(row)
            reviews['entries']['AAA']['reviewed_at'] = reviewed
            with self.subTest(changes=changes, reviewed=reviewed):
                self.assertIsNone(helper.assess(row, reviews=reviews)['rating'])

    def test_proposal_expiry_and_fill_are_bound_to_review(self):
        row, checked = approved()
        with patch.object(engine, 'DATA', {'AAA': row}):
            plan = engine.portfolio_proposal('REFLATION', assessments={'AAA': checked})['positions'][0]['trade_plan']
        self.assertEqual(plan['as_of'], checked['as_of'])
        self.assertEqual(plan['entry_valid_until'], checked['expires_at'])
        for fill_time in ('2026-10-22', '2026-10-21T16:00:01Z', '2026-10-21', '2026-10-20T16:14:59Z'):
            with self.subTest(fill_time=fill_time), self.assertRaises(ValueError):
                portfolio.filled_plan(plan, plan['entry_limit'], fill_time)
        filled = portfolio.filled_plan(plan, plan['entry_limit'], '2026-10-21T15:59:00Z')
        self.assertEqual(filled['next_review'], '2026-11-20')
        self.assertEqual(checked['rating'], 'BUY')

    def test_expired_injected_assessment_is_not_an_entry(self):
        row, checked = approved()
        checked['expires_at'] = '2026-10-20T16:14:00Z'
        with patch.object(engine, 'DATA', {'AAA': row}):
            book = engine.portfolio_proposal('REFLATION', assessments={'AAA': checked})
        self.assertEqual(book['positions'], [])


if __name__ == '__main__':
    unittest.main()
