"""Keep optional, scheduled and evidenced cash receipts distinct in a frozen packet."""
import copy
import json
from pathlib import Path
import unittest

import source_review


PACKET = Path(__file__).parent / 'docs/analysis/issuer-events-20261126/packet.json'


class NovemberPaymentEvidence(unittest.TestCase):
    def test_option_and_paid_month_are_not_a_paid_day(self):
        issuers = json.loads(PACKET.read_text())['issuers']
        vis = issuers['VIS']['payment']
        self.assertEqual((vis['amount'], vis['rights_per_new_share']), (1.434, 38))
        self.assertEqual((vis['record_date'], vis['election_end'], vis['payable_date']),
                         ('2026-11-26', '2026-12-09', '2026-12-21'))
        self.assertIsNone(vis['actual_payment_date'])
        payx = issuers['PAYX']['payment']
        self.assertEqual(payx['status'], 'PAYABLE_PASSED_ACTUAL_NOT_VERIFIED')
        self.assertIsNone(payx['actual_payment_date'])
        self.assertEqual(issuers['JD']['payments']['actual_payment_month'], '2026-04')
        self.assertIsNone(issuers['JD']['payments']['actual_payment_date'])
        self.assertIsNone(issuers['BIDU']['payments']['payable_date'])

    def test_quarter_paid_declared_and_tax_distribution_definitions(self):
        issuers = json.loads(PACKET.read_text())['issuers']
        payx = issuers['PAYX']['payments']
        self.assertNotEqual(payx['common_cash_paid'], payx['common_dividends_declared'])
        self.assertAlmostEqual(payx['operating_cash_flow'] - payx['cash_capex'],
                               payx['ocf_minus_cashcapex_derived'])
        fps = issuers['FPS']['payments']
        self.assertEqual(fps['tax_distributions_to_noncontrolling_opco_holders'], 0)
        self.assertIsNone(fps['common_cash_paid'])
        self.assertIsNone(fps['preferred_cash_paid'])

    def test_existing_gate_rejects_future_cash_confirmation(self):
        packet = json.loads(PACKET.read_text())
        register = source_review.empty()
        register.update(as_of='2026-11-26', window_start='2026-08-28', window_end='2026-11-26')
        monitoring = copy.deepcopy(packet['issuers']['VIS']['monitoring'])
        register['entries']['VIS'] = dict(
            issuer='Viscofan, S.A.', listing='VIS.MC',
            valuation=dict(status='PARTIAL', reason='Fixture scope remains partial.', sources=[]),
            insider=dict(status='PARTIAL', reason='Fixture scope remains partial.', sources=[],
                         transactions=[], limitations=['No complete ownership window.']),
            monitoring=monitoring)
        source_review.load(json.dumps(register))
        monitoring['next_common_payment']['actual_payment_date'] = '2026-12-21'
        with self.assertRaises(ValueError):
            source_review.load(json.dumps(register))


if __name__ == '__main__':
    unittest.main()
