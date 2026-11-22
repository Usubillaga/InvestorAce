"""Issuer cutoffs and partial event attempts must not refresh older reviews."""
import copy
import json
import unittest

import source_review as sr


def fixture():
    return dict(schema='source-reviews-v1', as_of='2026-11-21',
                window_start='2026-07-16', window_end='2026-10-14',
                entries={'OLD': dict(issuer='Old issuer', listing='OLD / USD',
                    valuation=dict(status='PARTIAL', reason='Cash-flow scope unresolved.', sources=[]),
                    insider=dict(status='PARTIAL', reason='Incomplete window.', sources=[],
                                 coverage={'complete': False}, limitations=['No complete export.'],
                                 transactions=[]))})


class EntryDates(unittest.TestCase):
    def test_legacy_entry_keeps_old_insider_cutoff_when_register_date_advances(self):
        doc = sr.load(json.dumps(fixture()))
        self.assertIn('2026-10-14', sr.insider_cell('OLD', doc))
        self.assertNotIn('2026-11-21', sr.insider_cell('OLD', doc))
        html = sr.panel({'OLD': {}}, doc)
        self.assertIn('individual review dates', html)
        self.assertIn('Individual valuation check date not recorded', html)

    def test_new_entry_uses_own_window_without_rewriting_legacy_entry(self):
        doc = fixture()
        newer = copy.deepcopy(doc['entries']['OLD'])
        newer.update(as_of='2026-11-20', reviewed_at='2026-11-20',
                     window_start='2026-08-22', window_end='2026-11-20')
        newer['insider']['transactions'] = [dict(transaction_date='2026-11-19',
            filing_date='2026-11-20', owner='Owner', code='A', shares=1, price=0,
            source_url='https://www.sec.gov/filing')]
        doc['entries']['NEW'] = newer
        loaded = sr.load(json.dumps(doc))
        self.assertEqual(loaded['entries']['OLD'], fixture()['entries']['OLD'])
        self.assertIn('2026-11-20', sr.insider_cell('NEW', loaded))
        self.assertIn('Insider window 2026-08-22 to 2026-11-20', sr.panel({'NEW': {}}, loaded))
        newer['insider']['transactions'][0]['transaction_date'] = '2026-08-21'
        with self.assertRaises(ValueError):
            sr.load(json.dumps(doc))

    def test_issuer_cutoff_rejects_later_filing_and_section_check(self):
        for change in ({'reviewed_at': '2026-11-22'},
                       {'as_of': '2026-11-22'}, {'window_end': '2026-11-22'}):
            doc = fixture()
            doc['entries']['OLD'].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                sr.load(json.dumps(doc))
        doc = fixture()
        entry = doc['entries']['OLD']
        entry.update(as_of='2026-10-14', reviewed_at='2026-10-14')
        entry['insider']['transactions'] = [dict(transaction_date='2026-10-13',
            filing_date='2026-10-15', owner='Owner', code='A',
            source_url='https://www.sec.gov/filing')]
        with self.assertRaisesRegex(ValueError, 'Filing postdates'):
            sr.load(json.dumps(doc))
        entry['insider']['transactions'] = []
        entry['valuation']['reviewed_at'] = '2026-10-15'
        with self.assertRaisesRegex(ValueError, 'Section check postdates'):
            sr.load(json.dumps(doc))

    def test_partial_monitoring_has_separate_dates_without_refreshing_old_insider(self):
        doc = fixture()
        doc['entries']['OLD']['monitoring'] = self.monitoring()
        loaded = sr.load(json.dumps(doc))
        self.assertIn('2026-10-14', sr.insider_cell('OLD', loaded))
        html = sr.panel({'OLD': {}}, loaded)
        self.assertIn('Event/payment monitoring: PARTIAL', html)
        self.assertIn('As of 2026-11-22', html)
        self.assertIn('does not refresh the valuation or insider checks', html)
        self.assertIn('https://example.com/filing', html)
        self.assertIn('Cash paid not established.', html)

    @staticmethod
    def monitoring():
        return dict(as_of='2026-11-22', attempted_at='2026-11-22T08:00:00+00:00',
                    window_start='2026-08-24', window_end='2026-11-22', coverage='PARTIAL',
                    sources=[dict(url='https://example.com/filing', title='Original report')],
                    gap='Cash paid not established.', next_check_date='2026-11-23')

    def test_invalid_monitoring_is_blocked_before_render(self):
        for change in ({'coverage': 'CHECKED_NO_EVENTS'}, {'window_start': '2026-12-01'},
                       {'attempted_at': '2026-11-22T08:00:00'}, {'as_of': 'bad'},
                       {'sources': [dict(url='javascript:alert(1)', title='Bad')]},
                       {'next_check_date': '2026-11-21'}, {'gap': ''}):
            doc = fixture()
            doc['entries']['OLD']['monitoring'] = dict(self.monitoring(), **change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                sr.load(json.dumps(doc))

    def test_unknown_payment_fields_and_separate_declared_dates_are_preserved(self):
        doc = fixture()
        monitoring = self.monitoring()
        payment = dict(declared_on=None, announced_on='2026-11-20', record_date=None,
                       payable_date='2026-12-01', actual_payment_date=None, amount=None,
                       currency='CAD', status='DECLARED_NOT_PAID')
        monitoring.update(next_common_payment=payment,
                          payments={'preferred_cash_paid': None, 'common_cash_paid': 0})
        doc['entries']['OLD']['monitoring'] = monitoring
        self.assertEqual(sr.load(json.dumps(doc))['entries']['OLD']['monitoring'], monitoring)

    def test_invalid_next_payment_metadata_is_rejected(self):
        for payment in ([], {'record_date': 'bad'}, {'amount': True}, {'amount': -1},
                        {'amount': float('inf')}, {'currency': 3},
                        {'actual_payment_date': '2026-11-23'},
                        {'status': 'DECLARED_NOT_PAID', 'actual_payment_date': '2026-11-21'}):
            doc = fixture()
            doc['entries']['OLD']['monitoring'] = dict(self.monitoring(), next_common_payment=payment)
            with self.subTest(payment=payment), self.assertRaises(ValueError):
                sr.load(json.dumps(doc))

    def test_cash_paid_recognized_fields_reject_invalid_amounts(self):
        for field in ('preferred_cash_paid', 'common_cash_paid'):
            for amount in (True, -1, float('inf'), '10'):
                for payments in ({field: amount}, [{'key': field, 'value': amount}]):
                    doc = fixture()
                    doc['entries']['OLD']['monitoring'] = dict(self.monitoring(), payments=payments)
                    with self.subTest(field=field, amount=amount, payments=payments), self.assertRaises(ValueError):
                        sr.load(json.dumps(doc))


if __name__ == '__main__':
    unittest.main()
