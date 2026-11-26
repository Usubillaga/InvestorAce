import json
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch

from codex_heat.native import DIR, FILES, Panel


class Parse(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tabs = []
        self.panels = []
        self.books = []
        self.urls = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get('role') == 'tab':
            self.tabs.append(a['aria-controls'])
        if a.get('role') == 'tabpanel':
            self.panels.append(a['id'])
        if tag == 'article':
            self.books.append(a['data-book'])
        if tag == 'script' and a.get('src'):
            self.urls.append(a['src'])
        if tag == 'a':
            self.links.append(a.get('href'))


class PanicTabTests(unittest.TestCase):
    def test_native_pages_include_the_accounts_before_javascript(self):
        with tempfile.TemporaryDirectory() as tmp:
            panel = Panel.build(Path(tmp))
            for lang in ('es', 'de', 'en'):
                html = panel.embed('<html><head></head><body><main id="original">Existing report</main></body></html>', lang)
                parsed = Parse()
                parsed.feed(html)
                self.assertEqual(parsed.tabs, ['ia-primary', 'panic-paper'])
                self.assertEqual(parsed.tabs, parsed.panels)
                self.assertEqual(parsed.books, ['original', '5', '6'])
                self.assertIn('Existing report', html)
                self.assertIn('AAPL', panel.languages[lang])
                self.assertIn('panic-paper.js', parsed.urls)
                self.assertIn('index.es.html#panic-paper', parsed.links)
                self.assertNotIn('<iframe', html)
            assets = dict(panel.assets())
            self.assertIn('index.es.html#panic-paper', assets[Path('heat-leaders.html')])
            self.assertIn(Path('heat-archive.en.html'), assets)
            self.assertNotIn('async function account()', assets[Path('heat-archive.en.html')].decode())

    def test_unavailable_source_uses_dated_snapshot_and_never_opens_positions(self):
        with tempfile.TemporaryDirectory() as tmp, patch('codex_heat.native.fetch_json', side_effect=OSError('offline')):
            saved = Panel.build(Path(tmp), refresh=True)
            data = json.loads(dict(saved.assets())[Path('heat-overlap.json')])
            self.assertEqual(data, saved.data['overlap'])
            self.assertEqual(saved.data['claude'], [])

    def test_complete_refresh_accepts_an_explicit_empty_holdings_list(self):
        original, overlap = [json.loads((DIR / name).read_text()) for name in FILES]
        for book in overlap['books'].values():
            book.update(holdings=[], cash=12345, nav=12345, entry=None, pending=None)
        with tempfile.TemporaryDirectory() as tmp, patch(
                'codex_heat.native.fetch_json', side_effect=[{'object': {'sha': 'a' * 40}}, original, overlap]):
            panel = Panel.build(Path(tmp), refresh=True)
        self.assertEqual(panel.data['overlap'], overlap)
