"""Publication boundaries: content safety, archives and report integrity."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import weekly_research as research


def example(stamp='2026-10-16'):
    return {'schema_version': 1, 'issue_date': stamp, 'period_start': '2026-10-09',
            'period_end': stamp, 'summary': 'A test edition.',
            'priority_review': 'Review the assumptions.', 'items': [{
                'title': 'An example source', 'authors': 'Example institution',
                'publication_date': '2026-10-12', 'source_url': 'https://example.org/paper',
                'topics': ['stock_selection'], 'what_changed': 'New evidence.',
                'investorace_implication': 'A candidate for review.', 'review': 'code',
                'review_question': 'Does the result survive costs?',
                'limitations': 'Small sample.', 'confidence': 'Wahrscheinlich'}]}


class ResearchPublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'repo'
        self.output = Path(self.temp.name) / 'public'
        (self.root / 'weekly-research').mkdir(parents=True)
        self.config = {'schema_version': 1, 'first_issue_date': '2026-10-16',
                       'schedule_label': 'Fridays, around 08:00 Europe/Berlin'}
        self.write('config.json', self.config)
        self.html = '<!DOCTYPE html><html><body><h1>Master Scoreboard</h1></body></html>'
        (self.root / 'index.html').write_text(self.html, encoding='utf-8')

    def write(self, name, value):
        (self.root / 'weekly-research' / name).write_text(json.dumps(value), encoding='utf-8')

    def write_market(self, issue, legacy_dates=None):
        folder = self.root / 'market-briefings'
        folder.mkdir(exist_ok=True)
        config = {'schema_version': 1, 'first_issue_date': '2026-10-12',
                  'schedule_label': 'Montags, gegen 08:00 Europe/Berlin',
                  'legacy_research_dates': legacy_dates or []}
        (folder / 'config.json').write_text(json.dumps(config), encoding='utf-8')
        (folder / f'{issue["issue_date"]}.json').write_text(json.dumps(issue), encoding='utf-8')

    def test_rejects_invalid_or_ambiguous_publication_content(self):
        original = example()
        invalid = []
        for key, value in [('source_url', 'javascript:alert(1)'),
                           ('source_url', 'https://user:secret@example.org'),
                           ('review', 'implement'), ('confidence', 'certain'),
                           ('topics', ['unknown']), ('topics', ['stock_selection'] * 2),
                           ('what_changed', '')]:
            item = copy.deepcopy(original)
            item['items'][0][key] = value
            invalid.append(item)
        invalid.extend([{**original, 'period_end': '2026-10-17'},
                        {**original, 'items': original['items'] * 6},
                        {**original, 'items': original['items'] * 2}])
        for item in invalid:
            with self.subTest(item=item), self.assertRaises(ValueError):
                research.validate_issue(item, '2026-10-16.json')
        with self.assertRaises(ValueError):
            research.validate_issue(original, '2026-10-23.json')

    def test_source_text_is_escaped_and_verdicts_are_visible(self):
        issue = example()
        issue['items'][0]['title'] = '<script>alert("source")</script>'
        issue['items'][0]['what_changed'] = '<img src=x onerror=alert(1)>'
        issue['items'][0]['source_url'] += '?one=1&two=2'
        page = research.render_page(issue, [issue], self.config)
        self.assertNotIn('<script>', page)
        self.assertNotIn('<img src=x', page)
        self.assertIn('&lt;script&gt;', page)
        self.assertIn('?one=1&amp;two=2', page)
        for label in ('Code review', '[Wahrscheinlich]', 'InvestorAce implication', 'Review question'):
            self.assertIn(label, page)

    def test_latest_issue_and_dated_archives_survive_build(self):
        self.write('2026-10-16.json', example())
        quiet = {**example('2026-10-23'), 'items': [], 'summary': 'No qualifying new research.'}
        self.write('2026-10-23.json', quiet)
        research.build_site(self.root, self.output)
        latest = (self.output / 'research.html').read_text()
        old = (self.output / 'research' / '2026-10-16.html').read_text()
        self.assertIn('Edition · 2026-10-23', latest)
        self.assertIn('No qualifying new sources', latest)
        self.assertIn('research/2026-10-16.html', latest)
        self.assertIn('../index.html', old)
        self.assertIn('../research/2026-10-23.html', old)
        self.assertEqual((self.root / 'index.html').read_text(), self.html)
        self.assertIn('href="research.html"', (self.output / 'index.html').read_text())

    def test_empty_page_does_not_invent_an_edition(self):
        research.build_site(self.root, self.output)
        page = (self.output / 'research.html').read_text()
        self.assertIn('Scheduled for 16 October 2026', page)
        self.assertIn('No edition has been published yet.', page)
        self.assertNotIn('selected sources', page)

    def test_existing_pointer_uses_verified_report_not_root_mirror(self):
        (self.root / 'history').mkdir()
        (self.root / 'history' / '_current.json').write_text('{}')
        verified = self.root / 'history' / 'verified.html'
        verified.write_text(self.html.replace('Master Scoreboard', 'Verified report'))
        with patch('evidence.current_build', return_value={'report_path': verified}) as resolve:
            research.build_site(self.root, self.output)
        resolve.assert_called_once_with(self.root / 'history')
        self.assertIn('Verified report', (self.output / 'index.html').read_text())
        self.assertNotIn('Master Scoreboard', (self.output / 'index.html').read_text())

    def test_corrupt_committed_report_cannot_fall_back_to_mirror(self):
        (self.root / 'history').mkdir()
        (self.root / 'history' / '_current.json').write_text('{}')
        with patch('evidence.current_build', side_effect=ValueError('Build report hash mismatch')):
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                research.build_site(self.root, self.output)
        self.assertFalse(self.output.exists())

    def test_nightly_build_requires_a_committed_generation(self):
        with self.assertRaises(FileNotFoundError):
            research.build_site(self.root, self.output, require_committed=True)
        self.assertFalse(self.output.exists())

    def test_invalid_issue_does_not_replace_previously_rendered_site(self):
        self.output.mkdir()
        (self.output / 'index.html').write_text('previous site')
        invalid = example()
        invalid['items'][0]['source_url'] = 'file:///private'
        self.write('2026-10-16.json', invalid)
        with self.assertRaises(ValueError):
            research.build_site(self.root, self.output)
        self.assertEqual((self.output / 'index.html').read_text(), 'previous site')
        self.assertFalse((self.output / 'research.html').exists())

    def test_navigation_is_added_once_and_rejects_truncated_reports(self):
        linked = research.add_research_link(self.html)
        self.assertEqual(research.add_research_link(linked), linked)
        self.assertEqual(linked.count('id="investorace-research-nav"'), 1)
        with self.assertRaises(ValueError):
            research.add_research_link('<html><body>truncated')

    def test_monday_and_friday_keep_separate_latest_issues_and_archives(self):
        friday = {**example(), 'summary': 'Friday research only.'}
        self.write('2026-10-16.json', friday)
        self.write_market({**example('2026-10-12'), 'summary': 'Older Monday market edition.'})
        monday = {**example('2026-10-19'), 'summary': 'Latest Monday market edition.'}
        self.write_market(monday)
        research.build_site(self.root, self.output)
        friday_page = (self.output / 'research.html').read_text()
        monday_page = (self.output / 'market.html').read_text()
        self.assertIn('Friday research only.', friday_page)
        self.assertNotIn('Monday market edition.', friday_page)
        self.assertNotIn('2026-10-19.html', friday_page)
        self.assertIn('Latest Monday market edition.', monday_page)
        self.assertNotIn('Friday research only.', monday_page)
        self.assertNotIn('2026-10-16.html', monday_page)
        self.assertIn('market/2026-10-12.html', monday_page)
        old = (self.output / 'market' / '2026-10-12.html').read_text()
        self.assertIn('../market/2026-10-19.html', old)
        self.assertIn('href="../market.html" aria-current="page"', old)
        self.assertIn('href="../research.html"', old)
        self.assertIn('Montags, gegen 08:00', monday_page)
        self.assertIn('Fridays, around 08:00', friday_page)
        self.assertIn('lang="de"', monday_page)
        self.assertEqual((self.root / 'index.html').read_text(), self.html)

    def test_same_issue_date_does_not_merge_the_two_series(self):
        self.write('2026-10-16.json', {**example(), 'summary': 'Research content.'})
        self.write_market({**example(), 'summary': 'Market content.'})
        research.build_site(self.root, self.output)
        friday = (self.output / 'research' / '2026-10-16.html').read_text()
        monday = (self.output / 'market' / '2026-10-16.html').read_text()
        self.assertIn('Research content.', friday)
        self.assertNotIn('Market content.', friday)
        self.assertIn('Market content.', monday)
        self.assertNotIn('Research content.', monday)

    def test_migrated_monday_url_redirects_without_entering_friday_feed(self):
        self.write('2026-10-11.json', example('2026-10-11'))
        self.write_market(example('2026-10-12'), legacy_dates=['2026-10-12'])
        research.build_site(self.root, self.output)
        friday = (self.output / 'research.html').read_text()
        redirect = (self.output / 'research' / '2026-10-12.html').read_text()
        self.assertNotIn('research/2026-10-12.html', friday)
        self.assertNotIn('Edition · 2026-10-12', friday)
        self.assertIn('content="0;url=../market/2026-10-12.html"', redirect)
        self.assertTrue((self.output / 'market' / '2026-10-12.html').exists())

    def test_redirect_cannot_overwrite_a_friday_issue(self):
        self.write('2026-10-16.json', example())
        self.write_market(example(), legacy_dates=['2026-10-16'])
        with self.assertRaisesRegex(ValueError, 'only to a market edition'):
            research.build_site(self.root, self.output)
        self.assertFalse(self.output.exists())

    def test_invalid_market_issue_does_not_replace_the_published_site(self):
        issue = example('2026-10-12')
        issue['items'][0]['source_url'] = 'javascript:alert(1)'
        self.write_market(issue)
        self.output.mkdir()
        (self.output / 'index.html').write_text('previous site')
        with self.assertRaises(ValueError):
            research.build_site(self.root, self.output)
        self.assertEqual((self.output / 'index.html').read_text(), 'previous site')
        self.assertFalse((self.output / 'research.html').exists())
        self.assertFalse((self.output / 'market.html').exists())

    def test_existing_single_link_navigation_is_upgraded(self):
        old = self.html.replace('<body>', '<body><nav id="investorace-research-nav">'
                               '<a href="research.html">Weekly research</a></nav>')
        updated = research.add_research_link(old)
        self.assertIn('href="market.html"', updated)
        self.assertIn('href="research.html"', updated)
        self.assertEqual(updated.count('id="investorace-research-nav"'), 1)
        self.assertEqual(research.add_research_link(updated), updated)


if __name__ == '__main__':
    unittest.main()
