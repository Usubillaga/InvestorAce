"""Offline, read-only PDF presentation of one frozen review packet.

This module formats supplied values. It never fetches quotes, runs a valuation,
fills missing scores, or grants approval. Raw field names preserve auditability.
"""
from __future__ import annotations

from io import BytesIO
import json
import math
from pathlib import Path
import unicodedata
from urllib.parse import quote, urlsplit
from xml.sax.saxutils import escape, quoteattr

import reportlab
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


_WORDS = {
    'title': ('Company analysis', 'Unternehmensanalyse', 'Análisis de empresa'),
    'review': ('Review required', 'Prüfung erforderlich', 'Revisión requerida'),
    'reviewed': ('Recorded analyst review', 'Erfasste Analystenprüfung', 'Revisión del analista registrada'),
    'unavailable': ('Unavailable', 'Nicht verfügbar', 'No disponible'),
    'screen': ('Scanning only', 'Nur Screening', 'Solo cribado'),
    'notice': ('Frozen snapshot; model output and source checking are separate from analyst approval.',
               'Eingefrorener Stand; Modellausgabe und Quellenprüfung sind von der Analystenfreigabe getrennt.',
               'Instantánea congelada; el modelo y la revisión de fuentes son distintos de la aprobación del analista.'),
    'freshness': ('Dates, currencies and basis', 'Daten, Währungen und Grundlage', 'Fechas, monedas y bases'),
    'current': ('Dynamic model at calculation date', 'Dynamisches Modell zum Berechnungszeitpunkt', 'Modelo dinámico en la fecha de cálculo'),
    'inputs': ('Model inputs', 'Modelleingaben', 'Datos del modelo'),
    'metrics': ('Financial metrics', 'Finanzkennzahlen', 'Métricas financieras'),
    'parameters': ('NGV / DCF / reverse DCF assumptions', 'NGV / DCF / Reverse-DCF-Annahmen', 'Supuestos NGV / DCF / DCF inverso'),
    'valuation': ('Stored valuation and scenarios', 'Gespeicherte Bewertung und Szenarien', 'Valoración y escenarios registrados'),
    'scores': ('Eight score components', 'Acht Score-Komponenten', 'Ocho componentes de puntuación'),
    'component': ('Component', 'Komponente', 'Componente'),
    'value': ('Value', 'Wert', 'Valor'),
    'nominal': ('Weight', 'Gewicht', 'Peso'),
    'effective': ('Effective', 'Effektiv', 'Efectivo'),
    'contribution': ('Contribution', 'Beitrag', 'Contribución'),
    'output': ('Captured model output', 'Erfasste Modellausgabe', 'Resultado del modelo capturado'),
    'archive': ('Archived / retained output - no current certification', 'Archivierte / erhaltene Ausgabe - keine aktuelle Bestätigung',
                'Resultado archivado / conservado - sin certificación actual'),
    'original': ('Original research language retained; labels translated only.',
                 'Originalsprache der Recherche beibehalten; nur Beschriftungen übersetzt.',
                 'Idioma original de la investigación conservado; solo se traducen las etiquetas.'),
    'research': ('Research and source review', 'Recherche und Quellenprüfung', 'Investigación y revisión de fuentes'),
    'thesis': ('Thesis', 'These', 'Tesis'),
    'counterargument': ('Counterargument', 'Gegenargument', 'Contraargumento'),
    'next_check': ('Next evidence check', 'Nächste Belegprüfung', 'Próxima comprobación'),
    'source_reason': ('Source review reason', 'Begründung der Quellenprüfung', 'Motivo de revisión de fuentes'),
    'notes': ('Additional notes and captured inputs', 'Weitere Notizen und erfasste Eingaben', 'Notas adicionales y datos capturados'),
    'issues': ('Issues and objections (all recorded statuses)', 'Befunde und Einwände (alle erfassten Status)', 'Incidencias y objeciones (todos los estados)'),
    'sources': ('Source register', 'Quellenverzeichnis', 'Registro de fuentes'),
    'provenance': ('Snapshot and model provenance', 'Snapshot- und Modellherkunft', 'Procedencia de la instantánea y del modelo'),
    'field': ('Field', 'Feld', 'Campo'),
    'page': ('Page', 'Seite', 'Página'),
    'weights': ('Weights are recorded fractions; missing values are not imputed or reweighted.',
                'Gewichte sind erfasste Anteile; fehlende Werte werden weder ergänzt noch umgewichtet.',
                'Los pesos son fracciones registradas; los valores ausentes no se imputan ni se reponderan.'),
    'archive_note': ('Selected dated archive values; the complete original packet is available separately as JSON.',
                     'Ausgewählte datierte Archivwerte; das vollständige Originalpaket ist separat als JSON verfügbar.',
                     'Valores históricos seleccionados; el paquete original completo está disponible por separado en JSON.'),
    'native_units': ('Native statement amounts use the financial currency; shares are full counts. Prices and per-share valuations use the quote currency.',
                     'Gemeldete Beträge verwenden die Berichtswährung; Aktienzahlen sind volle Stückzahlen. Kurse und Werte je Aktie verwenden die Kurswährung.',
                     'Los importes declarados usan la moneda financiera; las acciones son cantidades completas. Los precios y valores por acción usan la moneda de cotización.'),
    'engine_units': ('Engine cash-flow and share inputs are in millions, separately from native statement amounts above. Prices remain per share.',
                     'Cashflow- und Aktien-Eingaben des bisherigen Modells sind in Millionen angegeben, getrennt von den vollen Berichtsbeträgen oben. Kurse gelten je Aktie.',
                     'Los datos de caja y acciones del motor están en millones, separados de los importes completos anteriores. Los precios siguen siendo por acción.'),
    'saved_market': ('Saved screening inputs (archived)', 'Gespeicherte Screening-Eingaben (archiviert)', 'Datos guardados del cribado (históricos)'),
    'scenario': ('Scenario', 'Szenario', 'Escenario'),
    'growth': ('Growth (%)', 'Wachstum (%)', 'Crecimiento (%)'),
    'per_share': ('Value per share', 'Wert je Aktie', 'Valor por acción'),
    'technical': ('Appendix: calculation provenance', 'Anhang: Berechnungsherkunft', 'Anexo: procedencia del cálculo'),
}
_FIELDS = {
    'captured_at': ('Snapshot captured', 'Snapshot erfasst', 'Captura de datos'),
    'as_of': ('Analysis cutoff', 'Analysestichtag', 'Fecha de análisis'),
    'financial_period': ('Financial period', 'Finanzperiode', 'Periodo financiero'),
    'financial_published_at': ('Publication date', 'Veröffentlichung', 'Publicación'),
    'retrieved_at': ('Financial data retrieved', 'Finanzdaten abgerufen', 'Consulta de datos financieros'),
    'quote_observed_at': ('Quote observed', 'Kurszeitpunkt', 'Fecha de cotización'),
    'quote_currency': ('Quote currency', 'Kurswährung', 'Moneda de cotización'),
    'financial_currency': ('Financial currency', 'Berichtswährung', 'Moneda financiera'),
    'financial_unit': ('Statement amount unit', 'Einheit der Berichtsbeträge', 'Unidad de importes'),
    'quote_price': ('Quote per share', 'Kurs je Aktie', 'Cotización por acción'),
    'revenue': ('Revenue', 'Umsatz', 'Ingresos'),
    'operating_income': ('Operating income', 'Operatives Ergebnis', 'Resultado operativo'),
    'net_income': ('Net income', 'Jahresüberschuss', 'Beneficio neto'),
    'operating_cash_flow': ('Operating cash flow', 'Operativer Cashflow', 'Flujo de caja operativo'),
    'capex': ('Cash capital expenditure', 'Investitionen', 'Inversiones'),
    'fcf': ('Reported FCF', 'Gemeldeter freier Cashflow', 'Flujo de caja libre declarado'),
    'valuation_fcf': ('Cash flow used for valuation', 'Cashflow im Bewertungsszenario', 'Caja usada para la valoración'),
    'shares': ('Shares outstanding', 'Ausstehende Aktien', 'Acciones en circulación'),
    'debt': ('Financial debt', 'Finanzschulden', 'Deuda financiera'),
    'cash': ('Cash', 'Liquidität', 'Efectivo'),
    'dividends': ('Dividends paid', 'Gezahlte Dividenden', 'Dividendos pagados'),
    'ebitda': ('EBITDA', 'EBITDA', 'EBITDA'),
    'cover_pct': ('NGV / price (%)', 'NGV / Kurs (%)', 'NGV / cotización (%)'),
    'fcf_growth_pct': ('Annual FCF growth (%)', 'Jährliches FCF-Wachstum (%)', 'Crecimiento anual del FCF (%)'),
    'fcf_margin_pct': ('FCF margin (%)', 'FCF-Marge (%)', 'Margen de FCF (%)'),
    'fcf_yield_pct': ('FCF yield (%)', 'FCF-Rendite (%)', 'Rentabilidad por FCF (%)'),
    'market_cap': ('Market capitalization', 'Marktkapitalisierung', 'Capitalización bursátil'),
    'net_debt': ('Net debt', 'Nettoverschuldung', 'Deuda neta'),
    'net_debt_ebitda': ('Net debt / EBITDA', 'Nettoschulden / EBITDA', 'Deuda neta / EBITDA'),
    'operating_margin_pct': ('Operating margin (%)', 'Operative Marge (%)', 'Margen operativo (%)'),
    'revenue_growth_pct': ('Annual revenue growth (%)', 'Jährliches Umsatzwachstum (%)', 'Crecimiento anual de ingresos (%)'),
    'share_change_pct': ('Annual share change (%)', 'Jährliche Aktienzahländerung (%)', 'Variación anual de acciones (%)'),
    'shareholder_yield_pct': ('Shareholder yield (%)', 'Aktionärsrendite (%)', 'Retorno al accionista (%)'),
    'ngv_per_share': ('NGV per share', 'NGV je Aktie', 'NGV por acción'),
    'dcf_per_share': ('DCF per share', 'DCF je Aktie', 'DCF por acción'),
    'reverse_dcf_growth_pct': ('Reverse DCF growth (%)', 'Reverse-DCF-Wachstum (%)', 'Crecimiento implícito DCF inverso (%)'),
    'discount_rate_pct': ('Cost of equity (%)', 'Eigenkapitalkosten (%)', 'Coste del capital propio (%)'),
    'growth_rate_pct': ('Scenario growth (%)', 'Szenariowachstum (%)', 'Crecimiento del escenario (%)'),
    'terminal_growth_pct': ('Terminal growth (%)', 'Terminalwachstum (%)', 'Crecimiento terminal (%)'),
    'horizon_years': ('Forecast years', 'Prognosejahre', 'Años del escenario'),
    'risk_free_pct': ('Risk-free rate (%)', 'Risikofreier Zins (%)', 'Tipo libre de riesgo (%)'),
    'market_premium_pct': ('Market risk premium (%)', 'Marktrisikoprämie (%)', 'Prima de riesgo de mercado (%)'),
    'cash_flow_basis': ('Cash-flow basis', 'Cashflow-Basis', 'Base del flujo de caja'),
    'discount_rate_basis': ('Discount-rate basis', 'Diskontsatzbasis', 'Base de descuento'),
    'cash_flow_calculation': ('Cash-flow formula', 'Cashflow-Formel', 'Fórmula de caja'),
    'cash_flow_policy': ('Cash-flow scenario', 'Cashflow-Szenario', 'Escenario de caja'),
    'currency_factor': ('Quote-unit conversion', 'Kurseinheiten-Umrechnung', 'Conversión de unidad de cotización'),
    'cushion_tolerance_pp': ('Cushion tolerance (pp)', 'Puffertoleranz (pp)', 'Tolerancia del colchón (pp)'),
}
_CATEGORIES = {
    'g': ('Growth', 'Wachstum', 'Crecimiento'),
    'p': ('Profitability', 'Profitabilität', 'Rentabilidad'),
    'c': ('Cash generation', 'Cashflow', 'Generación de caja'),
    'b': ('Balance sheet', 'Bilanz', 'Balance'),
    'v': ('Valuation', 'Bewertung', 'Valoración'),
    'pr': ('Priced-in expectations', 'Eingepreiste Erwartungen', 'Expectativas implícitas'),
    'r': ('Shareholder returns', 'Aktionärsrendite', 'Retorno al accionista'),
    'd': ('Dilution', 'Verwässerung', 'Dilución'),
}
_LANGUAGES = ('en', 'de', 'es')
_NAVY, _TEAL, _PALE = (colors.HexColor(c) for c in ('#163248', '#167D88', '#F0F5F8'))


def pdf_path(ticker, language='es', *, scope='universe') -> Path:
    """Return a case-preserving, collision-free path for a canonical ticker."""
    if language not in _LANGUAGES or scope not in ('universe', 'market'):
        raise ValueError('Unknown PDF language or scope')
    if not isinstance(ticker, str) or not ticker.strip():
        raise ValueError('A nonempty canonical ticker is required')
    directory = Path('analysis-pdfs') / ('market' if scope == 'market' else '')
    return directory / f'{quote(ticker, safe="")}.{language}.pdf'


def _mapping(value):
    return value if isinstance(value, dict) else {}


def _fonts():
    if 'InvestorVera' not in pdfmetrics.getRegisteredFontNames():
        root = Path(reportlab.__file__).parent / 'fonts'
        pdfmetrics.registerFont(TTFont('InvestorVera', str(root / 'Vera.ttf')))
        pdfmetrics.registerFont(TTFont('InvestorVeraBold', str(root / 'VeraBd.ttf')))
        pdfmetrics.registerFontFamily('InvestorVera', normal='InvestorVera', bold='InvestorVeraBold')


def _safe(value):
    """Retain unsupported code points visibly instead of emitting missing glyphs."""
    supported = pdfmetrics.getFont('InvestorVera').face.charToGlyph
    chars = []
    for ch in str(value):
        if unicodedata.category(ch) == 'Pd' or ch == '\u2212':
            ch = '-'
        if ch in '\n\r\t':
            chars.append('\n' if ch == '\n' else ' ')
        elif ord(ch) in supported:
            chars.append(ch)
        else:
            chars.append(f'[U+{ord(ch):04X}]')
    return ''.join(chars)


def _number(value, missing):
    if value is None or isinstance(value, float) and not math.isfinite(value):
        return missing
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (int, float)):
        if value and abs(value) < .000001:
            return f'{value:.10g}'
        return f'{value:,.6f}'.rstrip('0').rstrip('.') if isinstance(value, float) else f'{value:,}'
    return str(value)


class _Report:
    def __init__(self, language):
        self.index = _LANGUAGES.index(language)
        self.story, self.seen_text = [], set()
        self.width = A4[0] - 80
        self.styles = {
            'body': ParagraphStyle('body', fontName='InvestorVera', fontSize=9, leading=13, spaceAfter=5,
                                   textColor=_NAVY, splitLongWords=True),
            'small': ParagraphStyle('small', fontName='InvestorVera', fontSize=8, leading=10.5,
                                    textColor=_NAVY, splitLongWords=True),
            'heading': ParagraphStyle('heading', fontName='InvestorVeraBold', fontSize=12, leading=16,
                                      textColor=_TEAL, spaceBefore=14, spaceAfter=7, keepWithNext=True),
            'title': ParagraphStyle('title', fontName='InvestorVeraBold', fontSize=22, leading=27,
                                    textColor=_NAVY, spaceAfter=8),
        }

    def tr(self, key):
        return _WORDS[key][self.index]

    def label(self, key):
        return _FIELDS[key][self.index] if key in _FIELDS else key

    def p(self, value, style='body', link=None):
        content = escape(_safe(_number(value, self.tr('unavailable')))).replace('\n', '<br/>')
        try:
            clickable = link and urlsplit(str(link)).scheme in ('http', 'https')
        except ValueError:
            clickable = False
        if clickable:
            content = f'<link href={quoteattr(str(link))} color="#167D88">{content}</link>'
        return Paragraph(content, self.styles[style])

    def heading(self, text):
        self.story.append(self.p(text, 'heading'))

    def table(self, rows, headers=None, widths=None):
        if not rows:
            return
        data = ([[self.p(h, 'small') for h in headers]] if headers else []) + [
            [self.p(cell, 'small') for cell in row] for row in rows]
        table = Table(data, colWidths=widths or [self.width*.38, self.width*.62],
                      repeatRows=1 if headers else 0, hAlign='LEFT', splitInRow=1)
        table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6), ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, _PALE]),
            ('LINEBELOW', (0, 0), (-1, -1), .25, colors.HexColor('#DAE3E9')),
        ]))
        self.story.extend([table, Spacer(1, 5)])

    def fields(self, data, title=None, compact=False):
        """Flatten supplied structures without truncation or numeric inference."""
        if title:
            self.heading(title)
        if data in ({}, []):
            return
        rows, paragraphs = [], []

        def walk(value, path=''):
            if isinstance(value, dict) and value:
                for key, child in value.items():
                    if key in ('sources', 'source_urls', 'financial_sources') or key.endswith('_url'):
                        continue  # Kept, with clickable links, in the source register.
                    walk(child, f'{path}.{key}' if path else key)
            elif isinstance(value, list) and value and any(isinstance(v, (dict, list)) for v in value):
                for i, child in enumerate(value, 1):
                    walk(child, f'{path}[{i}]')
            else:
                text = (', '.join(_number(v, self.tr('unavailable')) for v in value) or '[]') if isinstance(value, list) else value
                if isinstance(text, str) and len(text) > 180:
                    if text not in self.seen_text:
                        self.seen_text.add(text)
                        paragraphs.append((self.label(path), text))
                else:
                    rows.append((self.label(path), text if text not in ({}, []) else self.tr('unavailable')))

        walk(data)
        if compact == 'table' and rows:
            paired = [list(rows[i]) + (list(rows[i+1]) if i+1 < len(rows) else ['', ''])
                      for i in range(0, len(rows), 2)]
            self.table(paired, widths=[self.width*.24, self.width*.26]*2)
        elif compact and rows:
            text = '  |  '.join(f'{key}: {_number(value, self.tr("unavailable"))}' for key, value in rows)
            self.story.append(self.p(text, 'small'))
        else:
            self.table(rows, headers=[self.tr('field'), self.tr('value')])
        for label, text in paragraphs:
            self.story.append(self.p(label, 'small'))
            self.story.append(self.p(text))


def _sources(snapshot):
    """Include every distinct source record and URL, including nested research."""
    found, seen = [], set()

    def add(source):
        identity = json.dumps({k: v for k, v in source.items() if k != 'id'},
                              sort_keys=True, default=str, ensure_ascii=False)
        if identity not in seen:
            seen.add(identity)
            found.append(source)

    def walk(value, key=''):
        if isinstance(value, dict):
            if value.get('url'):
                add(value)
            for name, child in value.items():
                if name != 'url':
                    walk(child, name)
        elif isinstance(value, list):
            for child in value:
                walk(child, key)
        elif isinstance(value, str) and (key.endswith('_url') or key == 'source_urls'):
            add(dict(url=value))

    walk(snapshot.get('sources', []))
    walk(snapshot)
    detailed = {s['url'] for s in found if len(s) > 1}
    return [s for s in found if len(s) > 1 or s['url'] not in detailed]


def render_pdf(packet, language='es') -> bytes:
    """Render a packet snapshot in EN/DE/ES, retaining original research text."""
    if language not in _LANGUAGES:
        raise ValueError('Unknown PDF language')
    snapshot = _mapping(_mapping(packet).get('snapshot'))
    ticker = snapshot.get('ticker')
    pdf_path(ticker, language, scope=snapshot.get('scope', 'universe'))
    _fonts()
    r = _Report(language)
    inputs, research, origin = (_mapping(snapshot.get(k)) for k in ('inputs', 'research', 'origin'))
    dynamic = _mapping(inputs.get('dynamic_analysis'))
    output = _mapping(snapshot.get('model_output', snapshot.get('output')))
    market = snapshot.get('scope') == 'market'
    assessment = output if market else _mapping(output.get('assessment_at_cutoff') or output.get('assessment'))
    company = (_mapping(research.get('source_review')).get('issuer') or
               _mapping(research.get('scanner_note')).get('issuer') or inputs.get('name') or ticker)
    reviewed = bool(not market and assessment.get('review_status') == 'REVIEWED'
                    and assessment.get('quality_rank_eligible') and assessment.get('rating'))
    r.story.extend([r.p(r.tr('title'), 'title'), r.p(f'{company}  |  {ticker}'),
                    r.p(r.tr('reviewed') if reviewed else r.tr('review'), 'heading'), r.p(r.tr('notice'))])
    opportunity = _mapping(output.get('opportunity_at_cutoff') or output.get('opportunity'))
    if opportunity:
        r.heading({'en':'Automatic opportunity signal','de':'Automatisches Chancen-Signal',
                   'es':'Señal automática de oportunidad'}[language])
        r.fields({key:opportunity.get(key) for key in ('schema','label','score','score_lower','score_upper',
            'current_regime','current_fit','current_fit_bounds','financial_period','cash_flow_policy')},compact='table')
        r.fields(opportunity.get('profile',{}),'Business profile',compact=True)
        r.fields(opportunity.get('metrics',{}),'Valuation and financial quality',compact='table')
        r.fields(opportunity.get('regime_fit_bounds',{}),'Five-regime fit /100',compact='table')
        r.fields(opportunity.get('caps',[]),'Value-trap caps',compact=True)
        r.fields(opportunity.get('components',[]),'Opportunity score contributions',compact=True)
    if market:
        r.story.append(r.p(r.tr('screen'), 'heading'))
    r.table([('review_status', assessment.get('review_status')), ('packet.status', packet.get('status')),
             ('packet.can_approve', packet.get('can_approve')), ('approved_rating', assessment.get('rating') if reviewed else None)])
    r.fields(dict(captured_at=origin.get('captured_at'), as_of=origin.get('as_of'),
        quote_observed_at=dynamic.get('quote_observed_at') or inputs.get('quote_observed_at'),
        financial_period=dynamic.get('financial_period') or inputs.get('financial_period') or inputs.get('period_end'),
        financial_published_at=inputs.get('financial_published_at'),
        retrieved_at=dynamic.get('fetched_at') or inputs.get('financial_retrieved_at'),
        quote_currency=dynamic.get('currency') or inputs.get('cur') or inputs.get('currency'),
        financial_currency=dynamic.get('financial_currency') or (inputs.get('currency') if market else None),
        financial_unit=(dynamic.get('financial_currency') or inputs.get('currency')) if dynamic or market else inputs.get('financial_unit'),
        basis=dynamic.get('basis') or inputs.get('basis'), cash_flow_basis=inputs.get('cash_flow_basis')),
        r.tr('freshness'), compact='table')
    r.heading(r.tr('current'))
    if dynamic or market:
        r.story.append(r.p(r.tr('native_units'), 'small'))
    if not dynamic and not market:
        r.story.append(r.p(r.tr('unavailable')))
    valuation = _mapping(dynamic.get('valuation'))
    if valuation:
        r.fields({k:v for k,v in valuation.items() if k != 'scenarios'}, r.tr('valuation'))
        scenarios = valuation.get('scenarios') or []
        if scenarios:
            names = {'bear': ('Bear', 'Bär', 'Bajista'), 'base': ('Base', 'Basis', 'Base'),
                     'bull': ('Bull', 'Bulle', 'Alcista')}
            r.table([[names.get(s.get('name'), (s.get('name'),)*3)[r.index], s.get('growth_pct'), s.get('value_per_share')]
                     for s in scenarios], [r.tr('scenario'),r.tr('growth'),r.tr('per_share')],
                    [r.width*.34,r.width*.33,r.width*.33])
    for key in ('inputs', 'metrics', 'parameters'):
        value = dynamic.get(key)
        if market and key in ('inputs', 'metrics'):
            value = inputs.get('metrics') if key == 'inputs' else output.get('metrics', inputs.get('metrics'))
        r.fields(value, r.tr(key), compact='table')
    explanation = _mapping(dynamic.get('score_explanation') or output.get('score_explanation'))
    components = (explanation.get('components') or assessment.get('components') or
                  output.get('components') or inputs.get('components') or [])
    by_key = {c.get('key'): c for c in components if isinstance(c, dict)}
    weights = _mapping(origin.get('score_weights'))
    rows = []
    for key, labels in _CATEGORIES.items():
        component = by_key.get(key, {})
        def percent(value):
            return f'{value*100:g}%' if isinstance(value, (int, float)) and not isinstance(value, bool) else None
        rows.append([f'{labels[r.index]} ({key})', component.get('value', _mapping(dynamic.get('components')).get(key)),
                     percent(component.get('nominal_weight', component.get('weight', weights.get(key)))),
                     percent(component.get('effective_weight')), component.get('contribution')])
    r.heading(r.tr('scores'))
    r.table(rows, [r.tr(k) for k in ('component', 'value', 'nominal', 'effective', 'contribution')],
            [r.width*.34, r.width*.13, r.width*.16, r.width*.16, r.width*.21])
    r.story.append(r.p(r.tr('weights'), 'small'))
    r.fields({k: v for k, v in explanation.items() if k != 'components'}, compact=True)
    for text in dict.fromkeys(str(c['source']) for c in by_key.values() if c.get('source')):
        r.story.append(r.p(text, 'small'))
    output_keys = ('price', 'ngv', 'epv', 'cover', 'cushion', 'score', 'raw_verdict', 'verdict',
                   'valuation_gap', 'valuation_read', 'risk', 'r_wacc', 'beta', 'weight', 'note', 'regime',
                   'status', 'review_status', 'calculation_status', 'rank_eligible', 'quote_status',
                   'quote_observed_at', 'quote_age_hours', 'score_bounds', 'coverage_weight', 'source_limit')
    r.fields({k: output[k] for k in output_keys if k in output},
             r.tr('output') if dynamic or market else r.tr('archive'), compact=True)
    r.fields({k: v for k, v in assessment.items() if k not in
              ('components', 'issues', 'imputed_components')}, compact=True)
    diagnostics = _mapping(output.get('diagnostics'))
    r.fields({k: v for k, v in diagnostics.items() if k.endswith('_contract')}, compact=True)
    r.heading(r.tr('research'))
    r.story.append(r.p(r.tr('original'), 'small'))
    for key in ('thesis', 'counterargument', 'next_check', 'source_reason'):
        r.heading(r.tr(key))
        value = research.get(key) or _mapping(research.get('scanner_note')).get(key)
        r.story.append(r.p(value))
        if value:
            r.seen_text.add(value)
    r.fields({k: v for k, v in research.items() if k not in
              ('thesis', 'counterargument', 'next_check', 'source_reason', 'scanner_note')}, compact=True)
    r.heading(r.tr('saved_market') if market else r.tr('notes'))
    r.story.append(r.p(r.tr('native_units') if market else r.tr('engine_units'), 'small'))
    r.fields({k: v for k, v in inputs.items() if k not in
              ('dynamic_analysis', 'primary_analysis_archive', 'components', 'draft_components', 'sub')}, compact=True)
    if 'primary_analysis_archive' in inputs:
        r.heading(r.tr('archive'))
        r.story.append(r.p(r.tr('archive_note'), 'small'))
        archive = _mapping(inputs['primary_analysis_archive'])
        keys = ('score_fixed', 'built', 'financial_period', 'financial_published_at', 'fcf', 'fcf_ttm',
                'cash_flow_basis', 'shares', 'shares_asof', 'normalization_status', 'boot_note')
        r.fields({k: archive[k] for k in keys if k in archive}, compact=True)
    r.heading(r.tr('issues'))
    recorded = set()
    for key in ('issues', 'objections'):
        for item in snapshot.get(key) or []:
            if not isinstance(item, dict):
                r.story.append(r.p(item))
                continue
            identity = (item.get('id') or item.get('code'), item.get('severity'), item.get('status'), item.get('message'))
            signature = json.dumps(item, sort_keys=True, ensure_ascii=True)
            if signature in recorded:
                continue
            recorded.add(signature)
            label = ' | '.join(str(v) for v in identity[:3] if v is not None)
            r.story.append(r.p(f'{label}: {item.get("message", r.tr("unavailable"))}'))
            r.fields({k: v for k, v in item.items() if k not in ('id', 'code', 'severity', 'status', 'message')}, compact=True)
    r.heading(r.tr('sources'))
    sources = _sources(snapshot)
    if not sources:
        r.story.append(r.p(r.tr('unavailable')))
    for i, source in enumerate(sources, 1):
        r.story.append(r.p(f'{source.get("id", f"SRC-{i:03d}")}: {source.get("title") or r.tr("unavailable")}', 'small'))
        r.fields({k: v for k, v in source.items() if k not in ('id', 'title', 'url')}, compact=True)
        r.story.extend([r.p(source['url'], 'small', link=source['url']), Spacer(1, 5)])
    r.fields({k: v for k, v in dynamic.items() if k not in
              ('inputs', 'metrics', 'parameters', 'valuation', 'components', 'score_explanation', 'overlay')},
             r.tr('technical'), compact='table')
    r.fields({k: v for k, v in origin.items() if k not in ('macro', 'score_weights')}, r.tr('provenance'), compact=True)
    r.fields(dict(snapshot_sha256=packet.get('snapshot_sha256'), schema=packet.get('schema'),
                  scope=snapshot.get('scope')), compact=True)
    stream = BytesIO()
    document = SimpleDocTemplate(stream, pagesize=A4, leftMargin=40, rightMargin=40,
        topMargin=47, bottomMargin=43, title=f'{company} ({ticker}) - {r.tr("title")}',
        author='InvestorAce', pageCompression=1)

    def page(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(_NAVY)
        canvas.setFont('InvestorVeraBold', 8)
        canvas.drawString(40, A4[1]-28, 'InvestorAce')
        canvas.setFont('InvestorVera', 8)
        canvas.drawRightString(A4[0]-40, A4[1]-28, _safe(ticker))
        canvas.setStrokeColor(_TEAL)
        canvas.line(40, 31, A4[0]-40, 31)
        canvas.setFont('InvestorVera', 7)
        canvas.drawString(40, 19, _safe(r.tr('title')))
        canvas.drawRightString(A4[0]-40, 19, f'{r.tr("page")} {doc.page}')
        canvas.restoreState()

    document.build(r.story, onFirstPage=page, onLaterPages=page)
    return stream.getvalue()
