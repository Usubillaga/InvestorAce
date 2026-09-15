"""Optional constrained portfolio proposal. Raw regime ranking stays untouched."""
from evidence import number
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone


@dataclass(frozen=True)
class TradePolicy:
    """Configurable planning assumptions, not optimised return forecasts."""
    stop_loss_pct: float = 0.10
    holding_min_days: int = 90
    holding_max_days: int = 180
    review_every_days: int = 30
    entry_valid_days: int = 7

    def __post_init__(self):
        if number(self.stop_loss_pct) is None or not 0 < self.stop_loss_pct < 1:
            raise ValueError('Stop-loss fraction must be between zero and one')
        days = (self.holding_min_days, self.holding_max_days, self.review_every_days, self.entry_valid_days)
        if any(type(d) is not int or d < 1 for d in days):
            raise ValueError('Holding, review and validity periods must be positive integer days')
        if self.holding_max_days < self.holding_min_days:
            raise ValueError('Maximum holding period precedes minimum')


DEFAULT_POLICY = TradePolicy()


def trade_plan(row, entry_ceiling, policy=DEFAULT_POLICY, as_of=None):
    """New-entry scenario only; never changes an existing position's stop.

    The caller supplies engine.entry_price(row), preserving the existing 60%
    NGV-cover rule. A lower current quote caps the proposed buy limit.
    """
    today = date.fromisoformat(as_of) if as_of else datetime.now(timezone.utc).date()
    price, ceiling = number(row.get('price')), number(entry_ceiling)
    result = {'as_of': today.isoformat(), 'currency': row.get('cur'),
              'quote': price, 'quote_retrieved_at': row.get('price_ts'),
              'entry_ceiling': ceiling, 'entry_limit': None, 'initial_stop': None,
              'stop_loss_pct': policy.stop_loss_pct,
              'holding_min_days': policy.holding_min_days,
              'holding_max_days': policy.holding_max_days,
              'review_every_days': policy.review_every_days,
              'entry_valid_until': (today + timedelta(days=policy.entry_valid_days)).isoformat(),
              'status': 'UNAVAILABLE', 'basis': 'legacy-ngv-cover-60pct; fixed-percent-stop-v1'}
    if price is None or price <= 0 or ceiling is None or ceiling <= 0 or not row.get('cur'):
        result['reason'] = 'Positive quote, NGV entry ceiling and quote currency required'
        return result
    entry = min(price, ceiling)
    result.update(entry_limit=entry, initial_stop=entry * (1 - policy.stop_loss_pct),
                  status='WITHIN_ENTRY_CEILING' if price <= ceiling else 'WAIT_FOR_PULLBACK')
    return result


def filled_plan(plan, fill_price, filled_on):
    """Explicitly create a fixed plan from an actual fill; no order submission.

    Persist this returned object separately if tracking a real holding. Rebuilding
    the proposed portfolio must not reset this stop or the holding clock.
    """
    fill = number(fill_price)
    day = date.fromisoformat(filled_on)
    if plan.get('status') == 'UNAVAILABLE' or fill is None or fill <= 0:
        raise ValueError('Available entry plan and positive actual fill required')
    if not date.fromisoformat(plan['as_of']) <= day <= date.fromisoformat(plan['entry_valid_until']):
        raise ValueError('Entry plan not valid on fill date; refresh it before entry')
    if fill > plan['entry_limit']:
        raise ValueError('Fill exceeds the planned buy limit')
    return dict(plan, status='FILLED', actual_entry=fill, filled_on=day.isoformat(),
                initial_stop=fill * (1 - plan['stop_loss_pct']),
                next_review=(day + timedelta(days=plan['review_every_days'])).isoformat(),
                holding_review_from=(day + timedelta(days=plan['holding_min_days'])).isoformat(),
                mandatory_reassessment_on=(day + timedelta(days=plan['holding_max_days'])).isoformat())


def construct(ranked, target_size=10, max_per_sector=2, max_weight=0.10,
              entry_limits=None, policy=DEFAULT_POLICY, as_of=None):
    """Accept (ticker, row, fit) from engine.regime_book(regime, len(DATA)).

    Equal target slots; unfilled slots stay in cash. No renormalisation that
    could violate a weight cap. Existing holdings never affect stock fit.
    """
    if target_size < 1 or max_per_sector < 1 or not 0 < max_weight <= 1:
        raise ValueError('Positive size/sector limits and weight in (0,1] required')
    if len({x[0] for x in ranked}) != len(ranked):
        raise ValueError('Duplicate ticker')
    if any(number(x[2]) is None for x in ranked):
        raise ValueError('Every candidate requires a finite fit')
    ranked = sorted(ranked, key=lambda x: (-x[2], x[0]))
    counts, positions, exclusions = {}, [], []
    slot = min(1 / target_size, max_weight)
    for ticker, row, fit in ranked:
        sector = row.get('sector') or 'UNKNOWN'
        reason = None
        if number(row.get('price')) is None or row['price'] <= 0:
            reason = 'NO_VALID_PRICE'
        elif sector == 'UNKNOWN':
            reason = 'UNKNOWN_SECTOR'
        elif counts.get(sector, 0) >= max_per_sector:
            reason = 'SECTOR_LIMIT'
        elif len(positions) >= target_size:
            reason = 'TARGET_SIZE'
        if reason:
            exclusions.append({'ticker': ticker, 'reason': reason})
            continue
        plan = trade_plan(row, (entry_limits or {}).get(ticker), policy, as_of)
        positions.append({'ticker': ticker, 'fit': fit, 'sector': sector, 'weight': slot,
                          'trade_plan': plan, 'planned_loss_at_stop': slot * policy.stop_loss_pct
                          if plan['status'] != 'UNAVAILABLE' else None})
        counts[sector] = counts.get(sector, 0) + 1
    return {'method': 'equal-slots-sector-cap-entry-plan-v2', 'positions': positions,
            'cash_weight': max(0.0, 1 - sum(p['weight'] for p in positions)),
            'target_size': target_size, 'max_per_sector': max_per_sector,
            'max_weight': max_weight, 'exclusions': exclusions,
            'status': 'PROPOSAL', 'note': 'No trade execution; correlation and liquidity need separate review.'}
