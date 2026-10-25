"""A research handoff cannot silently change its evidence or become an approval."""
import copy
import hashlib
import json
import re
import subprocess
import unittest

import market_scanner as scanner
from test_market_scanner import ASOF, observation
import test_market_scanner as fixtures


class ReviewPacketTests(unittest.TestCase):
    def scan(self, record=None, notes=None, market=None):
        result = scanner.build_scan(record or observation(), as_of=ASOF,
                                    notes=notes, market=market)
        self.assertIn('review_packets', result, 'Scanner must provide a frozen research handoff')
        return result

    def test_all_roles_receive_the_same_frozen_evidence_without_approval(self):
        packet = self.scan()['review_packets']['universe']['EX']
        snapshot = packet['snapshot']
        encoded = json.dumps(snapshot, sort_keys=True, separators=(',', ':'), allow_nan=False)
        expected = hashlib.sha256(encoded.encode()).hexdigest()
        self.assertEqual(packet['snapshot_sha256'], expected)
        self.assertEqual([r['role'] for r in packet['assignments']], ['data', 'valuation', 'risk'])
        self.assertTrue(all(r['status'] == 'NOT_RUN' and r['snapshot_sha256'] == expected
                            for r in packet['assignments']))
        self.assertEqual(packet['status'], 'NOT_STARTED')
        self.assertFalse(packet['can_approve'])
        self.assertEqual(snapshot['inputs']['fcf'], 80)
        self.assertEqual(snapshot['sources'][0]['id'], 'SRC-001')
        self.assertEqual(snapshot['origin']['as_of'], '2026-10-18T12:00:00+00:00')

    def test_market_and_universe_symbols_cannot_overwrite_each_other(self):
        market = fixtures.MarketSectionTests().audited_market(ticker='EX')
        result = self.scan(market=market)
        packets = result['review_packets']
        self.assertEqual(packets['universe']['EX']['snapshot']['inputs']['fcf'], 80)
        self.assertEqual(packets['market']['EX']['snapshot']['inputs']['metrics']['fcf'], 700e6)
        self.assertNotEqual(packets['market']['EX']['snapshot_sha256'],
                            packets['universe']['EX']['snapshot_sha256'])
        self.assertIsNone(result['market']['candidates'][0]['rating'])
        self.assertIsNone(result['rows'][0]['rating'])

    def test_changed_inputs_or_source_or_objection_invalidate_packet_identity(self):
        original = observation()
        base = self.scan(original)['review_packets']['universe']['EX']['snapshot_sha256']
        changed = copy.deepcopy(original)
        changed['_evidence']['inputs']['EX']['fcf'] = 81
        self.assertNotEqual(base, self.scan(changed)['review_packets']['universe']['EX']['snapshot_sha256'])
        changed = copy.deepcopy(original)
        changed['_source_reviews']['entries']['EX']['valuation']['sources'][0]['url'] = 'https://example.org/new'
        self.assertNotEqual(base, self.scan(changed)['review_packets']['universe']['EX']['snapshot_sha256'])
        notes = dict(schema_version=1, entries={'EX': dict(objections=[dict(id='SHARES',
            severity='major', status='corrected', message='Check new shares.', response='Updated.')])})
        packet = self.scan(original, notes)['review_packets']['universe']['EX']
        self.assertNotEqual(base, packet['snapshot_sha256'])
        self.assertEqual(packet['snapshot']['objections'][0]['status'], 'corrected')
        self.assertFalse(packet['can_approve'])

    def test_missing_values_stay_missing_and_inputs_are_not_modified(self):
        record = observation()
        record['_evidence']['inputs']['EX']['fcf'] = None
        frozen = copy.deepcopy(record)
        packet = self.scan(record)['review_packets']['universe']['EX']
        self.assertIsNone(json.loads(json.dumps(packet, allow_nan=False))['snapshot']['inputs']['fcf'])
        self.assertEqual(record, frozen)

    def test_packet_source_text_remains_inert_in_the_page(self):
        record = observation()
        malicious = '</script><script>window.pwned=true</script>'
        record['_evidence']['inputs']['EX']['boot_note'] = malicious
        result = self.scan(record)
        self.assertEqual(result['review_packets']['universe']['EX']['snapshot']['inputs']['boot_note'], malicious)
        self.assertNotIn(malicious, scanner.render_scan(result))

    def test_download_transport_preserves_numeric_types_and_content_hash(self):
        record = observation()
        record['_evidence']['inputs']['EX'].update(fcf=80.0, tiny=1e-10)
        html = scanner.render_scan(self.scan(record))
        embedded = re.search(r'id="scanner-data">(.*?)</script>', html, re.S).group(1)
        # Exercise the actual browser JSON round trip, which would change 80.0
        # to 80 if the packet itself were parsed and re-serialized there.
        downloaded = subprocess.check_output(['node', '-e',
            'let s="";process.stdin.on("data",x=>s+=x);process.stdin.on("end",()=>'
            'process.stdout.write(JSON.parse(s).review_packets.universe.EX));'],
            input=embedded, text=True)
        packet = json.loads(downloaded)
        expected = hashlib.sha256(json.dumps(packet['snapshot'], sort_keys=True,
            separators=(',', ':'), allow_nan=False).encode()).hexdigest()
        self.assertEqual(packet['snapshot_sha256'], expected)
        self.assertIsInstance(packet['snapshot']['inputs']['fcf'], float)

    def test_invalid_market_candidates_do_not_break_universe_or_page(self):
        for candidates in [[{}], [None], None]:
            with self.subTest(candidates=candidates):
                market = fixtures.market_payload()
                market['candidates'] = candidates
                try:
                    result = self.scan(market=market)
                except (KeyError, TypeError) as exc:
                    self.fail(f'Rejected market data must not break universe export: {exc}')
                self.assertEqual(result['market']['status'], 'INVALID')
                self.assertIn('EX', result['review_packets']['universe'])
                self.assertEqual(result['review_packets']['market'], {})
                self.assertIn('scanner-data', scanner.render_scan(result))

    def test_original_note_sources_and_null_provenance_survive_export(self):
        note = dict(thesis=None, sources=[dict(title=None, url='http://example.org/filing',
                    passage='Original source passage', published_at=None, period='FY2025')])
        notes = dict(schema_version=1, entries={'EX': note})
        packet = self.scan(notes=notes)['review_packets']['universe']['EX']
        self.assertEqual(packet['snapshot']['research'].get('scanner_note'), note)

    def test_macro_history_is_bound_without_duplication_in_every_stock_file(self):
        record = observation()
        macro = dict(ok=True, regime='REFLATION', source_vintage='2026-10-17',
                     input_series={'CPI': list(range(20000))}, path_points=list(range(20000)))
        record['_evidence']['macro'] = macro
        packet = self.scan(record)['review_packets']['universe']['EX']
        self.assertLess(len(json.dumps(packet)), 20000)
        origin = packet['snapshot']['origin']
        self.assertEqual(origin['macro']['regime'], 'REFLATION')
        self.assertNotIn('input_series', origin['macro'])
        expected = hashlib.sha256(json.dumps(macro, sort_keys=True,
            separators=(',', ':'), allow_nan=False).encode()).hexdigest()
        self.assertEqual(origin['macro_full_snapshot_sha256'], expected)


if __name__ == '__main__':
    unittest.main()
