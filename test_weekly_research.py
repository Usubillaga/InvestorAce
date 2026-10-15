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


def multilingual(issue):
    value = copy.deepcopy(issue)
    value['translations'] = {}
    for language in ('es', 'de'):
        value['translations'][language] = {
            'summary': f'{language}: translated summary.',
            'priority_review': f'{language}: translated priority.',
            'items': [{'source_url': item['source_url'],
                       **{field: f'{language}: {item[field]}' for field in research.TRANSLATED_FIELDS}}
                      for item in issue['items']],
        }
    return value


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

    def require_languages(self):
        self.config.update(languages=['es', 'en', 'de'],
                           schedule_labels={'es': 'Viernes a las 08:00', 'de': 'Freitags um 08:00'})
        self.write('config.json', self.config)

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
        for label in ('Code review', '[Likely]', 'InvestorAce implication', 'Review question'):
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

    def test_requires_complete_translations_and_preserves_source_order(self):
        original = multilingual(example())
        research.validate_issue(original, '2026-10-16.json', ('es', 'en', 'de'))
        mutations = []
        for language in ('es', 'de'):
            incomplete = copy.deepcopy(original)
            del incomplete['translations'][language]
            mutations.append(incomplete)
        for key, value in [('source_url', 'https://example.org/other'), ('title', ''), ('review', 'neither')]:
            invalid = copy.deepcopy(original)
            invalid['translations']['es']['items'][0][key] = value
            mutations.append(invalid)
        invalid = copy.deepcopy(original)
        invalid['translations']['de']['items'] = []
        mutations.append(invalid)
        for item in mutations:
            with self.subTest(item=item), self.assertRaises(ValueError):
                research.validate_issue(item, '2026-10-16.json', ('es', 'en', 'de'))

    def test_multilingual_pages_keep_language_through_overview_and_archive_links(self):
        self.require_languages()
        self.write('2026-10-16.json', multilingual(example()))
        self.write_market({**example('2026-10-12'), 'summary': '[Sicher] Monday only.'})
        research.build_site(self.root, self.output)
        for language, label in [('es', 'Revisar el código'), ('en', 'Code review'), ('de', 'Code prüfen')]:
            page = (self.output / research.research_path(language=language)).read_text()
            old = (self.output / research.research_path('2026-10-16', language)).read_text()
            with self.subTest(language=language):
                self.assertIn(f'<html lang="{language}">', page)
                self.assertIn(label, page)
                self.assertIn('https://example.org/paper', page)
                self.assertIn(research.research_path('2026-10-16', language), page)
                self.assertIn('../' + research.research_path(language=language), old)
                self.assertIn('lang="es" hreflang="es"', old)
                self.assertIn('../research/2026-10-16-de.html', old)
                if language != 'en':
                    self.assertIn(f'{language}: translated summary.', page)
                    self.assertIn(f'{language}: translated priority.', page)
                self.assertNotIn('Monday only.', page)
        monday = (self.output / 'market.html').read_text()
        self.assertIn('[Sicher] Monday only.', monday)
        self.assertNotIn('class="languages"', monday)

    def test_translated_text_is_escaped_without_mutating_facts(self):
        issue = multilingual(example())
        issue['translations']['es']['items'][0]['title'] = '<script>unsafe</script>'
        original = copy.deepcopy(issue)
        page = research.render_page(issue, [issue], self.config, language='es')
        self.assertIn('&lt;script&gt;unsafe&lt;/script&gt;', page)
        self.assertNotIn('<script>', page)
        localized = research.localized_issue(issue, 'es')
        for key in ('source_url', 'review', 'confidence', 'topics', 'authors'):
            self.assertEqual(localized['items'][0][key], issue['items'][0][key])
        self.assertEqual(issue, original)

    def test_missing_translation_blocks_publication_before_site_replacement(self):
        self.require_languages()
        self.write('2026-10-16.json', example())
        self.output.mkdir()
        (self.output / 'index.html').write_text('previous site')
        with self.assertRaisesRegex(ValueError, 'Missing required es'):
            research.build_site(self.root, self.output)
        self.assertEqual((self.output / 'index.html').read_text(), 'previous site')
        self.assertFalse((self.output / 'research.html').exists())

    def test_empty_edition_has_translated_summary_and_priority_in_every_language(self):
        self.require_languages()
        issue = multilingual({**example(), 'items': []})
        self.write('2026-10-16.json', issue)
        research.build_site(self.root, self.output)
        for language in ('es', 'de'):
            page = (self.output / research.research_path(language=language)).read_text()
            self.assertIn(f'{language}: translated summary.', page)
            self.assertIn(f'{language}: translated priority.', page)
            self.assertEqual(page.count('<article>'), 0)

    def test_monday_and_friday_language_archives_remain_separate(self):
        self.require_languages()
        self.write('2026-10-16.json', multilingual(example()))
        issue = multilingual(example('2026-10-12'))
        issue['summary'] = 'Monday English.'
        issue['translations']['es']['summary'] = 'Lunes en español.'
        issue['translations']['de']['summary'] = 'Montag auf Deutsch.'
        self.write_market(issue)
        path = self.root / 'market-briefings' / 'config.json'
        config = json.loads(path.read_text())
        config.update(languages=['es', 'en', 'de'], default_language='de',
                      verify_translation_claims=True,
                      schedule_labels={'es': 'Lunes a las 08:00', 'de': 'Montags um 08:00'})
        path.write_text(json.dumps(config))
        research.build_site(self.root, self.output)
        for lang in ('es', 'en', 'de'):
            monday = (self.output / research.page_path('market', language=lang)).read_text()
            old = (self.output / research.page_path('market', '2026-10-12', lang)).read_text()
            friday = (self.output / research.research_path(language=lang)).read_text()
            self.assertIn(f'<html lang="{lang}">', monday)
            self.assertIn(research.page_path('market', '2026-10-12', lang), monday)
            self.assertIn('../' + research.page_path('market', language=lang), old)
            self.assertNotIn('market/2026-10-12', friday)
            for other in ('es', 'en', 'de'):
                self.assertIn('../' + research.page_path('market', '2026-10-12', other), old)
        self.assertIn('Montag auf Deutsch.', (self.output / 'market.html').read_text())

    def test_monday_requires_complete_languages_before_publication(self):
        self.write_market(example('2026-10-12'))
        path = self.root / 'market-briefings' / 'config.json'
        config = json.loads(path.read_text())
        config.update(languages=['es', 'en', 'de'],
                      schedule_labels={'es': 'Lunes', 'de': 'Montags'})
        path.write_text(json.dumps(config))
        self.output.mkdir()
        (self.output / 'index.html').write_text('previous site')
        with self.assertRaisesRegex(ValueError, 'Missing required es'):
            research.build_site(self.root, self.output)
        self.assertEqual((self.output / 'index.html').read_text(), 'previous site')
        self.assertFalse((self.output / 'market-en.html').exists())

    def test_monday_translations_preserve_numbers_signs_quarters_and_confidence(self):
        source = example('2026-10-12')
        source['items'][0]['what_changed'] = '[Sicher] Yield 5.24%; loss −0.9%; S&P-500 +1.2%; Q3.'
        issue = multilingual(source)
        issue['translations']['es']['items'][0]['what_changed'] = (
            '[Sicher] Rendimiento 5,24%; pérdida −0,9%; S&P 500 +1,2%; Q3.')
        research.validate_issue(issue, '2026-10-12.json', ('es', 'en', 'de'), True)
        for text in ('[Sicher] Yield 5.25%; loss −0.9%; S&P-500 +1.2%; Q3.',
                     '[Sicher] Yield 5.24%; loss +0.9%; S&P-500 +1.2%; Q3.',
                     '[Sicher] Yield 5.24%; loss −0.9%; S&P-500 +1.2%; Q4.',
                     '[Wahrscheinlich] Yield 5.24%; loss −0.9%; S&P-500 +1.2%; Q3.'):
            invalid = copy.deepcopy(issue)
            invalid['translations']['es']['items'][0]['what_changed'] = text
            with self.subTest(text=text), self.assertRaises(ValueError):
                research.validate_issue(invalid, '2026-10-12.json', ('es', 'en', 'de'), True)

    def test_monday_translated_authors_do_not_override_source_metadata(self):
        issue = multilingual(example('2026-10-12'))
        issue['translations']['es']['items'][0]['authors'] = 'Institución de ejemplo'
        research.validate_issue(issue, '2026-10-12.json', ('es', 'en', 'de'), True)
        localized = research.localized_issue(issue, 'es')
        for key in ('source_url', 'review', 'confidence', 'topics'):
            self.assertEqual(localized['items'][0][key], issue['items'][0][key])
        invalid = copy.deepcopy(issue)
        invalid['translations']['es']['items'][0]['review'] = 'neither'
        with self.assertRaises(ValueError):
            research.validate_issue(invalid, '2026-10-12.json', ('es', 'en', 'de'), True)

    def test_quiet_monday_edition_keeps_all_three_languages(self):
        issue = multilingual({**example('2026-10-12'), 'items': []})
        self.write_market(issue)
        path = self.root / 'market-briefings' / 'config.json'
        config = json.loads(path.read_text())
        config.update(languages=['es', 'en', 'de'],
                      schedule_labels={'es': 'Lunes', 'de': 'Montags'})
        path.write_text(json.dumps(config))
        research.build_site(self.root, self.output)
        for lang in ('es', 'en', 'de'):
            self.assertTrue((self.output / research.page_path('market', language=lang)).exists())
            self.assertTrue((self.output / research.page_path('market', '2026-10-12', lang)).exists())


    def test_scoreboard_languages_derive_from_verified_report_without_changing_facts(self):
        self.require_languages()
        (self.root / 'history').mkdir()
        (self.root / 'history' / '_current.json').write_text('{}')
        verified = self.root / 'history' / 'verified.html'
        source = ('<!DOCTYPE html><html lang="en"><head><title>InvestorAce · Master Scoreboard</title>'
                  '</head><body><h1>Master Scoreboard</h1><table><tbody>'
                  '<tr data-ticker="ASML"><td class="tk">ASML</td><td class="num">123.45</td>'
                  '<td class="num">-2.42%</td></tr></tbody></table>'
                  '<a href="https://example.org/filing?x=1&amp;y=2">Original source</a>'
                  '<p>Verified generation</p></body></html>')
        verified.write_text(source, encoding='utf-8')
        with patch('evidence.current_build', return_value={'report_path': verified}) as resolve:
            research.build_site(self.root, self.output)
        resolve.assert_called_once_with(self.root / 'history')
        for language, filename in [('en', 'index.html'), ('de', 'index.de.html'),
                                   ('es', 'index.es.html')]:
            page = (self.output / filename).read_text(encoding='utf-8')
            with self.subTest(language=language):
                self.assertIn(f'<html lang="{language}">', page)
                self.assertEqual(page.count('id="investorace-language-nav"'), 1)
                self.assertIn('data-ticker="ASML"', page)
                self.assertIn('>ASML</td>', page)
                self.assertIn('>123.45</td>', page)
                self.assertIn('>-2.42%</td>', page)
                self.assertIn('https://example.org/filing?x=1&amp;y=2', page)
                self.assertIn('Verified generation', page)
                for destination in ('index.html', 'index.de.html', 'index.es.html'):
                    self.assertIn(f'href="{destination}"', page)
                if language != 'en':
                    self.assertNotIn('Master Scoreboard', page)
                    self.assertIn(f'href="research-{language}.html"', page)
        self.assertEqual(verified.read_text(encoding='utf-8'), source)
        self.assertEqual((self.root / 'index.html').read_text(), self.html)

    def test_language_render_failure_keeps_existing_published_pages(self):
        import i18n
        self.output.mkdir()
        for filename in ('index.html', 'index.de.html', 'index.es.html'):
            (self.output / filename).write_text('previous ' + filename)
        original = i18n.localize

        def render(html, language='en'):
            if language == 'es':
                raise ValueError('translation failed')
            return original(html, language)

        with patch('i18n.localize', side_effect=render):
            with self.assertRaisesRegex(ValueError, 'translation failed'):
                research.build_site(self.root, self.output)
        for filename in ('index.html', 'index.de.html', 'index.es.html'):
            self.assertEqual((self.output / filename).read_text(), 'previous ' + filename)
        self.assertFalse((self.output / 'research.html').exists())

    def test_research_and_market_back_links_keep_scoreboard_language(self):
        self.require_languages()
        self.write('2026-10-16.json', multilingual(example()))
        self.write_market(multilingual(example('2026-10-12')))
        path = self.root / 'market-briefings' / 'config.json'
        config = json.loads(path.read_text())
        config.update(languages=['es', 'en', 'de'], default_language='de',
                      schedule_labels={'es': 'Lunes', 'de': 'Montags'})
        path.write_text(json.dumps(config))
        research.build_site(self.root, self.output)
        for language, home in [('en', 'index.html'), ('de', 'index.de.html'),
                               ('es', 'index.es.html')]:
            for series, stamp in [('research', '2026-10-16'), ('market', '2026-10-12')]:
                latest = (self.output / research.page_path(series, language=language)).read_text()
                old = (self.output / research.page_path(series, stamp, language)).read_text()
                with self.subTest(language=language, series=series):
                    self.assertIn(f'href="{home}"', latest)
                    self.assertIn(f'href="../{home}"', old)
        self.assertIn('href="index.de.html"', (self.output / 'market.html').read_text())


if __name__ == '__main__':
    unittest.main()
