"""PDF artifacts and URLs for exactly the scanner's frozen research packets."""
from urllib.parse import quote

from company_pdf import pdf_path, render_pdf


LANGUAGES = ('en', 'de', 'es')


def pdf_urls(ticker, *, scope='universe'):
    return {language: quote(pdf_path(ticker, language, scope=scope).as_posix(), safe='/')
            for language in LANGUAGES}


def pdf_pages(scan):
    pages = []
    for scope, packets in scan['review_packets'].items():
        for ticker, packet in packets.items():
            for language in LANGUAGES:
                pages.append((pdf_path(ticker, language, scope=scope), render_pdf(packet, language)))
    return pages
