"""Daily editions keep their four sections, evidence and translations intact."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

import weekly_research as research
from test_weekly_research import example, multilingual


def daily_example():
    issue = example('2026-10-18')
    issue.update(period_start='2026-10-17', period_end='2026-10-18',
                 data_cutoff='2026-10-18T07:40:00+02:00')
    item = issue['items'][0]
    issue['items'] = []
    for section in ('regime', 'usa', 'eu', 'colombia'):
        row = copy.deepcopy(item)
        row.update(section=section, title=f'{section} update',
                   source_url=f'https://example.org/{section}', topics=['macro_regimes'],
                   what_changed='[Sicher] Latest published reading: 2.5%.')
        row['sources'] = [{'title': 'Official release', 'url': row['source_url'],
                           'publication_date': '2026-10-16'}]
        issue['items'].append(row)
    return multilingual(issue)


class DailyPublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'repo'
        self.output = Path(self.temp.name) / 'public'
        for folder in ('weekly-research', 'daily-briefings'):
            (self.root / folder).mkdir(parents=True)
        self.write('weekly-research/config.json', {
            'first_issue_date': '2026-10-16', 'schedule_label': 'Fridays'})
        self.config = {
            'first_issue_date': '2026-10-18', 'schedule_label': 'Daily around 08:00 Berlin',
            'languages': ['es', 'en', 'de'], 'default_language': 'de',
            'verify_translation_claims': True,
            'schedule_labels': {'es': 'Cada día', 'de': 'Täglich'}}
        self.write('daily-briefings/config.json', self.config)
        (self.root / 'index.html').write_text(
            '<!DOCTYPE html><html><body><h1>Scoreboard</h1></body></html>')

    def write(self, path, value):
        (self.root / path).write_text(json.dumps(value), encoding='utf-8')

    def test_four_sections_have_separate_language_archives_and_evidence(self):
        self.write('daily-briefings/2026-10-18.json', daily_example())
        research.build_site(self.root, self.output)
        expected = {'en': ('Regime impact', 'United States', 'European Union', 'Colombia'),
                    'de': ('Regime-Einfluss', 'USA', 'Europäische Union', 'Kolumbien'),
                    'es': ('Impacto en el régimen', 'Estados Unidos', 'Unión Europea', 'Colombia')}
        for lang, headings in expected.items():
            page = (self.output / f'daily-{lang}.html').read_text()
            archive = (self.output / 'daily' / f'2026-10-18-{lang}.html').read_text()
            self.assertIn(f'<html lang="{lang}">', page)
            positions = [page.index(f'{heading} ·') for heading in headings]
            self.assertEqual(positions, sorted(positions))
            for section in ('regime', 'usa', 'eu', 'colombia'):
                self.assertIn(f'href="https://example.org/{section}"', page)
            self.assertIn('2026-10-18T07:40:00+02:00', page)
            self.assertIn(f'href="../daily/2026-10-18-{lang}.html"', archive)
            self.assertIn(f'href="daily/2026-10-18-{lang}.html"', page)
        self.assertIn('Regime-Einfluss ·', (self.output / 'daily.html').read_text())
        for lang in ('en', 'de', 'es'):
            home = (self.output / research.i18n.homepage(lang)).read_text()
            self.assertIn(f'href="daily-{lang}.html"', home)
            self.assertNotIn('data-i18n-missing', home)
        self.assertNotIn('2026-10-18', (self.output / 'research.html').read_text())

    def test_invalid_daily_editions_do_not_replace_the_previous_site(self):
        original = daily_example()
        invalid = []
        for change in ('order', 'missing_section', 'sources', 'unsafe_url', 'cutoff',
                       'future_source', 'translation', 'length'):
            issue = copy.deepcopy(original)
            if change == 'order':
                issue['items'].reverse()
            elif change == 'missing_section':
                for lang in ('es', 'de'):
                    issue['translations'][lang]['items'].pop()
                issue['items'].pop()
            elif change == 'sources':
                issue['items'][0]['sources'] = []
            elif change == 'unsafe_url':
                issue['items'][0]['sources'][0]['url'] = 'javascript:alert(1)'
            elif change == 'cutoff':
                issue['data_cutoff'] = '2026-10-18T07:40:00'
            elif change == 'future_source':
                issue['items'][0]['sources'][0]['publication_date'] = '2026-10-19'
            elif change == 'translation':
                issue['translations']['de']['items'][0]['what_changed'] = '3.5%'
            elif change == 'length':
                issue['summary'] = 'word ' * 901
            invalid.append((change, issue))
        self.output.mkdir()
        old = self.output / 'daily.html'
        old.write_text('Last verified edition')
        for change, issue in invalid:
            with self.subTest(change=change):
                self.write('daily-briefings/2026-10-18.json', issue)
                with self.assertRaises(ValueError):
                    research.build_site(self.root, self.output)
                self.assertEqual(old.read_text(), 'Last verified edition')

    def test_empty_daily_pages_do_not_invent_news(self):
        research.build_site(self.root, self.output)
        for lang in ('es', 'en', 'de'):
            self.assertTrue((self.output / f'daily-{lang}.html').exists())
        page = (self.output / 'daily-en.html').read_text()
        self.assertIn('No edition has been published yet.', page)
        self.assertIn('3–5', page)
        self.assertNotIn('Official release', page)


if __name__ == '__main__':
    unittest.main()
