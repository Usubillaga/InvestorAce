"""Period-bound common-equity bridges, separate from reported financial facts.

Cash preferred dividends, earnings deductions and capital redemptions are
different measures. A bridge is still a historical proxy, not normalized FCFE.
"""
import copy
from datetime import date
from urllib.parse import urlsplit

import assessment
from integrity import finite_number


SCHEMA = 'common-equity-bridge-v1'
SCOPES = {'REPORTED', 'CONSOLIDATED', 'CONTINUING', 'UNRESOLVED'}
MONEY_FIELDS = ('operating_cash_flow', 'capex', 'net_income', 'net_income_common',
                'preferred_cash_paid', 'preferred_earnings_deduction', 'revenue',
                'preferred_outstanding', 'common_dividends_paid', 'dividends_total',
                'capex_reported', 'capital_accrual_change', 'net_income_before_noncontrolling',
                'noncontrolling_earnings', 'reported_fcf')
RESOLVABLE = {'DISPOSED_BUSINESS_IN_CYCLE_PROXY', 'COMMON_EQUITY_CLAIMS_OMITTED'}


def validate(bridge, *, symbol, currency):
    """Reject malformed authoritative amounts rather than silently using Yahoo."""
    if (not isinstance(bridge, dict) or bridge.get('schema') != SCHEMA
            or not isinstance(symbol, str) or not symbol
            or not isinstance(currency, str) or len(currency) != 3
            or not isinstance(bridge.get('issuer_key'), str) or not bridge['issuer_key']
            or bridge.get('symbol') != symbol or bridge.get('currency') != currency
            or bridge.get('units') != 'currency_units'
            or bridge.get('required_scope') not in SCOPES - {'UNRESOLVED'}
            or type(bridge.get('preferred_claims_required')) is not bool):
        raise ValueError('Invalid common-equity bridge identity/currency/scope')
    published, fetched = (assessment.timestamp(bridge.get(k)) for k in ('published_at', 'fetched_at'))
    if published is None or fetched is None or fetched < published:
        raise ValueError('Invalid common-equity bridge publication/retrieval dates')
    urls = bridge.get('source_urls')
    if not isinstance(urls, list) or not urls:
        raise ValueError('Common-equity bridge requires primary sources')
    for url in urls:
        parsed = urlsplit(url)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError('Invalid common-equity bridge source URL')
    if not isinstance(bridge.get('periods'), list) or not bridge['periods']:
        raise ValueError('Common-equity bridge requires period rows')
    seen = set()
    for row in bridge['periods']:
        period = date.fromisoformat(row['period'])
        key = (row['period'], row.get('basis'))
        if (key in seen or key[1] not in ('FY', 'TTM') or period > published.date()
                or row.get('scope') not in SCOPES or not row.get('source_urls')
                or not set(row['source_urls']).issubset(urls)):
            raise ValueError('Invalid or duplicate common-equity period/scope/source')
        for field in MONEY_FIELDS:
            if row.get(field) is not None and finite_number(row[field]) is None:
                raise ValueError('Non-finite common-equity bridge amount: ' + field)
        if 'preferred_claims_known' in row and type(row['preferred_claims_known']) is not bool:
            raise ValueError('Preferred-claim disclosure must be boolean')
        parent, common, deduction = (finite_number(row.get(k)) for k in
                                      ('net_income', 'net_income_common', 'preferred_earnings_deduction'))
        if None not in (parent, common, deduction) and abs(parent-deduction-common) > 1.:
            raise ValueError('Primary common-income bridge does not reconcile')
        total, nci = (finite_number(row.get(k)) for k in ('net_income_before_noncontrolling', 'noncontrolling_earnings'))
        if None not in (total, nci, parent) and abs(total-nci-parent) > 1.:
            raise ValueError('Primary noncontrolling-income bridge does not reconcile')
        capex = finite_number(row.get('capex'))
        if capex is not None and capex < 0:
            raise ValueError('Primary cash capex must be nonnegative')
        reported, change = (finite_number(row.get(k)) for k in ('capex_reported', 'capital_accrual_change'))
        if None not in (capex, reported, change) and abs(reported-change-capex) > 1.:
            raise ValueError('Primary cash-capex accrual bridge does not reconcile')
        seen.add(key)
    return published, fetched


def _known(row):
    return bool(row.get('preferred_claims_known') or any(
        finite_number(row.get(k)) not in (None, 0.) for k in
        ('preferred_cash_paid', 'preferred_earnings_deduction', 'preferred_outstanding')))


def _normalise(row, *, required_scope=None, preferred_required=False):
    result = copy.deepcopy(row)
    for field in MONEY_FIELDS:
        result.setdefault(field, None)
    scope = row.get('scope', 'REPORTED')
    matched = scope != 'UNRESOLVED' and (required_scope is None or scope == required_scope)
    known = preferred_required or _known(row)
    ocf, capex, paid, deduction, common = (finite_number(row.get(k)) for k in
        ('operating_cash_flow', 'capex', 'preferred_cash_paid', 'preferred_earnings_deduction', 'net_income_common'))
    before = ocf-abs(capex) if matched and ocf is not None and capex is not None else None
    if before is None and matched and scope == 'REPORTED' and not known:
        before = finite_number(row.get('reported_fcf'))
    # Missing payments never become zero when a preferred obligation is known.
    fcf = before-abs(paid) if before is not None and paid is not None else before if not known else None
    earnings = finite_number(row.get('net_income'))
    method = 'ALREADY_COMMON' if common is not None else 'REPORTED_PARENT_EARNINGS'
    if common is None:
        common = (earnings-deduction if earnings is not None and deduction is not None
                  else earnings if not known else None)
        if deduction is not None:
            method = 'PARENT_LESS_PREFERRED_EARNINGS_DEDUCTION'
    if not matched or row.get('earnings_scope', scope) != scope:
        common = None
    dividend = finite_number(row.get('common_dividends_paid'))
    total = finite_number(row.get('dividends_total'))
    if dividend is None and total is not None:
        dividend = (abs(total)-abs(paid) if paid is not None and abs(total) >= abs(paid)
                    else abs(total) if not known else None)
    result.update(common_fcf=fcf, fcf_before_preferred=before, common_net_income=common,
                  comparable_revenue=row.get('revenue') if matched and row.get('revenue_scope', scope) == scope else None,
                  common_dividends_paid=dividend, preferred_claims_known=known,
                  scope_matched=matched, earnings_method=method,
                  adjustment_reason='Matched cash scope; paid preferred cash and earnings deductions applied separately.'
                    if matched else 'Cash/earnings scope does not match the required operating perimeter.')
    return result


def apply(facts, *, as_of):
    """Derive adjusted inputs without rewriting the provider packet or its cache."""
    rows = copy.deepcopy(facts.get('equity_periods') or [])
    bridge = facts.get('common_equity_bridge')
    scope, preferred_required = None, bool(facts.get('preferred_claims_required'))
    primary = None
    if bridge:
        published, fetched = validate(bridge, symbol=facts.get('symbol'),
                                      currency=facts.get('financial_currency') or bridge.get('currency'))
        if published <= fetched <= as_of:
            primary = bridge
            scope, preferred_required = bridge['required_scope'], bridge['preferred_claims_required']
            keyed = {(r['period'], r['basis']): r for r in rows}
            keyed.update({(r['period'], r['basis']): copy.deepcopy(r) for r in bridge['periods']})
            rows = list(keyed.values())
    if not rows and not preferred_required:
        return facts
    result = copy.deepcopy(facts)
    current_key = (facts.get('financial_period'), facts.get('basis'))
    current = next((r for r in rows if (r['period'], r['basis']) == current_key), None)
    preferred_required = preferred_required or any(_known(r) for r in rows)
    if current is None:
        inputs = facts.get('inputs') or {}
        unresolved_scope = any(r.get('has_discontinued_operations') or r.get('scope') in
                               ('UNRESOLVED', 'CONTINUING') for r in rows)
        current = dict(inputs, period=current_key[0], basis=current_key[1],
                       scope='UNRESOLVED' if unresolved_scope else 'REPORTED',
                       dividends_total=inputs.get('dividends'))
    current = _normalise(current, required_scope=scope, preferred_required=preferred_required)
    current['reported_fcf'] = (facts.get('inputs') or {}).get('fcf')
    current['reported_net_income'] = (facts.get('inputs') or {}).get('net_income')
    annual = []
    cash_raw = {r['period']: r.get('value') for r in facts.get('annual_fcf_series', [])}
    income_raw = {r['period']: r.get('value') for r in facts.get('annual_net_income_series', [])}
    revenue_raw = {r['period']: r.get('value') for r in facts.get('annual_revenue_series', [])}
    annual_rows = {r['period']: r for r in rows if r['basis'] == 'FY'}
    for period in sorted(set(cash_raw) | set(annual_rows), reverse=True):
        row = annual_rows.get(period)
        if row is None:
            # Do not mix an unbridged old consolidated year into a recast mean.
            row = dict(period=period, basis='FY', scope='REPORTED', net_income=income_raw.get(period),
                       revenue=revenue_raw.get(period))
        adjusted = _normalise(row, required_scope=scope, preferred_required=preferred_required)
        if not preferred_required and scope is None and period not in annual_rows:
            adjusted['common_fcf'] = finite_number(cash_raw.get(period))
        adjusted['reported_fcf'] = cash_raw.get(period)
        adjusted['reported_net_income'] = income_raw.get(period)
        annual.append(adjusted)
    conflicts = copy.deepcopy(facts.get('valuation_input_conflicts') or [])
    selected = []
    for row in annual[:5]:
        if row['common_fcf'] is None:
            break
        selected.append(row)
    consecutive = all(300 <= (date.fromisoformat(a['period'])-date.fromisoformat(b['period'])).days <= 400
                      for a, b in zip(selected, selected[1:]))
    cycle_complete = (not facts.get('midcycle') or (len(selected) >= 3 and consecutive
                      and all(r['common_net_income'] is not None for r in selected)))
    complete = (current['common_fcf'] is not None and current['common_net_income'] is not None
                and current['scope_matched'] and cycle_complete)
    resolved = []
    if primary and complete:
        resolved = [c for c in conflicts if c['code'] in RESOLVABLE]
        conflicts = [c for c in conflicts if c['code'] not in RESOLVABLE]
    reasons = []
    if not current['scope_matched']:
        reasons.append(('DISPOSED_BUSINESS_IN_CYCLE_PROXY', 'Operating cash and capital spending lack a matching business scope.'))
    if preferred_required and current.get('preferred_cash_paid') is None:
        reasons.append(('COMMON_EQUITY_CLAIMS_OMITTED', 'Paid preferred dividends are unavailable for the current financial window.'))
    if facts.get('midcycle') and not cycle_complete and (preferred_required or scope):
        reasons.append(('COMMON_EQUITY_CLAIMS_OMITTED', 'A complete common-equity cash/earnings bridge is unavailable for at least three comparable years.'))
    for code, reason in reasons:
        if code not in {c['code'] for c in conflicts}:
            conflicts.append(dict(code=code, reason=reason, detected_at=as_of.date().isoformat()))
    result['valuation_input_conflicts'] = conflicts
    result['common_equity_basis'] = dict(schema=SCHEMA, current=current, annual=annual,
        required_scope=scope, preferred_claims_required=preferred_required,
        resolved_input_conflicts=resolved,
        annual_fcf_series=[dict(period=r['period'], value=r['common_fcf']) for r in annual],
        annual_net_income_series=[dict(period=r['period'], value=r['common_net_income']) for r in annual],
        annual_revenue_series=[dict(period=r['period'], value=r['comparable_revenue']) for r in annual],
        enterprise_epv_compatible=not preferred_required and scope is None and all(
            r.get('scope') == 'REPORTED' and not r.get('has_discontinued_operations') for r in rows))
    if primary:
        result['common_equity_basis'].update(published_at=primary['published_at'], fetched_at=primary['fetched_at'],
                                            source_urls=primary['source_urls'])
        result['source_urls'] = list(dict.fromkeys(facts.get('source_urls', []) + primary['source_urls']))
    return result
