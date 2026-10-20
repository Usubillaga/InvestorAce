#!/usr/bin/env python3
"""Dated Enagas equity-cash-flow scenarios; never changes engine scores or NGV."""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from urllib.parse import urlsplit

from integrity import atomic_text

VERSION = 'enagas-fcfe-scenarios-v1'


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('Model inputs must be finite numbers')
    return float(value)


def _time(value):
    stamp = datetime.fromisoformat(value)
    if stamp.tzinfo is None:
        raise ValueError('Model timestamps require a timezone')
    return stamp


def dcf(cash, growth, cost_of_equity, terminal_growth, shares, *, years=5,
        one_off_cost=0, extra_cash_call=0):
    """Interest-paid equity cash; t=1..N, then a Gordon terminal value.

    Net borrowing is assumed zero (ordinary debt refinanced). Debt and the
    completed Terega purchase are not deducted a second time. Pending acquisition
    cost is immediate. Extra annual calls apply only to the explicit horizon.
    """
    cash, growth, rate, terminal, shares, oneoff, extra = map(
        _number, (cash, growth, cost_of_equity, terminal_growth, shares,
                  one_off_cost, extra_cash_call))
    if (cash <= 0 or shares <= 0 or growth <= -1 or rate <= 0 or
            terminal <= -1 or rate <= terminal or oneoff < 0 or extra < 0 or
            type(years) is not int or not 1 <= years <= 50):
        raise ValueError('Invalid equity cash flow, horizon or terminal assumptions')
    gross = [cash * (1 + growth) ** t for t in range(1, years + 1)]
    flows = [value - extra for value in gross]
    present = [value / (1 + rate) ** t for t, value in enumerate(flows, 1)]
    terminal_value = gross[-1] * (1 + terminal) / (rate - terminal)
    pv_terminal = terminal_value / (1 + rate) ** years
    gross_value = sum(present) + pv_terminal
    equity = gross_value - oneoff
    return dict(per_share=equity / shares, equity_value=equity,
                cash_flows=flows, present_cash_flows=present,
                terminal_value=terminal_value, pv_terminal=pv_terminal,
                terminal_share=pv_terminal / gross_value if gross_value > 0 else None,
                one_off_cost=oneoff)


def reverse_growth(price, cash, cost_of_equity, terminal_growth, shares, *,
                   years=5, one_off_cost=0):
    """Solve five-year cash CAGR; terminal growth stays independently fixed."""
    price = _number(price)
    if price <= 0:
        raise ValueError('Reverse DCF requires a positive reference quote')
    def value(growth):
        return dcf(cash, growth, cost_of_equity, terminal_growth, shares,
                   years=years, one_off_cost=one_off_cost)['per_share']
    low, high = -.95, 1.0
    if not value(low) <= price <= value(high):
        return None
    for _ in range(100):
        middle = (low + high) / 2
        if value(middle) < price:
            low = middle
        else:
            high = middle
    return (low + high) / 2


def load(path=None):
    path = Path(path) if path else Path(__file__).with_name('enagas_review.json')
    doc = json.loads(path.read_text(encoding='utf-8'))
    json.dumps(doc, allow_nan=False)
    if doc.get('schema') != 'enagas-valuation-v1' or doc.get('currency') != 'EUR':
        raise ValueError('Unsupported Enagas valuation schema or currency')
    _time(doc['as_of'])
    if doc['quote']['currency'] != doc['currency']:
        raise ValueError('Quote and valuation currency mismatch')
    if doc['review']['approved_rating'] is not None or doc['review']['fundamental_score'] is not None:
        raise ValueError('This unresolved scenario review cannot approve a rating or composite')
    if doc['method']['net_debt_deduction_m'] != 0 or doc['method']['net_borrowing_m'] != 0:
        raise ValueError('The published equity scenario assumes zero net borrowing and no debt deduction')
    for source in doc['sources']:
        parsed = urlsplit(source['url'])
        if (parsed.scheme != 'https' or not parsed.hostname or
                parsed.username or parsed.password):
            raise ValueError('Evidence sources must be safe HTTPS URLs')
    return doc


def build_model(doc, now=None):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('Build time requires a timezone')
    facts = doc['facts']
    ttm = facts['ffo_fy2025'] - facts['ffo_9m2025'] + facts['ffo_9m2026']
    wc_ttm = (facts['wc_outflow_fy2025'] - facts['wc_outflow_9m2025']
              + facts['wc_outflow_9m2026'])
    shares, price = _number(doc['shares_m']), _number(doc['quote']['value'])
    if shares <= 0 or price <= 0:
        raise ValueError('Positive share proxy and quote required')
    age = (now - _time(doc['quote']['as_of'])).total_seconds() / 3600
    fresh = 0 <= age <= doc['quote_max_age_hours']
    cases = {}
    for name in ('bear', 'base', 'bull'):
        assumptions = doc['cases'][name]
        starting = assumptions['ffo'] - sum(assumptions[key] for key in
                   ('capex', 'working_capital', 'lease_principal', 'other_cash_reserve'))
        result = dcf(starting, assumptions['growth'], assumptions['cost_of_equity'],
                     assumptions['terminal_growth'], shares, years=doc['years'],
                     one_off_cost=doc['pending_acquisition_cost_m'])
        cases[name] = dict(result, starting_cash=starting,
                           assumptions=assumptions, price_gap=result['per_share'] / price - 1)
    base = cases['base']
    assumptions = base['assumptions']
    reverse = reverse_growth(price, base['starting_cash'],
                             assumptions['cost_of_equity'], assumptions['terminal_growth'],
                             shares, years=doc['years'],
                             one_off_cost=doc['pending_acquisition_cost_m'])
    funding = []
    for extra in (0, 50, 100, 200):
        result = dcf(base['starting_cash'], assumptions['growth'],
                     assumptions['cost_of_equity'], assumptions['terminal_growth'],
                     shares, years=doc['years'],
                     one_off_cost=doc['pending_acquisition_cost_m'], extra_cash_call=extra)
        funding.append(dict(extra_annual_cash_m=extra, per_share=result['per_share']))
    sensitivity = []
    for rate in (.07, .08, .09, .10):
        sensitivity.append(dict(cost_of_equity=rate, values=[
            dcf(base['starting_cash'], assumptions['growth'], rate, terminal,
                shares, years=doc['years'], one_off_cost=doc['pending_acquisition_cost_m'])['per_share']
            for terminal in (0, .01, .02)]))
    return dict(version=VERSION, as_of=doc['as_of'], calculated_at=now.isoformat(),
                quote=doc['quote'], quote_fresh=fresh, quote_age_hours=age,
                ttm_ffo=ttm, ttm_working_capital_outflow=wc_ttm,
                transaction_adjusted_9m_cash=(facts['fcf_9m2026'] +
                    facts['terega_acquisition'] - facts['renovable_sale']),
                investment_residual=(facts['net_investment_9m2026'] -
                    facts['terega_acquisition'] - facts['gas_investment_9m'] + facts['renovable_sale']),
                dividend_funding=shares * facts['dividend_per_share'],
                payout_proxy=shares * facts['dividend_per_share'] / facts['profit_guidance_fy2026'],
                dividend_yield=facts['dividend_per_share'] / price,
                zero_growth_cash_hurdle=price * shares * assumptions['cost_of_equity'],
                cases=cases, reverse_growth=reverse, funding_sensitivity=funding,
                rate_sensitivity=sensitivity, ngv=None, cover=None, cushion=None,
                fundamental_score=None, approved_rating=None,
                research_view='WATCH', review_status='blocked_data', readiness='screen-grade',
                scenario_rating=doc['review']['conditional_scenario_stance'] if fresh else None,
                historical_scenario_rating=doc['review']['conditional_scenario_stance'],
                sources=doc['sources'], issues=doc['issues'])


def _table(headers, rows):
    head = ''.join('<th>' + escape(str(value)) + '</th>' for value in headers)
    body = ''.join('<tr>' + ''.join('<td>' + escape(str(value)) + '</td>' for value in row)
                   + '</tr>' for row in rows)
    return '<div class="scroll"><table><thead><tr>' + head + '</tr></thead><tbody>' + body + '</tbody></table></div>'


def site_pages(root, now=None):
    path = Path(root) / 'enagas_review.json'
    if not path.exists():
        return []
    doc = load(path)
    model = build_model(doc, now=now)
    pages = [(Path(name), render(doc, model, language))
             for language, name in (('en', 'enagas.html'), ('de', 'enagas.de.html'),
                                    ('es', 'enagas.es.html'))]
    pages += [(Path('enagas-review.json'), json.dumps(model, ensure_ascii=False, indent=2, allow_nan=False) + '\n'),
              (Path('enagas-inputs.json'), json.dumps(doc, ensure_ascii=False, indent=2, allow_nan=False) + '\n')]
    return pages


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).parent)
    parser.add_argument('--output', type=Path, default=Path('research-output/enagas'))
    args = parser.parse_args()
    pages = site_pages(args.root)
    args.output.mkdir(parents=True, exist_ok=True)
    for name, content in pages:
        atomic_text(args.output / name, content)
    print(f'Enagas dated scenario review: {len(pages)} pages/data files')


COPY = {
'en': {
'title': 'Enagas: DCF and reverse DCF', 'back': 'Scoreboard', 'headline': 'Income is visible. Funding remains the test.',
'stance': 'Conditional scenario stance', 'pending': 'Approved rating: pending', 'watch': 'Watch / wait for proof',
'hero': 'The continuity case offers no clear margin of safety at the reference quote. Cash normalisation and the hydrogen funding plan remain unresolved. The displayed HOLD NEG is an assumption-led scenario view, not an approved investment rating.',
'price': 'Reference quote', 'fair': 'Conditional base DCF', 'reverse': 'Required five-year cash CAGR',
'dated': 'Dated snapshot; quote', 'stale': 'Quote outside the 24-hour policy: current scenario stance withdrawn. Historical calculations remain dated to the recorded quote.',
'facts': 'Reported evidence', 'metric': 'Measure', 'value': 'EUR million unless stated', 'source': 'Source',
'ffo': 'Rolling 12-month FFO', 'wc': 'Rolling working-capital cash outflow', 'profit': '9M recurring net profit',
'debt': 'Net debt / reported leverage', 'dividend': 'Annual dividend policy / gross yield',
'bridge': 'From reported FFO to an assumed equity cash flow', 'item': 'Cash-flow bridge', 'bear': 'Bear', 'base': 'Base', 'bull': 'Bull',
'bridge_note': 'Only the EUR 612m rolling FFO and the EUR 225m 2026 investment target have reported anchors. Carrying those amounts forward is an assumption. Working capital, lease cash payments and the additional recurring-cash reserve are analyst estimates. The lease-maturity chart indicates approximately EUR 25m annually, not a reconciled principal-payment forecast. Historical rolling working-capital absorption was EUR 241.1m, far above the assumed base EUR 50m.',
'capex': 'All-case investment allowance', 'lease': 'Lease-cash allowance', 'other': 'Other recurring-cash reserve', 'cash': 'Starting cash before net borrowing',
'cash_note': 'The reported 9M FCF is -341.2. Adding back the completed Terega acquisition 573 and removing disposal proceeds 48 gives 183.8 for nine months. It is not annualised into sustainable FCF. Named investment components leave a9.9 allocation gap.',
'cases': 'Five-year equity DCF scenarios', 'growth': 'Cash CAGR', 'rate': 'Cost of equity', 'terminal': 'Terminal growth', 'per_share': 'EUR / share', 'gap': 'Versus quote',
'method': 'Five forward annual payments, first at t=1; C(t)=C0*(1+h)^t. Equity value=sum[C(t)/(1+Ke)^t]+[C5*(1+gT)/(Ke-gT)]/(1+Ke)^5-31. Divide by261.990074m issued shares. Ke is an analyst assumption, not WACC or the regulated return. Interest and affiliate dividends are already in FFO; no second net-debt deduction or affiliate valuation is added. Zero net ordinary borrowing assumes debt refinancing. The imminent Saggas cost 31 is deducted immediately with no incremental benefit assigned. This conservative cost-only treatment is not a full acquisition valuation.',
'terminal_note': 'Terminal value contributes {terminal:.1%} of base value before the immediate acquisition deduction. Cases are sensitivities, not probability-weighted forecasts. Growth implicitly scales the starting cash-flow bridge; it is not verified delivered cash growth.',
'reverse_note': 'At EUR 17.25, the base starting cash 300, Ke8% and terminal growth 1% require approximately {growth:.2%} annual cash growth in forward years 1-5. The terminal growth rate is held fixed. The zero-growth cash hurdle at8% is EUR {hurdle:.1f}m annually, before the separate acquisition cost. Neither number establishes actual FCF or a cash-growth cushion.',
'sensitivity': 'Rate and terminal-growth sensitivity', 'funding': 'Additional cash calls change value', 'extra': 'Extra annual cash, years 1-5', 'funding_note': 'These cash calls are incremental to the investment allowance already deducted. They receive no terminal cash benefit. This is a funding stress, not an engineering budget or a full debt/share-issuance model. The historical 2025 strategy envisaged EUR 3.125bn hydrogen investment by2030. The EUR 225m annual extension does not model that complete programme; paired returns, grants, borrowing and dilution are unresolved.',
'risks': 'What remains open', 'risk1': 'Normalised working capital, cash tax and lease payments; sustainable annual equity cash is not established.',
'risk2': 'The company-specific 2027 remuneration bridge and full-year Terega cash distributions and financing.',
'risk3': 'Hydrogen construction schedule, binding demand, grants, debt costs and potential share issuance.',
'risk4': 'Issued shares are a proxy; treasury-adjusted and diluted outstanding shares need reconciliation.',
'framework': 'InvestorAce review status', 'framework_note': 'Fundamental composite: unavailable. Legacy published total 6.0/10 remains unreviewed. NGV, cover and cushion stay unavailable. Regime fit is separate and is not rescored. No score weights, portfolio sizes or rotation rules change. Dividend policy implies about EUR 262m annual funding and 111.5% of guided recurring profit on the issued-share proxy; accounting payout alone does not prove a cut.',
'triggers': 'What would change the view', 'triggers_note': 'Upgrade evidence: recurring cash after all investment and funding needs supports the valuation with a margin of safety, and the 2027 bridge and hydrogen financing are documented. Re-underwrite after weaker recurring cash, cost overruns, refinancing pressure or dilution. A price decline alone cannot close the source gaps; no forced sale is implied.',
'review': 'Review record and reproducibility', 'review_note': 'Three isolated first-pass analyst roles reviewed the same packet. The coordinator performed the second-round arithmetic and decision-gate review after the agents hit a usage limit. This is not independent source authentication. Material normalisation and funding objections remain open.',
'sources': 'Primary sources', 'downloads': 'Calculation sheet', 'inputs': 'Frozen inputs', 'period': 'Forward year', 'forecast': 'Base equity cash, EURm',
'confidence': 'Reported facts / derived arithmetic; assumptions; analyst inference are separated. Scenario values are screen-grade and dated, not live targets.'
},
'de': {
'title': 'Enagas: DCF und Reverse DCF', 'back': 'Scoreboard', 'headline': 'Die Dividende ist sichtbar. Die Finanzierung bleibt offen.',
'stance': 'Bedingte Szenario-Einstufung', 'pending': 'Freigegebenes Rating: ausstehend', 'watch': 'Beobachten / Nachweise abwarten',
'hero': 'Das Fortführungsszenario bietet beim Referenzkurs keine klare Sicherheitsmarge. Cashflow-Normalisierung und Wasserstofffinanzierung bleiben ungeklärt. HOLD NEG ist eine annahmebasierte Szenario-Einschätzung, kein freigegebenes Investmentrating.',
'price': 'Referenzkurs', 'fair': 'Bedingter Basis-DCF', 'reverse': 'Erforderliches Cashflow-Wachstum über fünf Jahre',
'dated': 'Datierter Stand; Kurs', 'stale': 'Kurs außerhalb der 24-Stunden-Regel: aktuelle Szenario-Einstufung zurückgezogen. Die historischen Rechnungen behalten ihren ausgewiesenen Kursstand.',
'facts': 'Veröffentlichte Grundlagen', 'metric': 'Kennzahl', 'value': 'Mio. EUR, sofern nicht anders angegeben', 'source': 'Quelle',
'ffo': 'FFO der letzten zwölf Monate', 'wc': 'Working-Capital-Abfluss der letzten zwölf Monate', 'profit': 'Bereinigter Neunmonatsgewinn',
'debt': 'Nettoschulden / ausgewiesene Verschuldung', 'dividend': 'Jährliche Dividendenpolitik / Bruttorendite',
'bridge': 'Vom veröffentlichten FFO zum angenommenen Eigenkapital-Cashflow', 'item': 'Cashflow-Brücke', 'bear': 'Negativ', 'base': 'Basis', 'bull': 'Positiv',
'bridge_note': 'Veröffentlichte Anker sind der rollierende FFO von 612 Mio. EUR und das Investitionsziel 2026 von 225 Mio. EUR. Ihre Fortschreibung ist eine Annahme. Working Capital, Leasingzahlungen und die zusätzliche Reserve sind Analystenschätzungen. Der Fälligkeitenplan nennt ungefähr 25 Mio. EUR Leasing pro Jahr, keine vollständig abgestimmte Tilgungsprognose. Der tatsächliche rollierende Working-Capital-Abfluss von 241,1 Mio. EUR liegt deutlich über den 50 Mio. EUR im Basisszenario.',
'capex': 'Investitionsbudget einschließlich Wachstum', 'lease': 'Ansatz für Leasingzahlungen', 'other': 'Reserve für weitere laufende Cash-Abflüsse', 'cash': 'Ausgangscashflow vor Nettoneuverschuldung',
'cash_note': 'Der gemeldete Neunmonats-FCF beträgt -341,2. Hinzurechnung des abgeschlossenen Terega-Kaufs 573 und Abzug des Verkaufserlöses 48 ergeben 183,8 für neun Monate. Dieser Betrag wird nicht als nachhaltiger Jahres-FCF hochgerechnet. Bei den benannten Investitionsbestandteilen bleiben 9,9 ungeklärt.',
'cases': 'Eigenkapital-DCF über fünf Jahre', 'growth': 'Cashflow-Wachstum', 'rate': 'Eigenkapitalzins', 'terminal': 'Terminalwachstum', 'per_share': 'EUR je Aktie', 'gap': 'Zum Referenzkurs',
'method': 'Fünf zukünftige Jahreszahlungen, erstmals bei t=1; C(t)=C0*(1+h)^t. Eigenkapitalwert=Summe[C(t)/(1+Ke)^t]+[C5*(1+gT)/(Ke-gT)]/(1+Ke)^5-31. Division durch 261,990074 Mio. ausgegebene Aktien. Ke ist eine Analystenannahme, kein WACC und keine regulierte Rendite. Zinsen und Beteiligungsdividenden sind bereits im FFO berücksichtigt; weder Nettoschulden noch Beteiligungswerte werden nochmals verrechnet. Keine Nettoneuverschuldung setzt die Refinanzierung bestehender Schulden voraus. Der bevorstehende Saggas-Kauf 31 wird sofort abgezogen; Zusatz-Cashflows werden mangels Nachweis nicht angesetzt. Diese vorsichtige reine Kostenbetrachtung ist keine vollständige Übernahmebewertung.',
'terminal_note': 'Der Terminalwert trägt {terminal:.1%} zum Basiswert vor dem sofortigen Übernahmeabzug bei. Die Szenarien sind Sensitivitäten ohne zugewiesene Wahrscheinlichkeiten. Das Wachstum skaliert implizit die Ausgangs-Cashflow-Brücke und ist kein nachgewiesenes geliefertes Cashflow-Wachstum.',
'reverse_note': 'Bei 17,25 EUR, einem Ausgangscashflow von 300 Mio. EUR,8% Eigenkapitalzins und 1% Terminalwachstum verlangt der Kurs etwa {growth:.2%} jährliches Cashflow-Wachstum in den fünf Prognosejahren. Das Terminalwachstum bleibt dabei unverändert. Ohne Wachstum beträgt die Cashflow-Hürde bei 8% jährlich {hurdle:.1f} Mio. EUR, vor dem separaten Kaufpreisabzug. Beides beweist weder tatsächlichen FCF noch einen Cashflow-Cushion.',
'sensitivity': 'Sensitivität für Zins und Terminalwachstum', 'funding': 'Zusätzlicher Finanzierungsbedarf verändert den Wert', 'extra': 'Zusätzlicher jährlicher Cash-Bedarf, Jahre 1-5', 'funding_note': 'Diese Abflüsse kommen zum bereits abgezogenen Investitionsbudget hinzu. Ein zusätzlicher Terminalnutzen wird nicht unterstellt. Das ist ein Finanzierungstest, kein vollständiger Bau-, Schulden- oder Kapitalerhöhungsplan. Die historische Strategie 2025 sah 3,125 Mrd. EUR Wasserstoffinvestitionen bis 2030 vor. Die Fortschreibung von 225 Mio. EUR pro Jahr bildet dieses Programm nicht vollständig ab; zugehörige Erträge, Fördermittel, Kredite und Verwässerung bleiben ungeklärt.',
'risks': 'Offene Einwände', 'risk1': 'Normalisiertes Working Capital, Cash-Steuern und Leasingzahlungen; nachhaltiger jährlicher Eigenkapital-Cashflow ist nicht belegt.',
'risk2': 'Unternehmensspezifische Vergütungsbrücke 2027 sowie ganzjährige Terega-Ausschüttungen und Finanzierung.',
'risk3': 'Wasserstoff-Bauplan, verbindliche Nachfrage, Fördermittel, Finanzierungskosten und mögliche Kapitalerhöhungen.',
'risk4': 'Ausgegebene Aktien sind ein Näherungswert; eigene Aktien und verwässerte ausstehende Aktien müssen abgestimmt werden.',
'framework': 'InvestorAce-Prüfstatus', 'framework_note': 'Geprüfter Fundamentalscore: nicht verfügbar. Die veröffentlichte Legacy-Gesamtnote 6,0/10 bleibt ungeprüft. NGV, Cover und Cushion bleiben offen. Regime-Fit wird getrennt behandelt und nicht neu bewertet. Gewichte, Positionsgrößen und Rotationsregeln bleiben bestehen. Die Dividendenpolitik erfordert rechnerisch etwa 262 Mio. EUR jährlich beziehungsweise 111,5% des erwarteten bereinigten Gewinns. Diese Gewinnquote allein belegt keine Kürzung.',
'triggers': 'Was die Einschätzung ändern würde', 'triggers_note': 'Für eine Aufwertung: nachhaltiger Cashflow nach sämtlichen Investitionen und Finanzierungsbedarfen deckt den Wert mit Sicherheitsmarge; die Brücke 2027 und die Wasserstofffinanzierung sind dokumentiert. Neue Prüfung bei schwächerem laufendem Cashflow, Kostenüberschreitungen, Refinanzierungsdruck oder Verwässerung. Ein Kursrückgang allein schließt Datenlücken nicht; daraus folgt keine erzwungene Verkaufsregel.',
'review': 'Prüfprotokoll und Nachvollziehbarkeit', 'review_note': 'Drei getrennte Analystenrollen prüften in Runde eins dasselbe Quellenpaket. Die zweite Rechen- und Entscheidungsprüfung führte der Koordinator durch, nachdem die Agenten am Nutzungslimit scheiterten. Das ist keine unabhängige Quellenbestätigung. Wesentliche Einwände zu Normalisierung und Finanzierung bleiben offen.',
'sources': 'Primärquellen', 'downloads': 'Berechnungen', 'inputs': 'Eingefrorene Eingaben', 'period': 'Prognosejahr', 'forecast': 'Basis-Cashflow für Aktionäre, Mio. EUR',
'confidence': '[Sicher] Veröffentlichte Angaben und Rechenwege. [Vermutung] Modellannahmen. [Wahrscheinlich] Analysteneinschätzung. Die Szenariowerte sind datierte Orientierung, keine aktuellen Kursziele.'
},
'es': {
'title': 'Enagas: DCF y DCF inverso', 'back': 'Scoreboard', 'headline': 'El dividendo es visible. La financiación sigue abierta.',
'stance': 'Opinión condicional del escenario', 'pending': 'Rating aprobado: pendiente', 'watch': 'Observar / esperar pruebas',
'hero': 'El escenario de continuidad no ofrece un margen de seguridad claro al precio de referencia. La normalización de caja y la financiación del hidrógeno siguen abiertas. HOLD NEG es una opinión basada en supuestos, no un rating de inversión aprobado.',
'price': 'Precio de referencia', 'fair': 'DCF base condicional', 'reverse': 'Crecimiento de caja exigido durante cinco años',
'dated': 'Análisis fechado; cotización', 'stale': 'Cotización fuera del límite de24 horas: se retira la opinión actual. Los cálculos históricos mantienen su fecha de referencia.',
'facts': 'Datos publicados', 'metric': 'Indicador', 'value': 'Millones de EUR salvo indicación', 'source': 'Fuente',
'ffo': 'FFO de los últimos doce meses', 'wc': 'Salida de circulante de los últimos doce meses', 'profit': 'Beneficio recurrente de nueve meses',
'debt': 'Deuda neta / apalancamiento publicado', 'dividend': 'Política anual de dividendo / rentabilidad bruta',
'bridge': 'Del FFO publicado al flujo de caja supuesto para el accionista', 'item': 'Puente de caja', 'bear': 'Bajista', 'base': 'Base', 'bull': 'Alcista',
'bridge_note': 'Las referencias publicadas son el FFO móvil 612 y la inversión objetivo 2026 de225. Mantenerlas a futuro es un supuesto. Circulante, pagos de arrendamientos y reserva adicional son estimaciones del analista. El calendario indica aproximadamente 25 anuales en arrendamientos, no una previsión conciliada de principal. La salida móvil de circulante observada 241,1 supera ampliamente los 50 del caso base.',
'capex': 'Inversión incluida la de crecimiento', 'lease': 'Reserva para arrendamientos', 'other': 'Reserva para otros pagos recurrentes', 'cash': 'Caja inicial antes de endeudamiento neto',
'cash_note': 'El FCF publicado de nueve meses es -341,2. Sumar la compra completada de Terega 573 y restar la venta 48 da183,8 para nueve meses. No se anualiza como FCF sostenible. Quedan 9,9 sin asignar entre los componentes principales de inversión.',
'cases': 'DCF del accionista a cinco años', 'growth': 'Crecimiento de caja', 'rate': 'Coste del capital propio', 'terminal': 'Crecimiento terminal', 'per_share': 'EUR por acción', 'gap': 'Frente al precio',
'method': 'Cinco pagos anuales futuros, primero en t=1; C(t)=C0*(1+h)^t. Valor del capital=suma[C(t)/(1+Ke)^t]+[C5*(1+gT)/(Ke-gT)]/(1+Ke)^5-31. Dividir por 261,990074 millones de acciones emitidas. Ke es un supuesto del analista, no WACC ni rentabilidad regulada. FFO ya incluye intereses y dividendos de participadas; no se vuelve a restar deuda neta ni a sumar valor de participadas. El endeudamiento neto cero supone refinanciar deuda existente. Se resta inmediatamente la compra pendiente de Saggas 31, sin asignar aportación adicional no verificada. Este tratamiento conservador de coste no es una valoración completa de la adquisición.',
'terminal_note': 'El terminal aporta {terminal:.1%} del valor base antes del coste inmediato. Son sensibilidades sin probabilidades. El crecimiento escala implícitamente el puente de caja inicial; no es crecimiento de caja realizado y verificado.',
'reverse_note': 'Con 17,25 EUR, caja inicial 300, Ke8% y crecimiento terminal 1%, el precio exige aproximadamente {growth:.2%} de crecimiento anual de caja durante los cinco años explícitos. El crecimiento terminal permanece fijo. Sin crecimiento, el umbral de caja al8% es {hurdle:.1f} millones anuales, antes del coste separado de adquisición. Ningún resultado demuestra FCF real ni un colchón de crecimiento de caja.',
'sensitivity': 'Sensibilidad al coste de capital y crecimiento terminal', 'funding': 'Las necesidades adicionales de financiación cambian el valor', 'extra': 'Caja adicional anual, años 1-5', 'funding_note': 'Son pagos adicionales a la inversión ya deducida, sin beneficio terminal añadido. Es un estrés de financiación, no un presupuesto de ingeniería ni un modelo completo de deuda o ampliación de capital. La estrategia histórica 2025 preveía 3.125 millones en hidrógeno hasta 2030. Extender 225 anuales no representa ese programa completo; retornos, subvenciones, financiación y dilución siguen sin conciliar.',
'risks': 'Objeciones pendientes', 'risk1': 'Circulante normalizado, impuestos de caja y arrendamientos: la caja anual sostenible del accionista no está verificada.',
'risk2': 'Puente de remuneración 2027 específico de Enagas y dividendos y financiación de Terega durante un año completo.',
'risk3': 'Calendario de construcción de hidrógeno, demanda vinculante, ayudas, costes de financiación y posibles nuevas acciones.',
'risk4': 'Las acciones emitidas son una aproximación; faltan acciones en circulación netas de autocartera y diluidas.',
'framework': 'Estado de revisión InvestorAce', 'framework_note': 'Puntuación fundamental auditada: no disponible. El total histórico 6,0/10 sigue sin revisar. NGV, cobertura y cushion permanecen no disponibles. La adecuación al régimen se mantiene separada y no se recalcula. No cambian pesos, posiciones ni reglas de rotación. El dividendo implica unos 262 millones anuales o111,5% del beneficio recurrente previsto; el payout contable por sí solo no demuestra un recorte.',
'triggers': 'Qué cambiaría la opinión', 'triggers_note': 'Mejora: caja sostenible tras toda inversión y necesidad de financiación justifica un margen de seguridad, con puente 2027 y financiación del hidrógeno documentados. Revisar ante menor caja recurrente, sobrecostes, presión de refinanciación o dilución. Una caída del precio no resuelve datos faltantes y no impone una venta.',
'review': 'Registro de revisión y reproducibilidad', 'review_note': 'Tres roles separados revisaron el mismo paquete en la primera ronda. El coordinador realizó la segunda comprobación aritmética y de decisiones cuando los agentes alcanzaron el límite de uso. No constituye autenticación independiente. Permanecen objeciones materiales de normalización y financiación.',
'sources': 'Fuentes primarias', 'downloads': 'Cálculos', 'inputs': 'Datos congelados', 'period': 'Año futuro', 'forecast': 'Caja base del accionista, millones EUR',
'confidence': 'Se separan datos publicados, cálculos, supuestos e interpretación. Las valoraciones son escenarios fechados de orientación, no objetivos actuales.'
}}


CSS = """
:root{color-scheme:dark;--bg:#0c1015;--card:#151c25;--line:#2b3543;--text:#ecf0f4;--muted:#a8b7c9;--accent:#bedba0}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.6 system-ui,sans-serif}
main{max-width:1120px;margin:auto;padding:30px 24px 70px}a{color:var(--accent)}nav{display:flex;flex-wrap:wrap;gap:18px;justify-content:space-between}
.kicker,small{color:var(--muted)}.kicker{text-transform:uppercase;letter-spacing:.15em;font-size:12px}
h1{font-size:clamp(30px,5vw,55px);line-height:1.08;max-width:850px;margin:28px 0 20px}h2{font-size:23px;line-height:1.25;margin:0 0 18px}
.cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}.card,section{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:23px;margin:20px 0}
.card{margin:0}.big{font-size:32px;font-weight:750;line-height:1.3}.pill{display:inline-block;border:1px solid #b69a62;color:#e7ce9c;border-radius:30px;padding:5px 12px;font-size:13px}
.warning{border-left:4px solid #cfaa65;padding:12px 18px;background:#28241d}.muted{color:var(--muted)}.scroll{overflow:auto;max-width:100%}
table{border-collapse:collapse;width:100%;font-size:14px;font-variant-numeric:tabular-nums}td,th{border-bottom:1px solid var(--line);padding:11px 12px;text-align:right;white-space:nowrap}
td:first-child,th:first-child{text-align:left}th{color:var(--muted);font-weight:600}td:first-child{white-space:normal;min-width:150px}.mono{font-family:ui-monospace,monospace}
p,li{overflow-wrap:anywhere}.formula{background:#0b1118;padding:15px;border-radius:8px}ul{padding-left:22px}li{margin:8px 0}
@media(max-width:650px){main{padding:20px 14px 50px}.cards{grid-template-columns:1fr}.card,section{padding:18px}.big{font-size:29px}}
"""


def render(doc, model, language):
    text = COPY[language]
    base = model['cases']['base']
    fmt = lambda value: f'{value:,.2f}'
    pct = lambda value: 'N/A' if value is None else f'{value:.2%}'
    ref = lambda value: '<a href="#' + value + '">' + value + '</a>'
    section = lambda title, body: '<section><h2>' + escape(title) + '</h2>' + body + '</section>'
    paragraph = lambda value: '<p>' + escape(value) + '</p>'
    stance = model['scenario_rating'] or text['watch']
    nav = ('<nav><a href="' + ('index.html' if language == 'en' else 'index.' + language + '.html') +
           '">' + escape(text['back']) + '</a><span><a href="enagas.html">EN</a> · '
           '<a href="enagas.de.html">DE</a> · <a href="enagas.es.html">ES</a></span></nav>')
    hero = ('<p class="kicker">InvestorAce research · ENG / BME · EUR · 20 Oct 2026</p><h1>' +
            escape(text['headline']) + '</h1><span class="pill">' + escape(stance) +
            ' · ' + escape(text['stance']) + '</span><p>' + escape(text['hero']) +
            '</p><p class="muted">' + escape(text['pending']) + ' · screen-grade</p>')
    quote = doc['quote']
    hero += paragraph(text['dated'] + ': ' + quote['as_of'] + ' · EUR ' + fmt(quote['value']))
    if not model['quote_fresh']:
        hero += '<p class="warning">' + escape(text['stale']) + '</p>'
    cards = '<div class="cards">' + ''.join(
        '<div class="card"><small>' + escape(label) + '</small><div class="big">' + escape(value) +
        '</div><small>' + escape(detail) + '</small></div>' for label, value, detail in [
            (text['price'], '€' + fmt(quote['value']), 'EV-QUOTE · 20 Oct 2026 17:40 CEST'),
            (text['fair'], '€' + fmt(base['per_share']), pct(base['price_gap'])),
            (text['reverse'], pct(model['reverse_growth']), 'Ke 8% · gT 1% · C0 EUR300m')]) + '</div>'
    facts = doc['facts']
    fact_rows = [
        (text['ffo'], fmt(model['ttm_ffo']), 'EV-FY / EV-9M'),
        (text['wc'], fmt(model['ttm_working_capital_outflow']), 'EV-FY / EV-9M'),
        (text['profit'], fmt(facts['recurring_profit_9m']) + ' / -5.4%', 'EV-9M'),
        (text['debt'], fmt(facts['net_debt']) + ' / 4.6x', 'EV-9M'),
        (text['dividend'], 'EUR1.00 / ' + pct(model['dividend_yield']), 'EV-9M / EV-QUOTE')]
    body = section(text['facts'], _table([text['metric'], text['value'], text['source']], fact_rows) +
                   '<p>' + ref('EV-9M') + ' · ' + ref('EV-FY') + ' · ' + ref('EV-QUOTE') + '</p>')
    bridge_rows = []
    for key, label in [('ffo', 'FFO'), ('capex', text['capex']),
                       ('working_capital', text['wc']), ('lease_principal', text['lease']),
                       ('other_cash_reserve', text['other'])]:
        bridge_rows.append([label] + [fmt(doc['cases'][name][key]) for name in ('bear', 'base', 'bull')])
    bridge_rows.append([text['cash']] + [fmt(model['cases'][name]['starting_cash']) for name in ('bear', 'base', 'bull')])
    body += section(text['bridge'], _table([text['item'], text['bear'], text['base'], text['bull']], bridge_rows) +
                    paragraph(text['bridge_note']) + paragraph(text['cash_note']) +
                    '<p>' + ref('EV-9M') + ' · ' + ref('EV-FY') + '</p>')
    case_rows = []
    for name in ('bear', 'base', 'bull'):
        case, a = model['cases'][name], doc['cases'][name]
        case_rows.append([text[name], pct(a['growth']), pct(a['cost_of_equity']),
                          pct(a['terminal_growth']), fmt(case['per_share']), pct(case['price_gap'])])
    body += section(text['cases'], _table([text['item'], text['growth'], text['rate'],
                    text['terminal'], text['per_share'], text['gap']], case_rows) +
                    '<p class="formula">' + escape(text['method']) + '</p>' +
                    paragraph(text['terminal_note'].format(terminal=base['terminal_share'])) +
                    _table([text['period'], text['forecast']], [
                        [str(i), fmt(cash)] for i, cash in enumerate(base['cash_flows'], 1)]))
    body += section('Reverse DCF', paragraph(text['reverse_note'].format(
        growth=model['reverse_growth'], hurdle=model['zero_growth_cash_hurdle'])))
    body += section(text['sensitivity'], _table([text['rate'], 'gT 0%', 'gT 1%', 'gT 2%'], [
        [pct(row['cost_of_equity'])] + [fmt(value) for value in row['values']]
        for row in model['rate_sensitivity']]))
    body += section(text['funding'], _table([text['extra'], text['per_share']], [
        [fmt(row['extra_annual_cash_m']), fmt(row['per_share'])] for row in model['funding_sensitivity']]) +
        paragraph(text['funding_note']) + '<p>' + ref('EV-STRATEGY') + ' · ' + ref('EV-9M') + '</p>')
    body += section(text['risks'], '<ul>' + ''.join('<li>' + escape(text['risk' + str(i)]) +
                     '</li>' for i in range(1, 5)) + '</ul>')
    body += section(text['framework'], paragraph(text['framework_note']))
    body += section(text['triggers'], paragraph(text['triggers_note']))
    body += section(text['review'], paragraph(text['review_note']) +
                    '<p><a href="enagas-review.json">' + escape(text['downloads']) +
                    '</a> · <a href="enagas-inputs.json">' + escape(text['inputs']) + '</a></p>')
    sources = ''.join('<li id="' + escape(source['id']) + '"><a href="' +
        escape(source['url'], quote=True) + '" rel="noopener">' +
        escape(source['id'] + ' · ' + source['title']) + '</a><br><small>' +
        escape(source['published_date'] + ' · ' + source['locator']) + '</small></li>'
        for source in doc['sources'])
    body += section(text['sources'], '<ul>' + sources + '</ul>')
    return ('<!doctype html><html lang="' + language + '"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1"><title>' +
            escape(text['title']) + ' · InvestorAce</title><style>' + CSS + '</style></head><body><main>' +
            nav + hero + cards + body + '<footer><small>' + escape(text['confidence']) +
            '</small></footer></main></body></html>')


if __name__ == '__main__':
    main()
