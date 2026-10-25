"""Download URLs must identify the same company, scope and language as the PDF."""
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from urllib.parse import unquote

from pypdf import PdfReader

from company_pdf import pdf_path
from company_reports import pdf_pages, pdf_urls
from integrity import atomic_bytes
from review_packets import build_packet


class CompanyReportDelivery(unittest.TestCase):
    def test_urls_decode_to_the_exact_filename_without_scope_or_symbol_collisions(self):
        for ticker in ('ZTS', 'EX/A', 'EX%2FA', '../EX', 'BRK.B'):
            for scope in ('universe', 'market'):
                for language, url in pdf_urls(ticker, scope=scope).items():
                    self.assertEqual(Path(unquote(url)), pdf_path(ticker, language, scope=scope))
                    self.assertTrue(url.endswith('.' + language + '.pdf'))
        self.assertNotEqual(pdf_urls('ZTS')['es'], pdf_urls('ZTS', scope='market')['es'])

    def test_both_scopes_publish_real_pdfs_with_their_own_research(self):
        packets = {}
        for scope in ('universe', 'market'):
            packets[scope] = {'EX': build_packet(scope=scope, ticker='EX',
                origin=dict(as_of='2026-10-25T12:00:00Z'), inputs={}, output={},
                sources=[], issues=[], objections=[], research=dict(thesis=scope + '-unique-thesis'))}
        pages = pdf_pages(dict(review_packets=packets))
        self.assertEqual(len(pages), 6)
        self.assertEqual(len({path for path, _ in pages}), 6)
        with tempfile.TemporaryDirectory() as folder:
            for path, payload in pages:
                atomic_bytes(Path(folder) / path, payload)
                self.assertTrue((Path(folder) / path).read_bytes().startswith(b'%PDF-'))
                text = '\n'.join(p.extract_text() or '' for p in PdfReader(BytesIO(payload)).pages)
                scope = 'market' if path.parent.name == 'market' else 'universe'
                self.assertIn(scope + '-unique-thesis', text)


if __name__ == '__main__':
    unittest.main()
