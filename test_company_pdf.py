"""The download is a faithful offline rendering, never a new financial model."""
import copy
from io import BytesIO
from pathlib import Path
import unittest
from unittest.mock import patch

from pypdf import PdfReader

import company_pdf


def packet():
    weights = dict(g=.15, p=.20, c=.15, b=.15, v=.10, pr=.15, r=.05, d=.05)
    components = [dict(key=k, value=7, nominal_weight=w, effective_weight=w,
                       contribution=7*w, source='Captured financial statement')
                  for k, w in weights.items()]
    return dict(schema='research-review-packet-v1', status='NOT_STARTED',
        can_approve=False, snapshot_sha256='snapshot-hash-123', snapshot=dict(
            ticker='EX/A', scope='universe', origin=dict(
                captured_at='2026-10-25T12:00:00Z', as_of='2026-10-25T12:00:00Z',
                model_source_sha256='model-hash-456', models=dict(engine='fixture-v1'),
                score_weights=weights),
            inputs=dict(cur='USD', financial_unit='USD million', fcf=100,
                primary_analysis_archive=dict(score_fixed=4.55, boot_note='Archived original note'),
                dynamic_analysis=dict(status='COMPLETE', data_status='FRESH_INPUTS',
                    review_status='REVIEW_REQUIRED', can_approve=False,
                    financial_period='2026-06-30', financial_currency='USD', currency='USD',
                    basis='TTM', fetched_at='2026-10-25T11:00:00Z',
                    quote_observed_at='2026-10-23T20:00:00Z',
                    inputs=dict(quote_price=101.23, fcf=123456789, shares=1234567),
                    metrics=dict(fcf_margin_pct=14.321, market_cap=124962962.41),
                    parameters=dict(discount_rate_pct=8.5, terminal_growth_pct=2,
                        growth_rate_pct=4, horizon_years=5,
                        cash_flow_basis='LEVERED_FCF_PROXY', discount_rate_basis='COST_OF_EQUITY'),
                    valuation=dict(ngv_per_share=117.65, dcf_per_share=130.12,
                        reverse_dcf_growth_pct=1.23, scenarios=[dict(name='bear',
                            growth_pct=-1, value_per_share=97.25)]),
                    model_score=7, components=dict.fromkeys(weights, 7),
                    score_explanation=dict(components=components),
                    metric_periods=dict(cash_flow=['2026-06-30', '2026-03-31']),
                    source_urls=['https://example.org/dynamic-source'])),
            model_output=dict(ngv=117.65, verdict='REVIEW REQUIRED',
                assessment=dict(review_status='REVIEW_REQUIRED', rating=None,
                    calculation_status='COMPLETE', model_score=7, components=components)),
            research=dict(thesis='Research thesis', counterargument='Research counterargument',
                next_check='Obtain next filing', source_reason='Primary review reason',
                source_review=dict(issuer='Example & Partners', valuation=dict(
                    status='SOURCE_CHECKED', review_decision='Normalization is still open'))),
            sources=[dict(id='SRC-001', title='Current filing', period='H1 2026',
                published_at='2026-08-06', url='https://example.org/filing')],
            issues=[dict(code='NORMALIZATION', severity='major', status='open',
                message='Annual cash bridge is unresolved')],
            objections=[dict(id='OBJ-1', severity='major', status='open',
                message='Compare share dates')]))


def read(data):
    reader = PdfReader(BytesIO(data))
    return reader, '\n'.join(page.extract_text() or '' for page in reader.pages)


class CompanyPdfTests(unittest.TestCase):
    def test_canonical_paths_keep_distinct_tickers_and_stay_under_output_directory(self):
        self.assertEqual(company_pdf.pdf_path('EX/A', 'de'), Path('analysis-pdfs/EX%2FA.de.pdf'))
        self.assertEqual(company_pdf.pdf_path('EX/A', 'de', scope='market'),
                         Path('analysis-pdfs/market/EX%2FA.de.pdf'))
        with self.assertRaises(ValueError):
            company_pdf.pdf_path('EX', scope='invalid')
        symbols = ['EX/A', 'EX%2FA', 'EX.A', 'ex.a', '../EX', 'EX\\A', '株']
        paths = [company_pdf.pdf_path(t) for t in symbols]
        self.assertEqual(len(paths), len(set(paths)))
        self.assertTrue(all(p.parent == Path('analysis-pdfs') for p in paths))
        for ticker in ['', '   ', None]:
            with self.subTest(ticker=ticker), self.assertRaises(ValueError):
                company_pdf.pdf_path(ticker)
        for language in ['fr', 'EN', '']:
            with self.assertRaises(ValueError):
                company_pdf.pdf_path('EX', language)
            with self.assertRaises(ValueError):
                company_pdf.render_pdf(packet(), language)

    def test_valid_pdf_embeds_fonts_and_contains_dates_scores_sources_and_provenance(self):
        data = company_pdf.render_pdf(packet(), 'en')
        self.assertTrue(data.startswith(b'%PDF-'))
        reader, text = read(data)
        for expected in ['Example & Partners', 'EX/A', '2026-06-30', '2026-08-06',
                         '2026-10-23T20:00:00Z', 'H1 2026', 'TTM', 'USD',
                         'snapshot-hash-123', 'model-hash-456', 'fixture-v1',
                         'Research thesis', 'Primary review reason', 'OBJ-1',
                         'Annual cash bridge is unresolved', 'Reverse DCF growth (%)']:
            self.assertIn(expected, text)
        for key in ('g', 'p', 'c', 'b', 'v', 'pr', 'r', 'd'):
            self.assertIn(f'({key})', text)
        self.assertIn('15%', text)
        self.assertIn('20%', text)
        self.assertIn('5%', text)
        font_objects = [font.get_object() for p in reader.pages
                        for font in p['/Resources']['/Font'].get_object().values()]
        self.assertTrue(any('/FontFile2' in f.get('/FontDescriptor', {}).get_object()
                            for f in font_objects if '/FontDescriptor' in f))
        links = [a.get_object().get('/A', {}).get('/URI') for p in reader.pages
                 for a in p.get('/Annots', [])]
        self.assertIn('https://example.org/filing', links)
        self.assertIn('https://example.org/dynamic-source', links)

    def test_current_input_changes_and_current_source_period_are_rendered_without_mutation(self):
        original = packet()
        modified = copy.deepcopy(original)
        dynamic = modified['snapshot']['inputs']['dynamic_analysis']
        dynamic['inputs']['fcf'] = 987654321
        dynamic['valuation']['dcf_per_share'] = 333.77
        dynamic['financial_period'] = '2026-09-30'
        modified['snapshot']['sources'][0]['period'] = 'Q3 2026'
        frozen = copy.deepcopy(modified)
        _, first = read(company_pdf.render_pdf(original, 'en'))
        with patch('socket.create_connection', side_effect=AssertionError('No network')):
            _, second = read(company_pdf.render_pdf(modified, 'en'))
        self.assertIn('123,456,789', first)
        self.assertNotIn('987,654,321', first)
        self.assertIn('987,654,321', second)
        self.assertIn('333.77', second)
        self.assertIn('2026-09-30', second)
        self.assertIn('Q3 2026', second)
        self.assertEqual(modified, frozen)

    def test_missing_or_specialty_inputs_remain_unavailable_with_archived_output_distinct(self):
        p = packet()
        p['snapshot']['inputs']['dynamic_analysis'] = None
        p['snapshot']['model_output']['assessment'].update(review_status='MYSTERY', rating='BUY')
        _, text = read(company_pdf.render_pdf(p, 'en'))
        self.assertIn('Unavailable', text)
        self.assertIn('Review required', text)

        self.assertIn('Archived', text)
        self.assertIn('4.55', text)
        self.assertIn('Archived original note', text)
        self.assertNotIn('Approved rating: BUY', text)
        self.assertNotIn('SELL', text)
        p['snapshot']['inputs']['dynamic_analysis'] = dict(inputs=dict(fcf=None),
            metrics=dict(fcf_margin_pct=None), valuation=dict(dcf_per_share=None))
        _, text = read(company_pdf.render_pdf(p, 'en'))
        self.assertIn('Reported FCF', text)
        self.assertIn('Unavailable', text)
        self.assertIn('Review required', text)

    def test_recorded_valid_review_is_not_withdrawn_for_an_optional_missing_metric(self):
        p = packet()
        p['snapshot']['model_output']['assessment'].update(
            review_status='REVIEWED', quality_rank_eligible=True, rating='BUY')
        p['snapshot']['inputs']['dynamic_analysis']['inputs']['net_income'] = None
        _, text = read(company_pdf.render_pdf(p, 'en'))
        self.assertIn('Recorded analyst review', text)

    def test_native_dynamic_units_are_distinguished_from_engine_millions(self):
        _, text = read(company_pdf.render_pdf(packet(), 'en'))
        self.assertIn('Native statement amounts', text)
        self.assertIn('Engine cash-flow and share inputs are in millions', text)

    def test_objection_response_is_not_lost_behind_its_synthesized_issue(self):
        p = packet()
        objection = p['snapshot']['objections'][0]
        objection.update(response='COMPLETE-ANALYST-RESPONSE', resolution_required='REQUIRED-EVIDENCE')
        p['snapshot']['issues'] = [dict(code=objection['id'], severity=objection['severity'],
            status=objection['status'], message=objection['message'])]
        _, text = read(company_pdf.render_pdf(p, 'en'))
        self.assertIn('COMPLETE-ANALYST-RESPONSE', text)
        self.assertIn('REQUIRED-EVIDENCE', text)

    def test_market_replay_status_is_current_and_saved_inputs_are_archived(self):
        p = packet()
        p['snapshot']['scope'] = 'market'
        p['snapshot']['inputs'].update(dynamic_analysis=None, status='COMPLETE', score=8.725,
                                      price=155.83, metrics=dict(fcf_yield_pct=8.14689))
        p['snapshot']['model_output'] = dict(price=None, score=None, status='PARTIAL',
            review_status='BLOCKED_BY_DATA', quote_status='STALE', calculation_status='PARTIAL',
            source_limit='SCREENING ONLY', metrics=dict(fcf_yield_pct=None))
        _, text = read(company_pdf.render_pdf(p, 'en'))
        for expected in ('BLOCKED_BY_DATA', 'STALE', 'PARTIAL', 'SCREENING ONLY',
                         'Saved screening inputs (archived)'):
            self.assertIn(expected, text)

    def test_escaped_long_research_issues_and_source_urls_survive_pagination(self):
        p = packet()
        p['snapshot']['research']['thesis'] = '<script>cash & debt</script> - ü € 🚀\n' + (
            'Long original research sentence. ' * 1600) + 'THESIS-END'
        p['snapshot']['issues'][0]['message'] = ('Full objection detail. ' * 600) + 'ISSUE-END'
        url = 'https://example.org/' + 'x'*900 + '?a=1&b=2'
        p['snapshot']['sources'].append(dict(title='<b>Original title</b>', url=url))
        reader, text = read(company_pdf.render_pdf(p, 'en'))
        self.assertGreater(len(reader.pages), 4)
        for expected in ['<script>cash & debt</script>', 'THESIS-END', 'ISSUE-END',
                         '<b>Original title</b>', '[U+1F680]']:
            self.assertIn(expected, text)
        links = [a.get_object().get('/A', {}).get('/URI') for page in reader.pages
                 for a in page.get('/Annots', [])]
        self.assertIn(url, links)

    def test_languages_translate_labels_and_explicitly_keep_original_research(self):
        for language, expected in [('en', 'Company analysis'), ('de', 'Unternehmensanalyse'),
                                   ('es', 'Análisis de empresa')]:
            with self.subTest(language=language):
                _, text = read(company_pdf.render_pdf(packet(), language))
                self.assertIn(expected, text)
                self.assertIn('Research thesis', text)
                self.assertIn({'en': 'Original research language', 'de': 'Originalsprache der Recherche',
                               'es': 'Idioma original de la investigación'}[language], text)

    def test_market_report_uses_replayed_components_and_labels_missing_primary_analysis(self):
        p = packet()
        snapshot = p['snapshot']
        snapshot['scope'] = 'market'
        snapshot['inputs'] = dict(name='Market Candidate', metrics=dict(revenue=345678900),
            components=[dict(key='g', value=1, weight=.15)])
        snapshot['model_output'] = dict(metrics=dict(revenue=345678900, fcf_yield_pct=6.789),
            components=[dict(key='g', value=8.765, weight=.15)])
        snapshot['research'] = dict(thesis=None, counterargument=None, next_check='Read primary filing')
        _, text = read(company_pdf.render_pdf(p, 'en'))
        for expected in ['Scanning only', 'Market Candidate', '345,678,900', '6.789',
                         '8.765', 'Unavailable', 'Read primary filing', 'Review required']:
            self.assertIn(expected, text)


if __name__ == '__main__':
    unittest.main()
