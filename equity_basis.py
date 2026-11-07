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
PREFERRED_AMOUNTS = ('preferred_cash_paid', 'preferred_earnings_deduction', 'preferred_outstanding')
CORRECTION_FIELDS = MONEY_FIELDS + ('preferred_claims_known',)
RESOLVABLE = {'DISPOSED_BUSINESS_IN_CYCLE_PROXY', 'COMMON_EQUITY_CLAIMS_OMITTED'}
# Largest change of the preferred balance across a window for which its
# declared dividend stands in for an undisclosed cash payment. P&G's ESOP
# preferred fell 777m -> 747m (-3.9%) over the September 2026 TTM through
# conversions; OXY's Berkshire preferred stayed at 8,287m from 2023 to June
# 2026. OXY's 2023 redemptions (9,762m -> 8,287m) fail the test: that year's
# 923m deduction included a 151m premium against 762m of cash dividends.
STABLE_PREFERRED = .05


def material_discontinued(row):
    """A discontinued business large enough to change the row's perimeter.

    Rows extracted before the materiality field existed keep the
    conservative reading of any discontinued line."""
    material = row.get('discontinued_material')
    return bool(row.get('has_discontinued_operations') if material is None else material)


def _year_before(day):
    try:
        return day.replace(year=day.year-1)
    except ValueError:  # February 29
        return day.replace(year=day.year-1, day=28)


def _overlaps(row, period):
    """True when a twelve-month row and the twelve months to `period` share any days."""
    if not period or not row.get('period'):
        return False
    end, other = date.fromisoformat(period), date.fromisoformat(row['period'])
    return other > _year_before(end) and _year_before(other) < end


def _stable_preferred(rows, period):
    """Known preferred balances stay within 5% from the window's opening to its end."""
    if not period:
        return False
    end = date.fromisoformat(period)
    opening = _year_before(end)
    balances = []
    for row in rows:
        balance = finite_number(row.get('preferred_outstanding'))
        if balance is not None:
            balances.append((date.fromisoformat(row['period']), abs(balance)))
    balances.sort()
    before = [b for day, b in balances if day <= opening]
    inside = [b for day, b in balances if opening < day <= end]
    if not before or not inside:
        return False
    values = [before[-1]] + inside
    return max(values) > 0 and min(values) >= (1-STABLE_PREFERRED) * max(values)


def _validate_reconciliations(row, fields):
    equations = (
        (('net_income', 'preferred_earnings_deduction', 'net_income_common'),
         'Primary common-income bridge does not reconcile'),
        (('net_income_before_noncontrolling', 'noncontrolling_earnings', 'net_income'),
         'Primary noncontrolling-income bridge does not reconcile'),
        (('capex_reported', 'capital_accrual_change', 'capex'),
         'Primary cash-capex accrual bridge does not reconcile'),
    )
    for operands, message in equations:
        if fields.isdisjoint(operands):
            continue
        total, deduction, remainder = (finite_number(row.get(key)) for key in operands)
        if None not in (total, deduction, remainder) and abs(total-deduction-remainder) > 1.:
            raise ValueError(message)


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
        if 'patch_fields' in row:
            fields = row['patch_fields']
            if (not isinstance(fields, list) or not fields or any(not isinstance(f, str) for f in fields)
                    or len(set(fields)) != len(fields)
                    or any(f not in CORRECTION_FIELDS or f not in row for f in fields)):
                raise ValueError('Primary field correction requires unique explicit equity fields')
        for field in MONEY_FIELDS:
            if row.get(field) is not None and finite_number(row[field]) is None:
                raise ValueError('Non-finite common-equity bridge amount: ' + field)
        if 'preferred_claims_known' in row and type(row['preferred_claims_known']) is not bool:
            raise ValueError('Preferred-claim disclosure must be boolean')
        _validate_reconciliations(row, set(MONEY_FIELDS))
        capex = finite_number(row.get('capex'))
        if capex is not None and capex < 0:
            raise ValueError('Primary cash capex must be nonnegative')
        seen.add(key)
    return published, fetched


def _known(row):
    return bool(row.get('preferred_claims_known') or any(
        finite_number(row.get(k)) not in (None, 0.) for k in
        PREFERRED_AMOUNTS))


def _preferred_in_window(rows, period):
    """Use payments within the year and the last known opening balance."""
    if not period:
        return False
    end = date.fromisoformat(period)
    opening = _year_before(end)
    balances = []
    for row in rows:
        day = date.fromisoformat(row['period'])
        if opening < day <= end and _known(row):
            return True
        balance = finite_number(row.get('preferred_outstanding'))
        if day <= opening and balance is not None:
            balances.append((day, abs(balance)))
    # A closing zero alone cannot establish when an earlier claim was retired.
    return bool(balances and max(balances)[1])


def _reported_current(facts, rows):
    inputs = facts.get('inputs') or {}
    # Only rows that share days with the current window can put a disposed
    # business or a recast perimeter into it; Broadcom's FY2024 VMware sale
    # says nothing about a later SEC catch-up window.
    unresolved_scope = any((material_discontinued(r) or r.get('scope') in ('UNRESOLVED', 'CONTINUING'))
                           and _overlaps(r, facts.get('financial_period')) for r in rows)
    return dict(inputs, period=facts.get('financial_period'), basis=facts.get('basis'),
                scope='UNRESOLVED' if unresolved_scope else 'REPORTED',
                reported_fcf=inputs.get('fcf'), dividends_total=inputs.get('dividends'))


def _normalise(row, *, required_scope=None, preferred_required=False, declared_ok=False):
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
    # Cash paid wins. When the issuer reports only the declared dividend
    # (P&G's ESOP preferred, OXY's Berkshire preferred in Yahoo's rows), that
    # same-window declaration is the claim if the balance did not move: no
    # redemption premium sits in it and equal quarterly payments leave the
    # payable unchanged. A moved balance keeps the claim unknown.
    if paid is not None:
        claim, claim_basis = abs(paid), 'PAID'
    elif known and declared_ok and deduction is not None:
        claim, claim_basis = abs(deduction), 'DECLARED_STABLE_BALANCE'
    elif not known:
        claim, claim_basis = 0., 'NO_PREFERRED_CLAIM'
    else:
        claim, claim_basis = None, None
    fcf = before-claim if before is not None and claim is not None else None
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
        dividend = abs(total)-claim if claim is not None and abs(total) >= claim else None
    result.update(common_fcf=fcf, fcf_before_preferred=before, common_net_income=common,
                  preferred_cash_claim=claim, preferred_cash_basis=claim_basis,
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
    scope = None
    # Older SEC catch-up packets persisted an inferred flag across all
    # historical years. Their retained rows are the actual dated evidence.
    legacy_inference = (facts.get('financial_source') == 'SEC_COMPANYFACTS'
                        and not facts.get('preferred_claims_explicit')
                        and any(_known(row) for row in rows))
    explicit_claim = bool(facts.get('preferred_claims_required') and not legacy_inference)
    current_key = (facts.get('financial_period'), facts.get('basis'))
    unapplied_claims = []
    primary = None
    primary_applied = current_full_bridge = False
    if bridge:
        published, fetched = validate(bridge, symbol=facts.get('symbol'),
                                      currency=bridge.get('currency'))
        if published <= fetched <= as_of:
            primary = bridge
            explicit_claim = explicit_claim or bridge['preferred_claims_required']
            if any('patch_fields' not in row for row in bridge['periods']):
                if facts.get('financial_currency') not in (None, bridge['currency']):
                    raise ValueError('Common-equity bridge financial currency mismatch')
                scope = bridge['required_scope']
            keyed = {(r['period'], r['basis']): r for r in rows}
            for row in bridge['periods']:
                identity = (row['period'], row['basis'])
                if 'patch_fields' not in row:
                    keyed[identity] = copy.deepcopy(row)
                    primary_applied = True
                    current_full_bridge = current_full_bridge or identity == current_key
                    continue
                prior = keyed.get(identity)
                if prior is None and identity == current_key:
                    prior = _reported_current(facts, rows)
                if (prior is None or prior.get('scope', 'REPORTED') != row['scope']
                        or facts.get('financial_currency') != bridge['currency']):
                    # These facts can establish a dated preferred obligation
                    # even when their amounts cannot be merged into a packet.
                    unapplied_claims.append(dict(period=row['period'], **{
                        f: row[f] for f in row['patch_fields'] if f in
                        PREFERRED_AMOUNTS + ('preferred_claims_known',)}))
                    continue
                corrected = copy.deepcopy(prior)
                for field in row['patch_fields']:
                    corrected[field] = row[field]
                    corrected.setdefault('field_sources', {})[field] = dict(
                        source_urls=row['source_urls'], published_at=bridge['published_at'],
                        fetched_at=bridge['fetched_at'])
                _validate_reconciliations(corrected, set(row['patch_fields']))
                keyed[identity] = corrected
                primary_applied = True
            rows = list(keyed.values())
    claim_rows = rows + unapplied_claims
    if not claim_rows and not explicit_claim:
        return facts
    result = copy.deepcopy(facts)
    current = next((r for r in rows if (r['period'], r['basis']) == current_key), None)
    preferred_required = explicit_claim or _preferred_in_window(claim_rows, current_key[0])
    if current is None:
        current = _reported_current(facts, rows)
    current = _normalise(current, required_scope=scope, preferred_required=preferred_required,
                         declared_ok=_stable_preferred(claim_rows, current_key[0]))
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
        annual_preferred = explicit_claim or _preferred_in_window(claim_rows, period)
        adjusted = _normalise(row, required_scope=scope, preferred_required=annual_preferred,
                              declared_ok=_stable_preferred(claim_rows, period))
        if not annual_preferred and scope is None and period not in annual_rows:
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
    midcycle = bool(facts.get('midcycle'))
    cycle_complete = (not midcycle or (len(selected) >= 3 and consecutive
                      and all(r['common_net_income'] is not None for r in selected)))
    current_complete = (current['common_fcf'] is not None and current['common_net_income'] is not None
                        and current['scope_matched'])
    current_reasons = []
    if not current['scope_matched']:
        current_reasons.append(('DISPOSED_BUSINESS_IN_CYCLE_PROXY', 'Operating cash and capital spending lack a matching business scope.'))
    if preferred_required and current.get('preferred_cash_claim') is None:
        current_reasons.append(('COMMON_EQUITY_CLAIMS_OMITTED', 'Paid preferred dividends are unavailable for the current financial window.'))
    # A commodity value and its multiple use the cycle years only. When an
    # issuer bridge fixes their perimeter (scope) and at least three of them
    # are complete on it, an open current window withdraws the current cash
    # ratios, not the cycle valuation. Without such a bridge, a disposal in
    # the current window still means the older years hold the sold business.
    cycle_bridged = midcycle and scope is not None and cycle_complete
    resolved = []
    if (current_full_bridge and current_complete and cycle_complete) or cycle_bridged:
        resolved = [c for c in conflicts if c['code'] in RESOLVABLE]
        conflicts = [c for c in conflicts if c['code'] not in RESOLVABLE]
    reasons = [] if cycle_bridged else list(current_reasons)
    if midcycle and not cycle_complete and (preferred_required or scope):
        reasons.append(('COMMON_EQUITY_CLAIMS_OMITTED', 'A complete common-equity cash/earnings bridge is unavailable for at least three comparable years.'))
    for code, reason in reasons:
        if code not in {c['code'] for c in conflicts}:
            conflicts.append(dict(code=code, reason=reason, detected_at=as_of.date().isoformat(),
                                  origin='ENGINE'))
    result['valuation_input_conflicts'] = conflicts
    result['common_equity_basis'] = dict(schema=SCHEMA, current=current, annual=annual,
        required_scope=scope, preferred_claims_required=preferred_required,
        current_window_open=[reason for _, reason in current_reasons] if cycle_bridged else [],
        resolved_input_conflicts=resolved,
        annual_fcf_series=[dict(period=r['period'], value=r['common_fcf']) for r in annual],
        annual_net_income_series=[dict(period=r['period'], value=r['common_net_income']) for r in annual],
        annual_revenue_series=[dict(period=r['period'], value=r['comparable_revenue']) for r in annual],
        enterprise_epv_compatible=not preferred_required and scope is None and all(
            r.get('scope', 'REPORTED') == 'REPORTED' and not material_discontinued(r) for r in rows))
    if primary_applied:
        result['common_equity_basis'].update(published_at=primary['published_at'], fetched_at=primary['fetched_at'],
                                            source_urls=primary['source_urls'])
    if primary:
        result['source_urls'] = list(dict.fromkeys(facts.get('source_urls', []) + primary['source_urls']))
    return result
