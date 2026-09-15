"""Optional constrained portfolio proposal. Raw regime ranking stays untouched."""
from evidence import number


def construct(ranked, target_size=30, max_per_sector=6, max_weight=0.05):
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
        positions.append({'ticker': ticker, 'fit': fit, 'sector': sector, 'weight': slot})
        counts[sector] = counts.get(sector, 0) + 1
    return {'method': 'equal-slots-sector-cap-v1', 'positions': positions,
            'cash_weight': max(0.0, 1 - sum(p['weight'] for p in positions)),
            'target_size': target_size, 'max_per_sector': max_per_sector,
            'max_weight': max_weight, 'exclusions': exclusions,
            'status': 'PROPOSAL', 'note': 'No trade execution; correlation and liquidity need separate review.'}
