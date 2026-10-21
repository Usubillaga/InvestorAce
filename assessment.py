"""Strict score completeness and explicit, input-bound analyst approvals.

Arithmetic, declared evidence and an analyst's approval are separate outputs.
The register records accountable assertions; this code cannot authenticate a URL.
"""
import copy
import json
import math
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

from evidence import digest, valuation_contract
from integrity import finite_number, positive_number

VERSION = 'assessment-v1'
REVIEW_SCHEMA = 'assessment-reviews-v1'
QUOTE_MAX_AGE_HOURS = 96
WEIGHTS = dict(g=.15, p=.20, c=.15, b=.15, v=.10, pr=.15, r=.05, d=.05)
LABELS = dict(g='Growth', p='Profitability', c='Cash Generation', b='Balance Sheet',
              v='Valuation', pr='Priced-In Expectations', r='Shareholder Returns', d='Dilution')
INPUT_FIELDS = ('yf', 'isin', 'fcf', 'shares', 'r', 'r_wacc', 'cur', 'sub', 'dil', 'pr',
    'cash_flow_basis', 'discount_rate_basis', 'net_debt', 'financial_period',
    'financial_published_at', 'shares_asof', 'share_count_date', 'normalization_status',
    'built', 'draft_components', 'deliver', 'deliver_basis', 'midcycle', 'price',
    'quote_observed_at', 'trap', 'risk_floor', 'review_objections')


def timestamp(value):
    try:
        result = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return result if result.utcoffset() is not None else None
    except (TypeError, ValueError):
        return None


def _now(value):
    value = datetime.now(timezone.utc) if value is None else value
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError('Assessment cutoff requires a timezone')
    return value


def material_objections(objections):
    return [item for item in (objections or []) if item.get('severity') in ('major', 'critical')
            and item.get('status') not in ('verified', 'rejected')]


def source_after(value, cutoff):
    """Preserve supplied date precision; never truncate malformed timestamps."""
    if isinstance(value, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        return date.fromisoformat(value) > cutoff.date()
    observed = timestamp(value)
    if observed is None:
        raise ValueError('Source requires an ISO date or timezone-aware timestamp')
    return observed > cutoff


def quote_status(row, as_of):
    if positive_number(row.get('price')) is None:
        return 'MISSING'
    observed = timestamp(row.get('quote_observed_at'))
    if observed is None:
        return 'TIME_UNKNOWN'
    age = (as_of - observed).total_seconds() / 3600
    return 'FUTURE' if age < 0 else 'STALE' if age > QUOTE_MAX_AGE_HOURS else 'DATED'


def model_band(score):
    score = finite_number(score)
    if score is None or not 0 <= score <= 10:
        return None
    for ceiling, label in ((3.5, 'SELL'), (5.5, 'HOLD NEG'), (7., 'HOLD POS'),
                           (8.5, 'BUY'), (math.inf, 'STRONG BUY')):
        if score < ceiling:
            return label


def input_hash(row, weights, priced_in):
    return digest(dict(version=VERSION, weights=weights, priced_in=priced_in,
                       inputs={key: row.get(key) for key in INPUT_FIELDS}))


def _urls(values):
    if not isinstance(values, list) or not values:
        return False
    for value in values:
        try:
            parsed = urlsplit(value)
            if (parsed.scheme != 'https' or not parsed.hostname or parsed.username
                    or parsed.password or parsed.port not in (None, 443)):
                return False
        except (TypeError, ValueError):
            return False
    return True


def load_reviews(payload=None):
    if payload is None:
        payload = Path(__file__).with_name('assessment_reviews.json').read_text(encoding='utf-8')
    doc = json.loads(payload) if isinstance(payload, str) else copy.deepcopy(payload)
    try:
        json.dumps(doc, allow_nan=False)
        if doc['schema'] != REVIEW_SCHEMA or not isinstance(doc['entries'], dict):
            raise ValueError('Unsupported assessment review register')
        for ticker, note in doc['entries'].items():
            if not isinstance(ticker, str) or not ticker or note['status'] not in ('APPROVED', 'PENDING'):
                raise ValueError('Invalid assessment review entry')
            if note['status'] == 'PENDING':
                continue
            reviewed, until = timestamp(note.get('reviewed_at')), timestamp(note.get('valid_until'))
            sources = note.get('category_sources', {})
            if (not re.fullmatch('[a-f0-9]{64}', str(note.get('input_sha256')))
                    or reviewed is None or until is None or until < reviewed
                    or not isinstance(note.get('reviewer'), str) or not note['reviewer'].strip()
                    or set(sources) != set(WEIGHTS)
                    or not all(_urls(sources[key]) for key in WEIGHTS)
                    or not _urls(note.get('normalization_sources'))):
                raise ValueError('Approval requires bound inputs, dates, reviewer and category evidence')
        return doc
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError('Malformed assessment review register') from exc


def assess(row, weights, *, priced_in, raw_score, reviews=None, ticker=None, as_of=None):
    as_of = _now(as_of)
    if weights != WEIGHTS:
        raise ValueError('Assessment weights must match the versioned eight-category contract')
    reviews = load_reviews(reviews) if reviews is not None else load_reviews()
    issues = []

    def issue(code, message):
        issues.append(dict(code=code, message=message, severity='major', status='open'))

    values = {key: None for key in weights}
    sub = row.get('sub')
    has_sub = isinstance(sub, (tuple, list)) and len(sub) == 6
    if has_sub:
        values.update(zip(('g', 'p', 'c', 'b', 'v', 'r'), sub))
    elif isinstance(row.get('draft_components'), dict):
        values.update({key: row['draft_components'].get(key) for key in ('g', 'p', 'c', 'b', 'v', 'r')})
    values['d'] = row.get('dil')
    qstatus = quote_status(row, as_of)
    values['pr'] = priced_in if qstatus == 'DATED' else None
    if qstatus != 'DATED':
        issue('QUOTE_' + qstatus, 'Current price-dependent assessment requires a dated quote within 96 hours.')
    components, invalid = [], []
    for key, weight in weights.items():
        raw, value = values[key], finite_number(values[key])
        if raw is not None and (value is None or not 0 <= value <= 10):
            invalid.append(key)
            value = None
        values[key] = value
        components.append(dict(key=key, label=LABELS[key], value=value, nominal_weight=weight,
            effective_weight=weight if value is not None else 0.,
            contribution=value * weight if value is not None else None))
    missing = [key for key in weights if values[key] is None]
    coverage = sum(weights[key] for key in weights if values[key] is not None)
    lower = sum(item['contribution'] for item in components if item['contribution'] is not None)
    legacy_only = not has_sub and not row.get('draft_components')
    status = ('INVALID' if invalid else 'LEGACY_TOTAL' if legacy_only and raw_score is not None
              else 'PARTIAL' if missing else 'COMPLETE')
    score = lower if status == 'COMPLETE' else None
    if missing or invalid:
        issue('INCOMPLETE_SCORE', 'All eight nominal contributions are required; missing weights are not redistributed.')
    if legacy_only:
        issue('LEGACY_TOTAL', 'The supplied total has no complete category decomposition.')
    contract = valuation_contract(row)
    if contract['status'] != 'DECLARED' or contract['issues']:
        issue('VALUATION_CONTRACT', 'Cash-flow basis, discount rate, shares and dated sources require review.')
    if row.get('normalization_status') != 'VERIFIED':
        issue('NORMALIZATION', 'Sustainable cash flow has no explicitly verified normalization bridge.')
    if material_objections(row.get('review_objections')):
        issue('OPEN_OBJECTION', 'A material recorded research objection is not independently closed.')
    for key in ('financial_published_at', 'shares_asof', 'share_count_date'):
        if row.get(key):
            try:
                if source_after(row[key], as_of):
                    issue('FUTURE_SOURCE', 'A financial/share observation postdates the assessment.')
            except ValueError:
                issue('SOURCE_DATE', 'Financial/share dates require an ISO calendar date.')
    bound_hash = input_hash(row, weights, priced_in)
    note = reviews['entries'].get(ticker, {})
    if note.get('status') != 'APPROVED':
        issue('REVIEW_PENDING', 'An explicit input-bound analyst approval is still pending.')
    else:
        reviewed = timestamp(note['reviewed_at'])
        if note['input_sha256'] != bound_hash:
            issue('REVIEW_INPUT_CHANGED', 'Financial, score, quote or rate inputs differ from the approved packet.')
        if timestamp(note['reviewed_at']) > as_of:
            issue('FUTURE_REVIEW', 'Review timestamp postdates this assessment.')
        if timestamp(note['valid_until']) < as_of:
            issue('REVIEW_EXPIRED', 'The explicit analyst review validity has expired.')
        observed = timestamp(row.get('quote_observed_at'))
        if observed and observed > reviewed:
            issue('REVIEW_BEFORE_QUOTE', 'The approved quote postdates the analyst review.')
        for key in ('financial_published_at', 'shares_asof', 'share_count_date'):
            if row.get(key):
                try:
                    if source_after(row[key], reviewed):
                        issue('REVIEW_BEFORE_SOURCE', 'A financial/share source postdates the analyst review.')
                except ValueError:
                    issue('SOURCE_DATE', 'Source dates require an ISO date or timezone-aware timestamp.')
        for objection in note.get('issues', []):
            if (objection.get('severity') in ('major', 'critical')
                    and objection.get('status') not in ('verified', 'rejected')):
                issue('OPEN_OBJECTION', 'A material analyst objection remains unresolved.')
    approved = score is not None and not issues
    rating = model_band(score) if approved else None
    expires = (min(timestamp(note['valid_until']),
                   timestamp(row['quote_observed_at']) + timedelta(hours=QUOTE_MAX_AGE_HOURS))
               if approved else None)
    return dict(schema=VERSION, as_of=as_of.isoformat(), input_sha256=bound_hash,
        calculation_status=status, raw_score=finite_number(raw_score), model_score=score,
        model_band=model_band(score), components=components, missing_components=missing,
        imputed_components=[], coverage_weight=coverage,
        score_lower=lower, score_upper=lower + 10 * (1 - coverage),
        quote_status=qstatus, quote_observed_at=row.get('quote_observed_at'), price=row.get('price'),
        review_status='REVIEWED' if approved else 'REVIEW_REQUIRED',
        reviewed_at=note.get('reviewed_at'), valid_until=note.get('valid_until'),
        expires_at=expires.isoformat() if expires else None,
        rating=rating, rating_score=score if approved else None,
        quality_rank_eligible=approved,
        new_entry_eligible=approved and score >= 7. and not row.get('trap'), issues=issues)


def project(stored, *, raw_score=None, as_of=None, objections=None):
    """Project frozen evidence; old snapshots never acquire an approval by inference."""
    as_of = _now(as_of)
    if not isinstance(stored, dict) or stored.get('schema') != VERSION:
        return dict(schema=VERSION, raw_score=finite_number(raw_score), model_score=None,
            model_band=None, rating=None, rating_score=None, calculation_status='LEGACY_SNAPSHOT',
            review_status='REVIEW_REQUIRED', quality_rank_eligible=False, new_entry_eligible=False,
            components=[], missing_components=list(WEIGHTS), coverage_weight=0.,
            score_lower=0., score_upper=10., issues=[dict(code='ASSESSMENT_ABSENT',
                message='This archived generation predates the shared assessment contract.', severity='major', status='open')])
    result = copy.deepcopy(stored)
    captured = timestamp(result.get('as_of'))
    qstatus = quote_status(result, as_of)
    expired = timestamp(result.get('expires_at')) or timestamp(result.get('valid_until'))
    blocked = material_objections(objections)
    invalid_review = result.get('quality_rank_eligible') and (expired is None or timestamp(result.get('reviewed_at')) is None)
    if captured is None or captured > as_of or qstatus != 'DATED' or (expired and expired < as_of) or blocked or invalid_review:
        result.update(rating=None, rating_score=None, review_status='REVIEW_REQUIRED',
                      quality_rank_eligible=False, new_entry_eligible=False)
        if qstatus != 'DATED' or captured is None or captured > as_of:
            result.update(model_score=None, model_band=None, quote_status=qstatus)
            for item in result['components']:
                if item['key'] == 'pr':
                    item.update(value=None, contribution=None, effective_weight=0.)
            result['coverage_weight'] = sum(item['nominal_weight'] for item in result['components']
                                            if item['value'] is not None)
            result['missing_components'] = [item['key'] for item in result['components'] if item['value'] is None]
            result['score_lower'] = sum(item['contribution'] for item in result['components']
                                        if item['contribution'] is not None)
            result['score_upper'] = result['score_lower'] + 10 * (1 - result['coverage_weight'])
            if result['calculation_status'] == 'COMPLETE':
                result['calculation_status'] = 'PARTIAL'
        result['issues'].append(dict(code='ASSESSMENT_EXPIRED', message='Frozen assessment is not current at this cutoff.',
                                     severity='major', status='open'))
        if blocked:
            result['issues'].append(dict(code='OPEN_OBJECTION', message='A current material objection withdraws approval.',
                                         severity='major', status='open'))
    return result
