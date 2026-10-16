"""Regression tests for the rendered report's German and Spanish editions."""
import base64
import importlib
import importlib.util
import re
import unittest
from html.parser import HTMLParser
from unittest.mock import patch


def module():
    # The initial red run must fail as an assertion when localization is absent.
    if importlib.util.find_spec('i18n') is None:
        raise AssertionError('The scoreboard localization module is not implemented')
    return importlib.import_module('i18n')


class Tags(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.tags = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


def document(body, script=''):
    return ('<!DOCTYPE html><html lang="en"><head><title>InvestorAce &middot; Master Scoreboard</title>'
            '<style>#test{content:"BUY";color:red}</style></head><body>' + body
            + ('<script>' + script + '</script>' if script else '') + '</body></html>')


class Localization(unittest.TestCase):
    def test_three_accessible_static_language_links_and_current_page(self):
        for language, path, heading in [('en', 'index.html', 'Master Scoreboard'),
                                        ('de', 'index.de.html', 'Gesamtübersicht'),
                                        ('es', 'index.es.html', 'Panel general')]:
            with self.subTest(language=language):
                i18n = module()
                result = i18n.localize(document('<h1>Master Scoreboard</h1>'), language)
                parsed = Tags(result)
                navs = [a for tag, a in parsed.tags if tag == 'nav' and a.get('id') == 'investorace-language-nav']
                self.assertEqual(len(navs), 1)
                self.assertTrue(navs[0].get('aria-label'))
                links = [a for tag, a in parsed.tags if tag == 'a' and a.get('hreflang')]
                self.assertEqual({a['href'] for a in links}, {'index.html', 'index.de.html', 'index.es.html'})
                self.assertEqual([a['href'] for a in links if a.get('aria-current') == 'page'], [path])
                self.assertEqual(i18n.homepage(language), path)
                self.assertIn('<html lang="' + language + '">', result)
                self.assertIn(heading, result)
                for label in ('English', 'Deutsch', 'Español'):
                    self.assertIn(label, result)

    def test_english_is_canonical_and_navigation_is_idempotent(self):
        original = document('<h1>Master Scoreboard</h1><p>USD 12,345.6789 · 2026-10-15</p>')
        first = module().localize(original)
        self.assertEqual(module().localize(first), first)
        stripped = re.sub(r'<nav\b[^>]*id="investorace-language-nav"[\s\S]*?</nav>', '', first)
        self.assertEqual(stripped, original)

    def test_translates_prose_dynamic_dates_and_missing_states(self):
        body = ('<h2>Score explanations and entry observations</h2>'
                '<p>Legacy Score includes valuation. Regime Fit includes a cover-based duration proxy. '
                'Business Quality uses growth, profitability, cash conversion, balance sheet and dilution; '
                'it is a separate heuristic and does not change existing actions or rankings.</p>'
                '<p>76/76 valid quotes; 2 held positions without a quote. Rows without a valid quote '
                'show NO QUOTE and have no current action signal.</p>'
                '<p>Last eligible bar: 2026-10-14 · Calculated: 2026-10-15T08:30:00Z</p>'
                '<span>NO SCORE</span><span>UNAVAILABLE</span><span>NO_NEW_SIGNAL</span>'
                '<p>Refresh by 2026-10-22</p><p>Review every 30 days</p>'
                '<p>90–180 days after fill</p><p>21 / 76 observations available</p>')
        for language in ('de', 'es'):
            result = module().localize(document(body), language)
            for english in ('Score explanations and entry observations', 'Legacy Score includes valuation.',
                            'valid quotes', 'held positions without a quote', 'Last eligible bar:',
                            'Calculated:', 'NO SCORE', 'UNAVAILABLE', 'NO_NEW_SIGNAL', 'Refresh by',
                            'Review every', 'days after fill', 'observations available'):
                self.assertNotIn(english, result)
            for value in ('76/76', '2026-10-14', '2026-10-15T08:30:00Z', '2026-10-22', '90–180', '21 / 76'):
                self.assertIn(value, result)

    def test_does_not_change_financial_data_identifiers_links_or_script_keys(self):
        body = ('<table id="prices"><tr><td class="tk">BUY</td><td>12,345.6789 USD</td>'
                '<td>103.25 GBp</td><td>6.5%</td></tr></table>'
                '<a href="https://issuer.example/BUY?rate=0.60#REFLATION">Annual report 2026</a>'
                '<p class="decision-meta">Timing contract: experimental-timing-v2 · Input SHA-256: a0b123</p>')
        script = ("const DATA = {REFLATION:[1.25,3],GOLDILOCKS:[7.5]};"
                  "const QT=[{quadrant:'REFLATION',g:1.2,i:3.4}];"
                  "if (event === 'BUY') window.x = DATA.REFLATION;"
                  "new Chart(el,{label:'Reflation',data:DATA.REFLATION});")
        for language in ('de', 'es'):
            result = module().localize(document(body, script), language)
            for preserved in ('id="prices"', '<td class="tk">BUY</td>', '12,345.6789 USD',
                              '103.25 GBp', '6.5%', 'https://issuer.example/BUY?rate=0.60#REFLATION',
                              'Annual report 2026', 'experimental-timing-v2', 'a0b123',
                              'const DATA = {REFLATION:[1.25,3],GOLDILOCKS:[7.5]};',
                              "quadrant:'REFLATION'", "event === 'BUY'", 'data:DATA.REFLATION',
                              '#test{content:"BUY";color:red}'):
                self.assertIn(preserved, result)

    def test_chart_tooltips_and_form_feedback_are_translated_without_changing_behavior(self):
        script = ("out.value = 'Enter a Yahoo ticker first, e.g. ROAD or ASML.AS.';"
                  "out.value = key + ' is already in the model.';"
                  "link.textContent = 'Open GitHub issue for ' + t + ' \\u2192';"
                  "x:{title:{display:true,text:'rank (1 = best)'}};"
                  "ctx.fillText('RECESSION', (a.left+zx)/2, a.bottom-10);"
                  "if (KNOWN.includes(key)) { return false; }")
        for language in ('de', 'es'):
            result = module().localize(document('<input placeholder="e.g. ASML.AS" aria-label="Add a ticker">', script), language)
            for original in ('Enter a Yahoo ticker first', ' is already in the model.', 'Open GitHub issue for ',
                             'rank (1 = best)', "fillText('RECESSION'"):
                self.assertNotIn(original, result)
            for preserved in ('ROAD', 'ASML.AS', "if (KNOWN.includes(key)) { return false; }"):
                self.assertIn(preserved, result)

    def test_hidden_ziel_payload_is_translated_recursively(self):
        inner = ('<div class="box"><h2>Your book as one line</h2><p>weighted score '
                 '<b>7.25</b> · weighted cover <b>58%</b></p><canvas id="rwChart"></canvas></div>')
        encoded = base64.b64encode(inner.encode()).decode()
        for language, heading in [('de', 'Ihr Portfolio in einer Zeile'), ('es', 'Su cartera en una línea')]:
            result = module().localize(document('<div id="zielBox"></div>', 'const ZP = "' + encoded + '";'), language)
            payload = re.search(r'const ZP = "([A-Za-z0-9+/=]+)"', result).group(1)
            decoded = base64.b64decode(payload).decode()
            self.assertIn(heading, decoded)
            self.assertNotIn('weighted score', decoded)
            self.assertIn('<b>7.25</b>', decoded)
            self.assertIn('<b>58%</b>', decoded)
            self.assertIn('id="rwChart"', decoded)
            self.assertNotIn('investorace-language-nav', decoded)

    def test_research_navigation_uses_matching_language(self):
        body = ('<nav id="investorace-research-nav" aria-label="Research">'
                '<a href="market.html">Montagsbriefing ↗</a>'
                '<a href="research.html">Friday research ↗</a></nav>')
        for language, market, research in [('en', 'market-en.html', 'research.html'),
                                            ('de', 'market-de.html', 'research-de.html'),
                                            ('es', 'market-es.html', 'research-es.html')]:
            result = module().localize(document(body), language)
            self.assertIn('href="' + market + '"', result)
            self.assertIn('href="' + research + '"', result)

    def test_original_source_notes_remain_verbatim_and_are_labelled(self):
        source = 'Issuer source says 12.5% FCF; use neither proxy as a forecast.'
        body = ('<details id="review-TEST"><summary>TEST · Issuer · PARTIAL</summary>'
                '<p><b>Valuation source check: PARTIAL</b><br>' + source + '</p>'
                '<p><a href="https://issuer.example/report">Quarterly Results 2026</a></p></details>')
        for language, label in [('de', 'Originaltext'), ('es', 'Texto original')]:
            result = module().localize(document(body), language)
            self.assertIn(source, result)
            self.assertIn('Quarterly Results 2026', result)
            self.assertIn(label, result)

    def test_source_record_words_and_document_titles_are_not_ui_labels(self):
        body = ('<div id="filing-BUY"><b>BUY · PARTIAL</b><p>Growth</p></div>'
                '<details id="review-BUY"><summary>BUY · Growth · PARTIAL</summary>'
                '<p><a href="https://issuer.example/report">Growth</a></p>'
                '<table><thead><tr><th>Transaction</th><th>Filed</th>'
                '<th>Owner / role</th><th>Disclosed type</th></tr></thead>'
                '<tbody><tr><td>2026-10-14</td><td>2026-10-15</td>'
                '<td>HOLD</td><td>Gift [G]</td></tr></tbody></table></details>')
        for language in ('de', 'es'):
            result = module().localize(document(body), language)
            self.assertIn('BUY · ', result)
            self.assertIn('<p>Growth</p>', result)
            self.assertIn('>Growth</a>', result)
            self.assertIn('<td>HOLD</td>', result)
            self.assertNotIn('>Gift [G]</td>', result)

    def test_inline_ticker_lists_are_preserved_when_the_labels_translate(self):
        body = ('<p>Held positions missing quotes: BUY, SELL, HOLD</p>'
                '<p>Manual discount-rate fallbacks: BUY: manual rate fallback: no valid beta inputs</p>')
        for language in ('de', 'es'):
            result = module().localize(document(body), language)
            self.assertIn('BUY, SELL, HOLD', result)
            self.assertIn('BUY: ', result)
            self.assertNotIn('Held positions missing quotes:', result)
            self.assertNotIn('Manual discount-rate fallbacks:', result)

    def test_disclosed_codes_and_market_identifiers_have_complete_ui_coverage(self):
        body = ('<p>VIX</p><details id="review-TEST"><summary>TEST · Issuer · PARTIAL</summary>'
                '<table><thead><tr><th>Disclosed type</th></tr></thead><tbody>'
                '<tr><td>Employee fund subscription [AMF_ACQUISITION_EMPLOYEE_FCPE_SUBSCRIPTION]</td></tr>'
                '<tr><td>Sale of shares from a prior award plan [AMF_DISPOSAL_SHARE_PLAN_ORIGIN]</td></tr>'
                '</tbody></table></details>')
        self.assertEqual(module().translation_gaps(document(body)), [])
        for language in ('de', 'es'):
            result = module().localize(document(body), language)
            self.assertIn('VIX', result)
            self.assertIn('[AMF_ACQUISITION_EMPLOYEE_FCPE_SUBSCRIPTION]', result)
            self.assertIn('[AMF_DISPOSAL_SHARE_PLAN_ORIGIN]', result)
            self.assertNotIn('Employee fund subscription', result)
            self.assertNotIn('Sale of shares from a prior award plan', result)

    def test_full_report_first_party_text_inventory_has_no_gaps(self):
        # Uses actual renderers and model rows; network entry points are inert.
        i18n = module()
        from test_framework_contract import engine
        import source_review
        with patch.object(engine, 'sector_performance', return_value={}), \
             patch.object(engine, 'regime_history', return_value=([], {})), \
             patch.object(engine, 'forward_run', return_value={
                 'ok': False, 'note': 'no frozen cohort yet; build a validated snapshot first'}):
            report = engine.build_html(macro={'ok': False, 'note': 'no market data'}, write=False,
                                       monitoring={'entries': {}}, reviews=source_review.empty())
        self.assertEqual(i18n.translation_gaps(report), [],
                         'New first-party report prose requires catalog coverage')

    def test_unsupported_language_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'language'):
            module().localize(document(''), 'fr')
        with self.assertRaisesRegex(ValueError, 'language'):
            module().homepage('fr')


if __name__ == '__main__':
    unittest.main()
