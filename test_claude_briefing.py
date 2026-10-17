"""The Claude daily edition is published beside the ChatGPT one, without a word limit."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

import weekly_research as research
from test_daily_briefing import daily_example


class ClaudeDailyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'repo'
        self.output = Path(self.temp.name) / 'public'
        for folder in ('weekly-research', 'daily-briefings', 'claude-briefings'):
            (self.root / folder).mkdir(parents=True)
        self.write('weekly-research/config.json', {
            'first_issue_date': '2026-10-16', 'schedule_label': 'Fridays'})
        config = {
            'first_issue_date': '2026-10-17', 'schedule_label': 'Daily around 08:00 Berlin',
            'languages': ['es', 'en', 'de'], 'default_language': 'de',
            'verify_translation_claims': True,
            'schedule_labels': {'es': 'Cada día', 'de': 'Täglich'}}
        self.write('daily-briefings/config.json', config)
        self.write('claude-briefings/config.json', config)
        (self.root / 'index.html').write_text(
            '<!DOCTYPE html><html><body><h1>Scoreboard</h1></body></html>')

    def write(self, path, value):
        (self.root / path).write_text(json.dumps(value), encoding='utf-8')

    def long_edition(self):
        issue = daily_example()
        issue['summary'] = 'word ' * 950
        for lang in ('es', 'de'):
            issue['translations'][lang]['summary'] = 'palabra ' * 950
        return issue

    def test_both_feeds_publish_side_by_side(self):
        self.write('daily-briefings/2026-10-18.json', daily_example())
        self.write('claude-briefings/2026-10-18.json', daily_example())
        research.build_site(self.root, self.output)
        for lang in ('es', 'en', 'de'):
            claude = (self.output / f'claude-daily-{lang}.html').read_text()
            self.assertIn(f'<html lang="{lang}">', claude)
            self.assertIn(f'href="daily-{lang}.html"', claude)
            self.assertIn(f'href="claude-daily/2026-10-18-{lang}.html"', claude)
            self.assertTrue((self.output / 'claude-daily' / f'2026-10-18-{lang}.html').exists())
            self.assertIn(f'href="claude-daily-{lang}.html"',
                          (self.output / f'daily-{lang}.html').read_text())
            home = (self.output / research.i18n.homepage(lang)).read_text()
            self.assertIn(f'href="claude-daily-{lang}.html"', home)
            self.assertIn(f'href="daily-{lang}.html"', home)
            self.assertNotIn('data-i18n-missing', home)
        self.assertIn('Claude-Tagesbericht', (self.output / 'claude-daily.html').read_text())

    def test_claude_edition_has_no_word_limit_but_daily_keeps_it(self):
        self.write('claude-briefings/2026-10-18.json', self.long_edition())
        research.build_site(self.root, self.output)
        self.assertIn('word word', (self.output / 'claude-daily-en.html').read_text())
        self.write('daily-briefings/2026-10-18.json', self.long_edition())
        with self.assertRaises(ValueError):
            research.build_site(self.root, self.output)

    def test_claude_edition_keeps_the_evidence_contract(self):
        issue = copy.deepcopy(daily_example())
        issue['items'][0]['sources'] = []
        self.write('claude-briefings/2026-10-18.json', issue)
        with self.assertRaises(ValueError):
            research.build_site(self.root, self.output)

    def test_feed_without_editions_shows_schedule(self):
        research.build_site(self.root, self.output)
        self.assertIn('No edition has been published yet.',
                      (self.output / 'claude-daily-en.html').read_text())


if __name__ == '__main__':
    unittest.main()
