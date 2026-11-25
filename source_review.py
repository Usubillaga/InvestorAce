"""Dated reviews, issuer facts and explicit monetary input conflicts.

Review prose/status never overrides scores. Typed input conflicts invalidate
the affected valuation inputs until a reviewed financial bridge replaces them.
"""
import copy
import json
import math
from datetime import date, datetime
from html import escape
from pathlib import Path
from urllib.parse import urlsplit

import equity_basis


VALUATION_STATUSES = {'SOURCE_CHECKED', 'PARTIAL', 'UNAVAILABLE', 'NOT_APPLICABLE'}
INSIDER_STATUSES = {'CHECKED_WITH_EVENTS', 'CHECKED_NO_EVENTS', 'PARTIAL',
                    'UNAVAILABLE', 'NOT_APPLICABLE'}
CATEGORIES = {'P': 'Purchase (open market or private)',
              'S': 'Sale (open market or private)', 'A': 'Award/grant',
              'M': 'Exercise/conversion', 'F': 'Tax/exercise withholding', 'G': 'Gift',
              'FCPE': 'Employee fund subscription', 'SALE': 'Disclosed sale',
              'SUBSCRIPTION': 'Employee subscription',
              'AMF_ACQUISITION_EMPLOYEE_FCPE_SUBSCRIPTION': 'Employee fund subscription',
              'AMF_DISPOSAL_SHARE_PLAN_ORIGIN': 'Sale of shares from a prior award plan'}


def empty():
    """Older model bundles had no review register; absence is not a completed check."""
    return dict(schema='source-reviews-v1', as_of=None, window_start=None,
                window_end=None, entries={})


def _date(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError('Review dates must be ISO calendar dates') from exc


def _url(value):
    try:
        parsed = urlsplit(value)
        valid = (parsed.scheme == 'https' and parsed.hostname and not parsed.username
                 and not parsed.password and parsed.port in (None, 443))
    except (TypeError, ValueError):
        valid = False
    if not valid:
        raise ValueError('Review source requires a valid HTTPS URL')


def valuation_input_conflicts(section, *, as_of):
    """Concrete input defects known at the cutoff, not generic pending review."""
    cutoff = as_of.date() if isinstance(as_of, datetime) else as_of
    return copy.deepcopy([item for item in section.get('input_conflicts', [])
                          if _date(item['detected_at']) <= cutoff])


def entry_dates(entry, reviews):
    """An aggregate register date must not refresh an individual issuer review.

    Old bundles retain their disclosed common transaction window. New entries
    may carry their own cutoff and window without changing the v1 envelope.
    """
    return (entry.get('window_start', reviews['window_start']),
            entry.get('window_end', reviews['window_end']),
            entry.get('as_of', entry.get('reviewed_at', reviews['as_of'])))


def _payment_amount(value):
    if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))
                              or not math.isfinite(value) or value < 0):
        raise ValueError('Payment amounts must be finite nonnegative numbers or unknown')


def _actual_payment(event, cutoff):
    dates = {event[k] for k in ('actual_payment_date', 'actual_paid_date') if event.get(k) is not None}
    status = event.get('status', event.get('payment_status'))
    if not dates:
        if status in ('PAID', 'PAYMENT_CONFIRMED'):
            raise ValueError('A confirmed payment requires its evidenced actual date')
        return
    if len(dates) != 1 or _date(dates.pop()) > cutoff:
        raise ValueError('Actual cash payment dates conflict or postdate the monitoring cutoff')
    if status != 'PAYMENT_CONFIRMED':
        raise ValueError('An actual payment date needs a confirmed payment')
    _url(event.get('payment_evidence_url'))


def _monitoring_payments(monitoring, cutoff):
    """A declared payable date is not evidence of an actual cash payment."""
    payment = monitoring.get('next_common_payment')
    if payment is not None:
        if not isinstance(payment, dict):
            raise ValueError('Next common payment must be an object or unknown')
        for name in ('declared_on', 'announced_on', 'published_on', 'record_date',
                     'ex_date', 'payable_date', 'actual_payment_date'):
            if payment.get(name) is not None:
                _date(payment[name])
        _actual_payment(payment, cutoff)
        _payment_amount(payment.get('amount'))
        if payment.get('currency') is not None and (
                not isinstance(payment['currency'], str) or not payment['currency'].strip()):
            raise ValueError('Payment currency must be nonempty text or unknown')
    recognized = {'preferred_cash_paid', 'common_cash_paid'}

    def check(value):
        if isinstance(value, dict):
            for name, amount in value.items():
                if name in recognized:
                    _payment_amount(amount)
                elif isinstance(amount, (dict, list)):
                    check(amount)
            if value.get('key') in recognized:
                _payment_amount(value.get('value'))
        elif isinstance(value, list):
            for item in value:
                check(item)

    check(monitoring.get('payments'))
    for event in monitoring.get('payment_events', []):
        _payment_amount(event.get('amount', event.get('amount_per_share')))
        if event.get('payable_date') is not None:
            _date(event['payable_date'])
        _actual_payment(event, cutoff)


def _calendar_checks(calendar, cutoff):
    if not calendar:
        return
    if _date(calendar['as_of']) > cutoff:
        raise ValueError('Calendar check postdates the register')
    for row in calendar['issuers'].values():
        urls = {s['url'] for s in row['sources']}
        if not urls:
            raise ValueError('Calendar checks require an inspected source')
        for url in urls:
            _url(url)
            if any(ch.isspace() for ch in url):
                raise ValueError('Calendar source URL contains whitespace')
        hint = row.get('provider_earnings')
        if hint:
            _url(calendar['provider_archive'])
            if hint.get('status') != 'UNCONFIRMED_BY_ISSUER' or _date(hint['date']) < _date(calendar['as_of']):
                raise ValueError('Invalid unconfirmed provider earnings date')
        for event in row['events']:
            if event.get('status') not in {'DECLARED_SCHEDULED', 'INDICATIVE_SCHEDULE', 'APPROVED_SCHEDULED',
                                           'PROPOSED', 'ISSUER_SCHEDULED', 'CONTRACTUAL_SCHEDULE'}:
                raise ValueError('Calendar event requires its announcement or schedule status')
            if event['source_url'] not in urls or not event.get('locator'):
                raise ValueError('Calendar event requires a checked source and locator')
            if event.get('date'):
                if _date(event['date']) < _date(calendar['as_of']):
                    raise ValueError('Historical event in forward calendar')
            else:
                date.fromisoformat(event['month'] + '-01')
            _payment_amount(event.get('amount'))
            _actual_payment(event, _date(calendar['as_of']))
            if any(event.get(k) is not None for k in ('actual_payment_date', 'actual_paid_date')):
                raise ValueError('A forward calendar does not establish a cash payment')


def load(payload=None):
    """Validate before publication; incomplete coverage cannot certify no activity."""
    if payload is None:
        payload = Path(__file__).with_name('source_reviews.json').read_text(encoding='utf-8')
    try:
        doc = json.loads(payload)
        # Reject NaN/Infinity even in optional metadata and return a detached object.
        doc = json.loads(json.dumps(doc, allow_nan=False))
        if doc['schema'] != 'source-reviews-v1' or not isinstance(doc['entries'], dict):
            raise ValueError('Invalid source review schema')
        start, end, asof = (_date(doc[k]) for k in ('window_start', 'window_end', 'as_of'))
        if not start <= end <= asof:
            raise ValueError('Invalid source review window')
        _calendar_checks(doc.get('calendar_checks'), asof)
        for ticker, entry in doc['entries'].items():
            if not isinstance(ticker, str) or not ticker or not entry['issuer'] or not entry['listing']:
                raise ValueError('Review requires an issuer and listing')
            entry_start, entry_end, entry_asof = map(_date, entry_dates(entry, doc))
            if not entry_start <= entry_end <= entry_asof <= asof:
                raise ValueError('Invalid issuer review window or cutoff')
            if entry.get('reviewed_at') is not None and _date(entry['reviewed_at']) > entry_asof:
                raise ValueError('Issuer check postdates its cutoff')
            monitoring = entry.get('monitoring')
            if monitoring is not None:
                if not isinstance(monitoring, dict):
                    raise ValueError('Issuer monitoring must be an object')
                mstart, mend, mcutoff = (_date(monitoring[k]) for k in
                                       ('window_start', 'window_end', 'as_of'))
                if not mstart <= mend <= mcutoff:
                    raise ValueError('Invalid issuer monitoring window')
                attempted = datetime.fromisoformat(monitoring['attempted_at'].replace('Z', '+00:00'))
                if attempted.utcoffset() is None or attempted.date() < mcutoff:
                    raise ValueError('Issuer monitoring needs a dated, timezone-aware attempt')
                if monitoring['coverage'] not in {'PARTIAL', 'UNAVAILABLE', 'PENDING', 'COMPLETE'}:
                    raise ValueError('Invalid issuer monitoring coverage')
                if not isinstance(monitoring['gap'], str) or not monitoring['gap'].strip():
                    raise ValueError('Issuer monitoring must explain its remaining gap or scope')
                if 'summary' in monitoring and not isinstance(monitoring['summary'], str):
                    raise ValueError('Issuer monitoring summary must be text')
                if not isinstance(monitoring['sources'], list):
                    raise ValueError('Issuer monitoring sources must be a list')
                for source in monitoring['sources']:
                    _url(source['url'])
                    if not source['title']:
                        raise ValueError('Issuer monitoring sources require titles')
                if monitoring.get('next_check_date') is not None:
                    if _date(monitoring['next_check_date']) < mcutoff:
                        raise ValueError('Issuer next monitoring check precedes its cutoff')
                _monitoring_payments(monitoring, mcutoff)
            for name, statuses in (('valuation', VALUATION_STATUSES), ('insider', INSIDER_STATUSES)):
                section = entry[name]
                if section['status'] not in statuses or not isinstance(section['reason'], str) or not section['reason'].strip():
                    raise ValueError('Review requires a supported status and concrete reason')
                if not isinstance(section['sources'], list):
                    raise ValueError('Review sources must be a list')
                if section.get('reviewed_at') is not None and _date(section['reviewed_at']) > entry_asof:
                    raise ValueError('Section check postdates its issuer cutoff')
                for source in section['sources']:
                    _url(source['url'])
                    if not source['title']:
                        raise ValueError('Review sources require a title')
            dcf = entry['valuation'].get('dcf')
            conflicts = entry['valuation'].get('input_conflicts', [])
            if not isinstance(conflicts, list):
                raise ValueError('Valuation input conflicts must be a list')
            codes = set()
            for conflict in conflicts:
                if (not isinstance(conflict, dict) or not isinstance(conflict.get('code'), str)
                        or not conflict['code'].strip() or conflict['code'] in codes
                        or not isinstance(conflict.get('reason'), str) or not conflict['reason'].strip()
                        or not entry['valuation']['sources']):
                    raise ValueError('Valuation input conflict requires unique code, reason and sources')
                if _date(conflict.get('detected_at')) > entry_asof:
                    raise ValueError('Valuation input conflict postdates the register')
                codes.add(conflict['code'])
            if dcf is not None:
                if _date(dcf['as_of']) > entry_asof:
                    raise ValueError('DCF review postdates the register')
                dcf_results(dcf)
            bridge = entry['valuation'].get('common_equity_bridge')
            if bridge is not None:
                if bridge.get('issuer_key') != ticker:
                    raise ValueError('Common-equity bridge belongs to another register issuer')
                _, fetched = equity_basis.validate(bridge, symbol=bridge.get('symbol'), currency=bridge.get('currency'))
                if fetched.date() > entry_asof:
                    raise ValueError('Common-equity bridge postdates the register')
            insider = entry['insider']
            for checked in (insider.get('reviewed_at'),
                            insider.get('coverage', {}).get('checked_through')):
                if checked is not None and _date(checked) > entry_asof:
                    raise ValueError('Insider check postdates the register')
            complete = insider.get('coverage', {}).get('complete') is True
            transactions = insider['transactions']
            if not isinstance(transactions, list) or not isinstance(insider['limitations'], list):
                raise ValueError('Review transactions and limitations must be lists')
            if insider['status'].startswith('CHECKED_'):
                if not complete or not insider['sources']:
                    raise ValueError('A checked window requires complete coverage and sources')
                if bool(transactions) != (insider['status'] == 'CHECKED_WITH_EVENTS'):
                    raise ValueError('Review activity status disagrees with its transactions')
            for transaction in transactions:
                _url(transaction['source_url'])
                if not entry_start <= _date(transaction['transaction_date']) <= entry_end:
                    raise ValueError('Transaction falls outside the disclosed review window')
                if _date(transaction['filing_date']) > entry_asof:
                    raise ValueError('Filing postdates the review')
                if not transaction['owner'] or not transaction['code']:
                    raise ValueError('Transaction requires an owner and a disclosed type')
                for field in ('shares', 'units', 'price'):
                    value = transaction.get(field)
                    if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))
                                              or not math.isfinite(value) or value < 0):
                        raise ValueError('Transaction quantities must be finite and nonnegative')
                if transaction.get('ten_b5_1') is not None and type(transaction['ten_b5_1']) is not bool:
                    raise ValueError('10b5-1 must be true, false or unknown')
        return doc
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError('Malformed source review register') from exc


def insider_cell(ticker, reviews):
    entry = reviews['entries'].get(ticker)
    if entry is None:
        return '<span class="pill empty">NOT REVIEWED</span>'
    insider = entry['insider']
    checked = (insider.get('reviewed_at') or insider.get('coverage', {}).get('checked_through')
               or entry.get('reviewed_at') or entry.get('as_of')
               or reviews.get('window_end') or reviews['as_of'])
    status = insider['status'].replace('_', ' ')
    return (f'<a class="pill x-appr" href="#review-{escape(ticker)}">{escape(status)}</a>'
            f'<br><small>as of {escape(checked)}</small>')



def dcf_results(note):
    """Reproduce a conditional review, independently of NGV, scores and live prices."""
    def number(section, key, minimum=None, maximum=None):
        value = section[key]
        if (isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or (minimum is not None and value < minimum)
                or (maximum is not None and value > maximum)):
            raise ValueError('DCF inputs must be finite numbers within their economic bounds')
        return value

    try:
        if (note['schema'] != 'equity-dcf-review-v1' or note['status'] != 'CONDITIONAL'
                or note['currency'] != 'USD'
                or note['cash_flow_basis'] != 'NORMALIZED_FCFF_PROXY'):
            raise ValueError('Unsupported conditional DCF review')
        asof = _date(note['as_of'])
        capital, quote = note['capital_bridge'], note['reference_quote']
        if _date(capital['as_of']) > asof or not capital['shares_basis'].strip():
            raise ValueError('DCF capital bridge needs a dated share basis')
        timestamp = datetime.fromisoformat(quote['as_of'].replace('Z', '+00:00'))
        if (timestamp.utcoffset() is None or timestamp.date() > asof
                or quote['purpose'] != 'DATED_REFERENCE_NOT_LIVE'):
            raise ValueError('DCF requires a dated reference quote at or before the review')
        _url(quote['source_url'])
        price = number(quote, 'price', 0)
        shares = number(capital, 'diluted_shares', 0)
        if price == 0 or shares == 0:
            raise ValueError('DCF quote and share denominator must be positive')
        n = note['normalization']
        reported = number(n, 'reported_fy_fcf', 0)
        low, high = (number(n, k, -.99) for k in
                     ('guided_fcf_growth_low', 'guided_fcf_growth_high'))
        if reported == 0 or high < low:
            raise ValueError('DCF requires positive starting FCF and ordered guidance')
        tax = number(n, 'tax_rate', 0, 1)
        if tax == 1:
            raise ValueError('DCF tax assumption must be below 100%')
        guided_fcf = reported * (1 + (low + high) / 2)
        sbc = number(n, 'guided_revenue', 0) * number(n, 'sbc_share', 0, 1)
        interest = number(n, 'quarterly_interest', 0) * 4 * (1 - tax)
        other_income = number(n, 'half_year_other_income') * 2 * (1 - tax)
        financing_principal = number(n, 'half_year_financing_principal', 0) * 2
        starting_fcff = guided_fcf - sbc + interest - other_income - financing_principal
        if not math.isfinite(starting_fcff) or starting_fcff <= 0:
            raise ValueError('This DCF requires a positive finite normalized FCFF proxy')
        cash = number(capital, 'cash', 0)
        securities = number(capital, 'marketable_securities', 0)
        debt = number(capital, 'financial_debt', 0)
        investments = (number(capital, 'strategic_investments', 0)
                       * number(capital, 'strategic_value_fraction', 0, 1))
        number(note['braze'], 'enterprise_value', 0)
        deal_npv = number(note['braze'], 'assumed_incremental_npv')
        bridge = cash + securities + investments - debt + deal_npv

        def value(first, second, rate, terminal):
            if (not all(math.isfinite(v) for v in (first, second, rate, terminal))
                    or min(first, second, terminal) <= -1 or not 0 < rate < 1
                    or terminal >= rate):
                raise ValueError('DCF growth and discount rates are inconsistent')
            cash_flow, present_cash = starting_fcff, 0
            for year in range(1, 11):
                cash_flow *= 1 + (first if year <= 5 else second)
                present_cash += cash_flow / (1 + rate) ** year
            present_terminal = cash_flow * (1 + terminal) / (rate - terminal) / (1 + rate) ** 10
            enterprise = present_cash + present_terminal
            result = dict(enterprise_value=enterprise, equity_value=enterprise + bridge,
                          value_per_share=(enterprise + bridge) / shares,
                          terminal_share=present_terminal / enterprise, year10_fcff=cash_flow)
            if not all(math.isfinite(v) for v in result.values()):
                raise ValueError('DCF outputs must be finite')
            return result

        scenarios = {}
        for case in ('downside', 'base', 'upside'):
            s = note['scenarios'][case]
            scenarios[case] = value(*(number(s, k) for k in
                                     ('growth_first5', 'growth_second5',
                                      'discount_rate', 'terminal_growth')))
        reverse = []
        rates = note['reverse']['discount_rates']
        if not isinstance(rates, list) or not 1 <= len(rates) <= 9:
            raise ValueError('Reverse DCF requires one to nine discount rates')
        terminal = number(note['reverse'], 'terminal_growth')
        for raw_rate in rates:
            rate = number({'rate': raw_rate}, 'rate')
            lower, upper = -.5, .5
            if not (value(lower, lower, rate, terminal)['value_per_share'] <= price
                    <= value(upper, upper, rate, terminal)['value_per_share']):
                raise ValueError('Reference price is outside the reverse DCF search range')
            for _ in range(90):
                growth = (lower + upper) / 2
                if value(growth, growth, rate, terminal)['value_per_share'] < price:
                    lower = growth
                else:
                    upper = growth
            growth = (lower + upper) / 2
            solved = value(growth, growth, rate, terminal)
            reverse.append(dict(discount_rate=rate, growth=growth,
                                reproduced_price=solved['value_per_share'],
                                year10_fcff=solved['year10_fcff']))
        return dict(guided_fcf=guided_fcf, sbc=sbc, interest=interest,
                    other_income=other_income, financing_principal=financing_principal,
                    starting_fcff=starting_fcff, capital_bridge=bridge,
                    recognized_investments=investments, scenarios=scenarios, reverse=reverse)
    except (KeyError, TypeError, AttributeError, OverflowError, ZeroDivisionError) as exc:
        raise ValueError('Malformed conditional DCF review') from exc


def dcf_badge(ticker, reviews):
    note = reviews['entries'].get(ticker, {}).get('valuation', {}).get('dcf')
    if note is None:
        return ''
    base = dcf_results(note)['scenarios']['base']['value_per_share']
    return (f'<br><a class="pill x-appr" href="#dcf-{escape(ticker)}" '
            f'title="Conditional DCF; {escape(note["as_of"])}; dated reference">'
            f'DCF {base:,.0f} USD*</a>')


def dcf_panel(ticker, note):
    """Render the archived inputs and all three site languages without model mutation."""
    if note is None:
        return ''
    result = dcf_results(note)
    n, capital, quote = note['normalization'], note['capital_bridge'], note['reference_quote']
    copy = {
        'en': {
            'title': 'Conditional DCF / reverse DCF',
            'quote': 'Dated reference: {price:.2f} USD at {date}; not a live quote. The reference predates the Braze announcement.',
            'method': 'Ten future 12-month periods; growth starts in year 1; year-end discounting and terminal value at year 10. This normalized FCFF proxy is an analyst assumption, not issuer-reported FCFF or a complete GAAP forecast. Values are conditional scenarios, not a verified current fair value or a buy signal.',
            'headers': ['Scenario', 'FCFF growth years 1–5 / 6–10', 'WACC', 'Terminal growth', 'USD / share', 'Terminal share of EV'],
            'cases': ['Downside', 'Base', 'Upside'],
            'reverse': 'Reverse DCF: constant ten-year cash-flow growth at the dated reference',
            'reverse_headers': ['WACC', 'Implied FCFF CAGR', 'Reproduced USD / share'],
            'terminal': 'Reverse DCF terminal growth',
            'details': 'Cash-flow normalization and equity bridge (USD million; shares in millions)',
            'bridge_headers': ['Input / adjustment', 'Amount'],
            'rows': ['FY26 reported FCF', 'FY27 FCF growth guidance midpoint', 'FY27 guided FCF proxy',
                     'FY27 revenue midpoint', 'SBC cost: revenue × assumed share', 'After-tax interest addback: quarterly × 4',
                     'Other-income proxy deducted: half-year × 2 after tax',
                     'Replacement cash cost: financing principal, half-year × 2', 'Starting normalized FCFF proxy',
                     'Cash', 'Marketable securities', 'Recognized strategic investments', 'Financial debt principal deducted',
                     'Assumed incremental Braze NPV', 'Total equity bridge', 'Model share denominator'],
            'limits': 'The full SBC cost is deducted with a fixed share count; no second dilution penalty is applied. The 827m denominator is a Q3 FY27 guided diluted weighted-average proxy, not a verified current diluted spot count. Capital balances are from {balance}. Cash, debt, Fin/Contentful acquisitions, the final ASR and the share roll-forward remain unresolved. Other income is an uncertain proxy for nonoperating cash income; finance-lease interest in the total interest addback is an unquantified approximation. Lease liabilities are not deducted again under this cash-cost convention. Strategic investments are recognized at an assumed {fraction:.0%} of carrying value. Tax assumption: {tax:.1%}.',
            'deal': 'Braze announced EV: {ev:,.0f} million USD. Incremental deal NPV is assumed to be {npv:,.0f} million USD, not established by the analysis. Acquired value and funding must be counted together; the full purchase price is not deducted by itself. Each 1,000 million USD of incremental NPV changes value by {delta:.2f} USD/share. FCFF growth is not revenue or cRPO growth. Score, NGV and Regime Fit remain separate from this DCF.',
        },
        'de': {
            'title': 'Vorläufig: DCF / Reverse DCF',
            'quote': 'Datierter Referenzkurs: {price:.2f} USD am {date}; kein Livekurs. Der Kurs stammt aus der Zeit vor der Braze-Ankündigung.',
            'method': 'Zehn künftige Zwölfmonatsperioden; Wachstum ab Jahr 1, Abzinsung zum Jahresende und Terminalwert nach Jahr 10. Der normalisierte FCFF-Proxy ist eine Analystenannahme, kein vom Unternehmen berichteter FCFF und keine vollständige GAAP-Prognose. Die Werte sind bedingte Szenarien, kein bestätigter aktueller Fair Value und kein Kaufsignal.',
            'headers': ['Szenario', 'FCFF-Wachstum Jahre 1–5 / 6–10', 'WACC', 'Terminalwachstum', 'USD / Aktie', 'Terminalanteil am EV'],
            'cases': ['Negativ', 'Basis', 'Positiv'],
            'reverse': 'Reverse DCF: konstantes zehnjähriges Cashflow-Wachstum beim datierten Referenzkurs',
            'reverse_headers': ['WACC', 'Implizite FCFF-Wachstumsrate', 'Reproduzierter USD-Kurs'],
            'terminal': 'Terminalwachstum im Reverse DCF',
            'details': 'Cashflow-Normalisierung und Eigenkapitalbrücke (Mio. USD; Aktien in Mio.)',
            'bridge_headers': ['Eingangswert / Anpassung', 'Betrag'],
            'rows': ['Berichteter FCF GJ26', 'Mitte der FCF-Wachstumsprognose GJ27', 'FCF-Proxy GJ27 aus Prognose',
                     'Umsatzprognose GJ27: Mittelpunkt', 'SBC-Kosten: Umsatz × angenommener Anteil',
                     'Zinskorrektur nach Steuern: Quartal × 4', 'Abzug übriger Ertragsproxy: Halbjahr × 2 nach Steuern',
                     'Ersatz-Cashkosten: Finanzierungstilgung, Halbjahr × 2', 'Normalisierter FCFF-Startwert',
                     'Barmittel', 'Marktgängige Wertpapiere', 'Angesetzte strategische Beteiligungen',
                     'Abzug Finanzschulden: Nennbetrag', 'Angenommener zusätzlicher Braze-NPV',
                     'Gesamte Eigenkapitalbrücke', 'Aktienzahl im Modell'],
            'limits': 'SBC wird vollständig als Kosten abgezogen; die Aktienzahl bleibt konstant und erhält keinen zweiten Verwässerungsabschlag. 827 Mio. Aktien sind ein Proxy aus der Prognose der verwässerten gewichteten Durchschnittsaktien für Q3 GJ27, keine bestätigte aktuelle Aktienzahl. Die Bilanzwerte stammen vom {balance}. Aktuelle Barmittel, Schulden, Fin/Contentful-Zukäufe, endgültiger ASR und die Aktienfortschreibung bleiben offen. Übrige Erträge sind ein unsicherer Proxy für nichtoperative Cash-Erträge; Finanzierungsleasing-Zinsen in der gesamten Zinskorrektur sind eine nicht quantifizierte Näherung. Leasingverbindlichkeiten werden unter dieser Cashkosten-Konvention nicht nochmals abgezogen. Strategische Beteiligungen werden mit angenommenen {fraction:.0%} des Buchwerts angesetzt. Steuerannahme: {tax:.1%}.',
            'deal': 'Angekündigter Braze-EV: {ev:,.0f} Mio. USD. Der zusätzliche Transaktions-NPV wird mit {npv:,.0f} Mio. USD angenommen; die Analyse bestätigt diesen Wert nicht. Erworbener Wert und Finanzierung müssen gemeinsam erfasst werden; der volle Kaufpreis wird nicht isoliert abgezogen. Je 1.000 Mio. USD zusätzlicher NPV verändert sich der Wert um {delta:.2f} USD/Aktie. FCFF-Wachstum ist kein Umsatz- oder cRPO-Wachstum. Score, NGV und Regime Fit bleiben eigenständig.',
        },
        'es': {
            'title': 'Condicional: DCF / DCF inverso',
            'quote': 'Cotización de referencia: {price:.2f} USD a {date}; no es una cotización en tiempo real. La referencia es anterior al anuncio de Braze.',
            'method': 'Diez períodos futuros de doce meses; crecimiento desde el año 1, descuento al cierre anual y valor terminal al final del año 10. Este proxy de FCFF normalizado es una hipótesis del analista, no FCFF publicado por la empresa ni una previsión GAAP completa. Son escenarios condicionales, no un valor razonable actual verificado ni una señal de compra.',
            'headers': ['Escenario', 'Crecimiento FCFF años 1–5 / 6–10', 'WACC', 'Crecimiento terminal', 'USD / acción', 'Peso terminal en EV'],
            'cases': ['Bajista', 'Base', 'Alcista'],
            'reverse': 'DCF inverso: crecimiento constante del flujo de caja durante diez años a la cotización de referencia',
            'reverse_headers': ['WACC', 'CAGR implícita del FCFF', 'Precio reproducido USD / acción'],
            'terminal': 'Crecimiento terminal del DCF inverso',
            'details': 'Normalización del flujo de caja y puente al patrimonio (millones USD; acciones en millones)',
            'bridge_headers': ['Dato / ajuste', 'Importe'],
            'rows': ['FCF publicado AF26', 'Punto medio del crecimiento previsto del FCF AF27', 'Proxy del FCF AF27 previsto',
                     'Punto medio de ingresos previstos AF27', 'Coste SBC: ingresos × proporción supuesta',
                     'Ajuste de intereses tras impuestos: trimestre × 4', 'Deducción del proxy de otros ingresos: semestre × 2 tras impuestos',
                     'Coste de caja sustitutivo: principal de financiación, semestre × 2', 'Proxy inicial de FCFF normalizado',
                     'Efectivo', 'Valores negociables', 'Inversiones estratégicas reconocidas',
                     'Deducción del principal de deuda financiera', 'VPN incremental supuesto de Braze',
                     'Puente total al patrimonio', 'Número de acciones del modelo'],
            'limits': 'Se deduce todo el coste SBC con un número fijo de acciones, sin una segunda penalización por dilución. Las 827 millones de acciones son un proxy del promedio ponderado diluido previsto para T3 AF27, no una cifra actual verificada. Los saldos son del {balance}. Siguen pendientes efectivo, deuda, compras de Fin/Contentful, ASR final y evolución del número de acciones. Otros ingresos son un proxy incierto de ingresos de caja no operativos; los intereses de arrendamientos financieros incluidos en el ajuste total son una aproximación no cuantificada. No se deducen otra vez los pasivos por arrendamientos bajo esta convención de costes de caja. Las inversiones estratégicas se reconocen al {fraction:.0%} supuesto de su valor contable. Impuesto supuesto: {tax:.1%}.',
            'deal': 'EV anunciado de Braze: {ev:,.0f} millones USD. El VPN incremental se supone en {npv:,.0f} millones USD; el análisis no demuestra ese valor. El valor adquirido y la financiación se deben contar juntos; no se deduce aisladamente todo el precio. Cada 1.000 millones USD de VPN incremental cambia el valor en {delta:.2f} USD/acción. El crecimiento del FCFF no es crecimiento de ingresos o cRPO. Score, NGV y Regime Fit siguen siendo medidas separadas.',
        },
    }

    def table(headers, rows):
        return ('<div class="tw"><table><thead><tr>'
                + ''.join('<th>' + escape(h) + '</th>' for h in headers)
                + '</tr></thead><tbody>'
                + ''.join('<tr>' + ''.join('<td>' + escape(str(cell)) + '</td>' for cell in row)
                          + '</tr>' for row in rows) + '</tbody></table></div>')

    blocks = []
    for language, text in copy.items():
        scenarios = []
        for case, label in zip(('downside', 'base', 'upside'), text['cases']):
            s, r = note['scenarios'][case], result['scenarios'][case]
            scenarios.append([label, f'{s["growth_first5"]:.1%} / {s["growth_second5"]:.1%}',
                              f'{s["discount_rate"]:.1%}', f'{s["terminal_growth"]:.1%}',
                              f'{r["value_per_share"]:,.2f}', f'{r["terminal_share"]:.1%}'])
        reverse = [[f'{r["discount_rate"]:.1%}', f'{r["growth"]:.2%}',
                    f'{r["reproduced_price"]:,.2f}'] for r in result['reverse']]
        values = [n['reported_fy_fcf'], (n['guided_fcf_growth_low'] + n['guided_fcf_growth_high']) / 2,
                  result['guided_fcf'], n['guided_revenue'], -result['sbc'], result['interest'],
                  -result['other_income'], -result['financing_principal'], result['starting_fcff'],
                  capital['cash'], capital['marketable_securities'], result['recognized_investments'],
                  -capital['financial_debt'], note['braze']['assumed_incremental_npv'],
                  result['capital_bridge'], capital['diluted_shares']]
        bridge_rows = [[label, f'{v:.1%}' if i == 1 else f'{v:,.3f}']
                       for i, (label, v) in enumerate(zip(text['rows'], values))]
        quote_text = text['quote'].format(price=quote['price'], date=quote['as_of'])
        limits = text['limits'].format(balance=capital['as_of'],
                                      fraction=capital['strategic_value_fraction'], tax=n['tax_rate'])
        deal = text['deal'].format(ev=note['braze']['enterprise_value'],
                                  npv=note['braze']['assumed_incremental_npv'],
                                  delta=1000 / capital['diluted_shares'])
        blocks.append(f'<div class="dcf-language dcf-{language}" lang="{language}">'
                      + '<h4>' + escape(text['title']) + ' · ' + escape(note['as_of']) + '</h4>'
                      + '<p>' + escape(quote_text) + '</p><p>' + escape(text['method']) + '</p>'
                      + table(text['headers'], scenarios)
                      + '<h4>' + escape(text['reverse']) + '</h4><p>'
                      + escape(text['terminal']) + f': {note["reverse"]["terminal_growth"]:.1%}</p>'
                      + table(text['reverse_headers'], reverse)
                      + '<details><summary>' + escape(text['details']) + '</summary>'
                      + table(text['bridge_headers'], bridge_rows) + '</details>'
                      + '<p>' + escape(limits) + '</p><p>' + escape(deal) + '</p></div>')
    return (f'<section class="dcf-review" id="dcf-{escape(ticker)}">'
            '<style>.dcf-language{display:none}.dcf-en{display:block}'
            'html[lang="de"] .dcf-en,html[lang="es"] .dcf-en{display:none}'
            'html[lang="de"] .dcf-de,html[lang="es"] .dcf-es{display:block}</style>'
            + ''.join(blocks) + '</section>')


def _sources(sources):
    return ' &middot; '.join(f'<a href="{escape(s["url"], quote=True)}" target="_blank" '
                             f'rel="noopener">{escape(s["title"])}</a>' for s in sources)


def _payment_list(monitoring):
    events = list(monitoring.get('payment_events', []))
    if monitoring.get('next_common_payment'):
        events.append(monitoring['next_common_payment'])
    facts = {}
    for event in events:
        actual = event.get('actual_payment_date') or event.get('actual_paid_date')
        day = actual or event.get('payable_date')
        if not day:
            continue
        kind = event.get('security') or event.get('event_type') or event.get('kind') or 'common'
        kind = kind.lower().replace('_dividend', '').replace('_', ' ')
        amount = event.get('amount', event.get('amount_per_share'))
        currency = event.get('currency') or ''
        status = 'Payment confirmed' if actual else 'Scheduled payable date'
        instrument = ' '.join(filter(None, (event.get('issuer'), kind)))
        value = '' if amount is None else f' · {amount:g} {currency}'
        key = (day, status, instrument, amount, currency)
        item = escape(f'{status} · {day} · {instrument}{value}')
        if actual:
            item += ' · ' + _sources([dict(url=event['payment_evidence_url'], title='Payment evidence')])
        facts.setdefault(key, item)
    if not facts:
        return ''
    return '<ul>' + ''.join('<li>' + item + '</li>' for item in facts.values()) + '</ul>'


def panel(rows, reviews):
    entries = {t: e for t, e in reviews['entries'].items() if t in rows}
    intro = (f'{len(entries)} of {len(rows)} tickers have a dated review entry; '
             f'{len(rows) - len(entries)} not reviewed. Source inspection and a validated '
             'sustainable valuation are separate checks. Dated issuer facts can correct model inputs; review narrative does not override formulas or approval.')
    if not reviews['as_of']:
        return '<section class="box"><h2>Source and insider review</h2><p>' + intro + '</p></section>'
    body = []
    for ticker, entry in sorted(entries.items()):
        valuation, insider = entry['valuation'], entry['insider']
        start, end, cutoff = entry_dates(entry, reviews)
        valuation_checked = valuation.get('reviewed_at') or entry.get('reviewed_at') or entry.get('as_of')
        valuation_date = (f'Source check {escape(valuation_checked)}.' if valuation_checked
                          else 'Individual valuation check date not recorded; read the dated sources.')
        monitoring = entry.get('monitoring')
        monitoring_html = ''
        if monitoring is not None:
            monitoring_html = (f'<p><b>Event/payment monitoring: {escape(monitoring["coverage"])}</b><br>'
                               f'As of {escape(monitoring["as_of"])}; attempted '
                               f'{escape(monitoring["attempted_at"])}. Window '
                               f'{escape(monitoring["window_start"])} to {escape(monitoring["window_end"])}. '
                               'This attempt does not refresh the valuation or insider checks above. '
                               f'Next check: {escape(monitoring.get("next_check_date") or "UNKNOWN")}. '
                               + escape(monitoring['gap']) + '</p><p>'
                               + escape(monitoring.get('summary', '')) + '</p><p>'
                               + _sources(monitoring['sources']) + '</p>' + _payment_list(monitoring))
        events = []
        for tx in insider['transactions']:
            code = tx['code']
            category = CATEGORIES.get(code, 'Other disclosed transaction')
            plan = {True: 'yes', False: 'no', None: 'unknown'}[tx.get('ten_b5_1')]
            amount = tx.get('shares') if tx.get('shares') is not None else tx.get('units')
            quantity = '&mdash;' if amount is None else f'{amount:,.4f}'.rstrip('0').rstrip('.')
            quantity += '<br>' + escape(tx.get('unit_type') or tx.get('security_title') or tx.get('security') or '')
            price = '&mdash;' if tx.get('price') is None else f'{tx["price"]:,.4f}'.rstrip('0').rstrip('.')
            events.append('<tr>' + ''.join('<td>' + cell + '</td>' for cell in (
                escape(tx['transaction_date']), escape(tx['filing_date']),
                escape(tx['owner']) + '<br>' + escape(tx.get('role') or ''),
                escape(category) + ' [' + escape(code) + ']', quantity,
                price + ' ' + escape(tx.get('currency') or ''),
                escape(tx.get('ownership') or 'UNKNOWN') + '<br>10b5-1: ' + plan,
                f'<a href="{escape(tx["source_url"], quote=True)}" target="_blank" rel="noopener">Filing</a>'
                + '<br>' + escape(tx.get('note') or ''))) + '</tr>')
        table = ''
        if events:
            table = ('<div class="tw"><table><thead><tr><th>Transaction</th><th>Filed</th>'
                     '<th>Owner / role</th><th>Disclosed type</th><th>Quantity</th><th>Price / currency</th>'
                     '<th>Ownership / plan</th><th>Source / note</th></tr></thead><tbody>'
                     + ''.join(events) + '</tbody></table></div>')
        elif insider['status'] == 'CHECKED_NO_EVENTS':
            table = '<p>No transactions reported in the checked public register for this window.</p>'
        limits = ' '.join(insider['limitations'])
        opened = ' open' if valuation.get('dcf') is not None else ''
        body.append(f'<details id="review-{escape(ticker)}"{opened}><summary>{escape(ticker)} &middot; '
                    f'{escape(entry["issuer"])} &middot; {escape(insider["status"])}</summary>'
                    f'<p>{valuation_date} Insider window {escape(start)} to {escape(end)}; '
                    f'entry cutoff {escape(cutoff)}. These dates are not a fresh review of later events.</p>'
                    f'<p><b>Valuation source check: {escape(valuation["status"])}</b><br>'
                    + escape(valuation['reason']) + '</p><p>' + _sources(valuation['sources']) + '</p>'
                    + dcf_panel(ticker, valuation.get('dcf'))
                    + f'<p><b>Insider coverage: {escape(insider["status"])}</b><br>'
                    + escape(insider['reason']) + '</p><p>' + escape(limits) + '</p><p>'
                    + _sources(insider['sources']) + '</p>' + table + monitoring_html + '</details>')
    calendar = reviews.get('calendar_checks') or {}
    calendar_rows = []
    for ticker, row in sorted(calendar.get('issuers', {}).items()):
        if ticker not in rows:
            continue
        events = []
        for event in row['events']:
            amount = '' if event.get('amount') is None else f' · {event["amount"]:g} {event["currency"]}'
            label = ' · '.join((event.get('date') or event['month'], event['kind'].replace('_', ' '),
                                event['status'].replace('_', ' ').lower()))
            events.append(escape(label + amount))
        if row.get('provider_earnings'):
            hint = row['provider_earnings']
            archive = escape(calendar['provider_archive'], quote=True)
            events.append(escape(hint['date']) + f' · earnings · <a href="{archive}">provider date</a>, '
                          'awaiting issuer confirmation')
        calendar_rows.append('<tr><td>' + escape(ticker) + '</td><td>'
                             + ('<br>'.join(events) or 'Next date unconfirmed')
                             + '</td><td>' + _sources(row['sources']) + '</td></tr>')
    calendar_html = ''
    if calendar_rows:
        calendar_html = ('<details><summary>Additional issuer and fund calendars · ' + escape(calendar['as_of'])
                         + '</summary><p>A payable date is a scheduled event. An unknown date can still '
                           'be announced later.</p><div class="tw"><table><thead><tr><th>Listing</th>'
                           '<th>Announced events</th><th>Sources checked</th></tr></thead><tbody>'
                         + ''.join(calendar_rows) + '</tbody></table></div></details>')
    return ('<section class="box"><h2>Source and insider review</h2><p>' + intro + '</p>'
            f'<p>Register assembled as of {escape(reviews["as_of"])}; '
            'individual review dates and transaction windows are shown per issuer. '
            'P/S codes include open market or private transactions; awards, exercises, '
            'withholding, gifts and employee fund subscriptions are shown separately. '
            'Quantities can refer to different security or fund-unit types; read each filing. '
            'Unknown or incomplete coverage is not evidence of no activity. No motive is inferred.</p>'
            + calendar_html + ''.join(body) + '</section>')
