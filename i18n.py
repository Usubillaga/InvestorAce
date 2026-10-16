"""Static, token-aware report localization; financial inputs are never re-evaluated.

localize accepts the canonical English report. The English edition changes only
language controls and their research links. translation_gaps inventories new
first-party UI text that needs catalog coverage; issuer/source prose is explicitly
labelled as original and excluded. Only stdlib modules are used.
"""
from __future__ import annotations

import base64
import json
import re
from functools import lru_cache
from html import escape, unescape
from html.parser import HTMLParser

from i18n_data import TRANSLATIONS

LANGUAGES = {'en': 'English', 'de': 'Deutsch', 'es': 'Español'}
LANGUAGE_NAV_ID = 'investorace-language-nav'
_VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link',
         'meta', 'param', 'source', 'track', 'wbr'}
_NOTICE = {
    'de': 'Originaltext: Quellenhinweise und Dokumenttitel bleiben in ihrer Originalsprache.',
    'es': 'Texto original: las notas de fuentes y los títulos de documentos conservan su idioma original.',
}
_NEUTRAL_WORDS = (
    'InvestorAce', 'Yahoo', 'Finance', 'yfinance', 'GitHub', 'NGV', 'EPV', 'FCF',
    'FCFE', 'FCFF', 'WACC', 'SMA', 'EMA', 'ATR', 'OHLC', 'TR', 'VIX', 'UTC', 'USD',
    'EUR', 'GBP', 'GBp', 'CAD', 'CHF', 'JPY', 'AUD', 'HKD', 'CNY', 'SEK',
    'NOK', 'DKK', 'REIT', 'S&P', 'SPY', '10Y', '6m', '10y', '1y', '3y',
    '5y', '12m', '9m', '3m', '1m', 'pp', 'bp', 'x', 'r', 't', 'n/a',
    'CLOCK', 'CONC', 'DIV', 'TTM', 'PROXY', 'CAGR', 'ARR', 'AFFO', 'DCF',
    'cRPO', 'FY26', 'FY25', 'YoY', 'cc', 'High', 'Low', 'Close', 'True', 'wacc',
)
_JS_PHRASES = {
    'Enter a Yahoo ticker first, e.g. ROAD or ASML.AS.',
    ' is already in the model.', 'Open GitHub issue for ',
    r'Opening GitHub...\n\nIf it does not open, use the green link below.\n\n',
    '  rank ', ' &middot; growth ', '% &middot; inflation ',
    'Auto-add ', 'Do not edit the title -- the workflow reads the ticker from it.',
    'It fetches price, shares and TTM free cash flow from Yahoo, drafts the',
    'mechanical fields and opens a tested draft PR for review.',
    '  deliver : revenue/operating proxies stay descriptive; a cushion requires',
    '            sourced cash-flow growth and deliver_basis=CASH_FLOW',
    'Negative free cash flow is written as na= with no NGV, by design.',
}
_JS_LITERAL = re.compile(r"""(?P<quote>['"])(?P<value>(?:\\.|(?!\1)[^\\])*?)(?P=quote)""", re.DOTALL)


def _language(language):
    if language not in LANGUAGES:
        raise ValueError('Unsupported language: ' + str(language))
    return language


def homepage(language='en'):
    """Root-relative static homepage, shared with research/market renderers."""
    _language(language)
    return 'index.html' if language == 'en' else 'index.' + language + '.html'


def _navigation(language):
    label = {'en': 'Language', 'de': 'Sprache', 'es': 'Idioma'}[language]
    links = ''.join(
        '<a href="' + homepage(code) + '" lang="' + code + '" hreflang="' + code + '"'
        + (' aria-current="page" style="color:inherit;font-weight:700;text-decoration:underline"'
           if code == language else ' style="color:inherit"')
        + '>' + name + '</a>' for code, name in LANGUAGES.items())
    return ('<nav id="' + LANGUAGE_NAV_ID + '" aria-label="' + label + '" '
            'style="display:flex;flex-wrap:wrap;gap:14px;align-items:center;margin:0 0 18px;'
            'padding:12px 16px;border:1px solid #2a3040;border-radius:10px;background:#141821">'
            '<span>' + label + ':</span>' + links + '</nav>')


@lru_cache(maxsize=2)
def _pattern(language):
    def term(key):
        return (r'(?<!\w)' if key[0].isalnum() else '') + re.escape(key) + (
            r'(?!\w)' if key[-1].isalnum() else '')
    return re.compile('|'.join(term(k) for k in sorted(TRANSLATIONS[language], key=len, reverse=True)))


def _residue(value):
    value = value.replace('auto_adjust=True daily High/Low/Close', '')
    value = re.sub(r'(?<=\d)(?:pp|bp|[ymx])\b', '', value)
    value = re.sub(r'\b[0-9a-f]{32,64}\b', '', value)
    value = re.sub(r'\b\d{4}-\d{2}-\d{2}(?:T[\d:.]+(?:Z|[+-]\d{2}:\d{2}))?', '', value)
    value = re.sub(r'\b[a-z][a-z0-9.-]*-v\d+(?:[.-][a-z0-9-]+)*\b', '', value)
    value = re.sub(r'\bv\d+(?:[.-][a-z0-9-]+)*\b', '', value)
    value = re.sub(r'\b[A-Za-z_+-]+/[A-Za-z_+-]+\b', '', value)
    value = re.sub(r'\b(?:ISSUER_[A-Z_]+|SELECTED_NORMALIZED_ASSUMPTION|OCF_MINUS_CAPEX|COST_OF_EQUITY)\b', '', value)
    value = re.sub(r'\b[A-Z]\w*(?:Error|Exception)\b', '', value)
    value = value.replace('auto_adjust=True daily High/Low/Close', '').replace('history/', '')
    value = re.sub('|'.join(r'(?<!\w)' + re.escape(w) + r'(?!\w)' for w in sorted(_NEUTRAL_WORDS, key=len, reverse=True)), '', value)
    return re.sub(r'[\d\s\W_]+', '', value)


def _translate(value, language):
    """Translate known UI spans once and report any remaining prose."""
    if language == 'en' or not value.strip():
        return value, ''
    catalog = TRANSLATIONS[language]
    normalized = re.sub(r'\s+', ' ', value.strip())
    pattern = _pattern(language)
    translated = pattern.sub(lambda m: catalog[m.group()], normalized)
    missing = _residue(pattern.sub('', normalized))
    leading = value[:len(value) - len(value.lstrip())]
    trailing = value[len(value.rstrip()):]
    return leading + translated + trailing, missing


def _attribute(raw, name, value):
    pattern = re.compile(r'(\s' + re.escape(name) + r'\s*=\s*)(["\'])(.*?)\2', re.I | re.S)
    if pattern.search(raw):
        return pattern.sub(lambda m: m.group(1) + m.group(2) + escape(value, quote=True) + m.group(2),
                           raw, count=1)
    # Only controlled accessibility/lang attributes are added through this path.
    return re.sub(r'(\s*/?>)$', lambda m: ' ' + name + '="' + escape(value, quote=True) + '"' + m.group(1), raw, count=1)


class _Report(HTMLParser):
    def __init__(self, language, navigation=True):
        super().__init__(convert_charrefs=False)
        self.language = language
        self.navigation = navigation
        self.parts = []
        self.stack = []
        self.pending = []
        self.skip_navigation = 0
        self.gaps = set()

    def _notice(self):
        return '<small class="source-original">' + escape(_NOTICE[self.language]) + '</small>'

    def _research(self):
        return any(f['attrs'].get('id') == 'investorace-research-nav' for f in self.stack)

    def _source_scope(self):
        return any(f['source'] for f in self.stack)

    def _ticker(self, text):
        if not self.stack:
            return False
        current = self.stack[-1]
        if current['tag'] == 'td' and (
                'tk' in current['attrs'].get('class', '').split() or current.get('ticker')):
            return text not in {'score', 'cover', 'cushion', 'momentum'}
        return (current['tag'] == 'b' and len(self.stack) > 1
                and self.stack[-2]['tag'] == 'summary'
                and any('decision-stock' in f['attrs'].get('class', '').split() for f in self.stack))

    def _flush(self):
        if not self.pending:
            return
        raw = ''.join(self.pending)
        self.pending = []
        if self.skip_navigation:
            return
        value = unescape(raw)
        if not self.stack:
            self.parts.append(raw)
            return
        current = self.stack[-1]
        tag = current['tag']
        if tag == 'style':
            self.parts.append(raw)
            return
        if tag == 'script':
            self.parts.append(self._script(raw) if self.language != 'en' else raw)
            return
        for frame in self.stack:
            if frame['tag'] == 'th':
                frame['text'] += value
        if tag == 'h2' and value.strip().startswith('Price issues this run'):
            for frame in reversed(self.stack[:-1]):
                if frame['tag'] == 'div':
                    frame['original_records'] = True
                    break
        if self.language == 'en':
            # Legacy research controls contained a German default market label.
            if self._research():
                raw = raw.replace('Montagsbriefing', 'Monday briefing')
            self.parts.append(raw)
            return
        if self._ticker(value.strip()):
            self.parts.append(raw)
            return
        if 'decision-alert' in current['attrs'].get('class', '').split():
            # Translate the event, never the symbol between the two separators.
            fields = value.split(' · ')
            if len(fields) >= 3:
                fields[0] = _translate(fields[0], self.language)[0]
                self.parts.append(escape(' · '.join(fields), quote=False))
                return
        # These prose fields contain symbols as data. Translate their labels
        # and explanations, while leaving the symbols outside the catalog.
        ticker_label = 'Held positions missing quotes:'
        if value.lstrip().startswith(ticker_label):
            start = raw.index(ticker_label)
            self.parts.append(raw[:start] + escape(TRANSLATIONS[self.language][ticker_label], quote=False)
                              + raw[start + len(ticker_label):])
            return
        fallback_label = 'Manual discount-rate fallbacks:'
        if value.lstrip().startswith(fallback_label):
            prefix, tail = value.split(fallback_label, 1)
            def fallback(match):
                note, missing = _translate(match.group(4), self.language)
                if missing:
                    self.gaps.add(match.group(4))
                return match.group(1) + match.group(2) + match.group(3) + note
            tail = re.sub(r'(^\s*|;\s*)([A-Za-z0-9.^=_-]+)(:\s*)([^;]*)', fallback, tail)
            self.parts.append(escape(prefix + TRANSLATIONS[self.language][fallback_label] + tail,
                                     quote=False))
            return
        if self._source_scope():
            if tag in {'summary', 'b'}:
                fields = value.rsplit(' · ', 1)
                if len(fields) == 2:
                    fields[-1] = _translate(fields[-1], self.language)[0]
                    self.parts.append(escape(' · '.join(fields), quote=False))
                    return
            # Source reasons, limitations, disclosed security types, issuer
            # titles and transaction notes must remain verbatim. UI labels
            # remain translated; the containing record has an original notice.
            if tag not in {'b', 'th'}:
                core = value.strip()
                table = current.get('table')
                category = (tag == 'td' and table
                            and current['column'] < len(table['headers'])
                            and table['headers'][current['column']] == 'Disclosed type')
                if category:
                    label, separator, code = value.rpartition(' [')
                    if separator:
                        label, missing = _translate(label, self.language)
                        if missing:
                            self.gaps.add(value.strip())
                        self.parts.append(escape(label + separator + code, quote=False))
                        return
                is_ui = (category or core in {
                    'No transactions reported in the checked public register for this window.',
                    'Filing', 'checked', '· checked'}
                    or core.startswith(('Primary source ', '10b5-1:')))
                if core.startswith('Next review:'):
                    translated = TRANSLATIONS[self.language]['Next review:']
                    self.parts.append(escape(translated, quote=False) + raw[raw.index('Next review:') + len('Next review:'):])
                    return
                if not is_ui:
                    self.parts.append(raw)
                    return
        if any(f.get('original_records') for f in self.stack) and tag != 'h2':
            self.parts.append(raw)
            return
        if tag == 'a' and current['attrs'].get('href', '').startswith(('https://', 'http://')):
            core = value.strip()
            if core not in {'How stop orders work', 'Filing'} and not core.startswith('Primary source '):
                self.parts.append(raw)
                return
        # The detail includes a user-authored growth-metric description. Keep
        # this descriptor original; translate the surrounding first-party rule.
        metric = re.match(r'([+-]?\d[\d.,]*%\s+)(.*?)(; basis:.*)', value, re.S)
        if metric and any('review-note' in f['attrs'].get('class', '').split() for f in self.stack):
            prefix, descriptor, suffix = metric.groups()
            translated_descriptor, missing = _translate(descriptor, self.language)
            if missing:
                translated_descriptor = ('[' + {'de': 'Originaltext', 'es': 'Texto original'}[self.language]
                                         + ': ' + descriptor + ']')
            suffix = _translate(suffix, self.language)[0]
            self.parts.append(escape(prefix + translated_descriptor + suffix, quote=False))
            return
        # Source-attached quote warnings have no stable wording; mark them.
        if tag in {'span', 'div'} and '#f06a6a' in current['attrs'].get('style', ''):
            candidate, missing = _translate(value, self.language)
            if missing:
                self.parts.append(self._notice() + raw)
                return
        translated, missing = _translate(value, self.language)
        if missing and re.search(r'[A-Za-z]{2}', missing):
            self.gaps.add(re.sub(r'\s+', ' ', value.strip()))
        self.parts.append(raw if translated == value else escape(translated, quote=False))

    def _script(self, script):
        def portfolio(match):
            try:
                decoded = base64.b64decode(match.group(3), validate=True).decode('utf-8')
            except (ValueError, UnicodeError):
                return match.group()
            parser = _Report(self.language, navigation=False)
            parser.feed(decoded)
            parser.close()
            self.gaps.update(parser.gaps)
            encoded = base64.b64encode(parser.result().encode('utf-8')).decode('ascii')
            return match.group(1) + match.group(2) + encoded + match.group(2)
        script = re.sub(r'(\bconst\s+ZP\s*=\s*)(["\'])([A-Za-z0-9+/=]+)\2', portfolio, script)
        catalog = TRANSLATIONS[self.language]

        def literal(match):
            value = match.group('value')
            before = script[max(0, match.start()-220):match.start()]
            ui = (re.search(r'(?:\blabel|\btext)\s*:\s*$|\bfillText\(\s*$', before)
                  or re.search(r'(?:out\.value|link\.textContent|n\.textContent)\s*=[^;{}\n]*$', before)
                  or value in _JS_PHRASES)
            if not ui:
                return match.group()
            if value in catalog:
                translated = catalog[value]
                # Catalog JS messages store escaped line breaks intentionally.
                translated = translated.replace(r'\n', '\n')
                return json.dumps(translated, ensure_ascii=False)
            if _residue(value) and value not in {'', ' ', '%', ' \\u2192'}:
                self.gaps.add('JavaScript UI: ' + value)
            return match.group()
        script = _JS_LITERAL.sub(literal, script)
        # Map display values at the tooltip, keeping QT/QH and regime-series
        # keys and their entire JSON payloads byte-for-byte intact.
        tooltip = re.compile(r"(c\.raw\.y\.toFixed\(1\)\s*\+\s*['\"]% &middot; ['\"]\s*\+\s*)c\.raw\.q")
        script, count = tooltip.subn(lambda m: m.group(1) + '_iaLabel(c.raw.q)', script)
        if count:
            script = script.replace("c.raw.l + ", "_iaLabel(c.raw.l) + ")
            labels = {k: catalog.get(k, k) for k in (
                'GOLDILOCKS', 'REFLATION', 'INFLATION', 'STAGFLATION', 'RECESSION')}
            labels['now'] = {'de': 'jetzt', 'es': 'ahora'}[self.language]
            script = ('const _IA_LABELS=' + json.dumps(labels, ensure_ascii=False)
                      + ';\nfunction _iaLabel(v){return _IA_LABELS[v] || v;}\n' + script)
        return script

    def handle_starttag(self, tag, attrs):
        self._flush()
        attrs = dict(attrs)
        if self.skip_navigation:
            if tag == 'nav':
                self.skip_navigation += 1
            return
        if tag == 'nav' and attrs.get('id') == LANGUAGE_NAV_ID:
            self.skip_navigation = 1
            return
        raw = self.get_starttag_text()
        if tag == 'html':
            raw = _attribute(raw, 'lang', self.language)
        if tag == 'a' and self._research():
            match = re.fullmatch(r'(market|research)(?:-(?:en|de|es))?\.html', attrs.get('href', ''))
            if match:
                series = match.group(1)
                suffix = '' if series == 'research' and self.language == 'en' else '-' + self.language
                raw = _attribute(raw, 'href', series + suffix + '.html')
        if self.language != 'en':
            for key in ('title', 'placeholder', 'aria-label', 'alt'):
                if key in attrs and attrs[key]:
                    value = attrs[key]
                    if key == 'title' and value.startswith('Filing coverage') and ': ' in value:
                        prefix, note = value.split(': ', 1)
                        value = _translate(prefix, self.language)[0] + ' · ' + {
                            'de': 'Originaltext: ', 'es': 'Texto original: '}[self.language] + note
                    else:
                        value, _ = _translate(value, self.language)
                    if value != attrs[key]:
                        raw = _attribute(raw, key, value)
            if attrs.get('id') in {'zielIn', 'zielBtn'}:
                labels = {'de': ('Portfolio-Zugangswort', 'Portfolio öffnen'),
                          'es': ('Clave de acceso a la cartera', 'Abrir cartera')}
                raw = _attribute(raw, 'aria-label', labels[self.language][attrs['id'] == 'zielBtn'])
        self.parts.append(raw)
        if tag == 'body' and self.navigation:
            self.parts.append(_navigation(self.language))
        frame = {'tag': tag, 'attrs': attrs, 'text': '', 'source': (
            attrs.get('id', '').startswith(('review-', 'filing-')))}
        if tag == 'table':
            frame.update(headers=[], column=0)
        table = next((f for f in reversed(self.stack) if f['tag'] == 'table'), None)
        if table and tag == 'tr':
            table['column'] = 0
        if table and tag in {'td', 'th'}:
            index = table['column']
            table['column'] += 1
            frame['column'] = index
            frame['table'] = table
            frame['ticker'] = (tag == 'td' and index < len(table['headers'])
                               and table['headers'][index] == 'Ticker')
        if tag not in _VOID:
            self.stack.append(frame)
        if frame['source'] and tag != 'details' and self.language != 'en':
            self.parts.append(self._notice())

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in _VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        self._flush()
        if self.skip_navigation:
            if tag == 'nav':
                self.skip_navigation -= 1
            return
        found = next((i for i in range(len(self.stack)-1, -1, -1)
                      if self.stack[i]['tag'] == tag), None)
        frame = self.stack[found] if found is not None else None
        if frame and tag == 'th':
            headers = frame['table']['headers']
            while len(headers) <= frame['column']:
                headers.append('')
            headers[frame['column']] = frame['text'].strip()
        self.parts.append('</' + tag + '>')
        if self.language != 'en' and tag == 'summary' and self._source_scope():
            self.parts.append(self._notice())
        if self.language != 'en' and tag == 'h2' and any(f.get('original_records') for f in self.stack):
            self.parts.append(self._notice())
        if found is not None:
            del self.stack[found:]

    def handle_data(self, data):
        self.pending.append(data)

    def handle_entityref(self, name):
        self.pending.append('&' + name + ';')

    def handle_charref(self, name):
        self.pending.append('&#' + name + ';')

    def handle_comment(self, data):
        self._flush()
        if not self.skip_navigation:
            self.parts.append('<!--' + data + '-->')

    def handle_decl(self, decl):
        self._flush()
        self.parts.append('<!' + decl + '>')

    def handle_pi(self, data):
        self._flush()
        self.parts.append('<?' + data + '>')

    def close(self):
        super().close()
        self._flush()

    def result(self):
        return ''.join(self.parts)


def localize(html: str, language='en') -> str:
    """Create one static edition from canonical English; never mutate model data."""
    _language(language)
    parser = _Report(language)
    parser.feed(html)
    parser.close()
    return parser.result()


def translation_gaps(html: str) -> list[str]:
    """Inventory unmatched English UI prose (including the hidden portfolio).

    This deliberately ignores labelled source records, original issuer document
    titles, ticker cells and opaque provenance identifiers. New first-party UI
    sentences are reported so coverage tests fail when the catalog needs updating.
    """
    parser = _Report('de', navigation=False)
    parser.feed(html)
    parser.close()
    return sorted(parser.gaps)
