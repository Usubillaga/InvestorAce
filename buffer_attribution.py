"""Accounting attribution for long-only SMA200 buffer variants, in simulated quote units."""
import math


class Trace:
    def __init__(self):
        self.decisions = {}
        self.lots = {}
        self.open = {}
        self.final = None

    def buy(self, symbol, signal, day, shares, price, gap, cost):
        lot = dict(symbol=symbol, signal=str(signal.date()), entry=str(day.date()), shares=shares,
                   entry_price=float(price), gap_pct=float(gap), entry_cost=float(shares * price * (1 + cost)))
        self.open[symbol] = lot
        self.lots[(lot['entry'], symbol)] = lot

    def mark(self, symbol, day, price, reason, cost):
        lot = self.open.pop(symbol)
        lot.update(end=str(day.date()), end_price=float(price), reason=reason,
                   pnl=float(lot['shares'] * price * (1 - cost) - lot['entry_cost']))

    def first_difference(self, other):
        for day in sorted(self.decisions.keys() | other.decisions.keys()):
            left, right = self.decisions.get(day, []), other.decisions.get(day, [])
            if left != right:
                return dict(signal=day, baseline=left, buffer=right,
                            baseline_only=[order for order in left if order not in right],
                            buffer_only=[order for order in right if order not in left])
        return None


def compare(base, buffer, capital):
    lots = []
    for key in sorted(base.lots.keys() | buffer.lots.keys()):
        left, right = base.lots.get(key), buffer.lots.get(key)
        if left == right:
            continue
        pnl = (right['pnl'] if right else 0) - (left['pnl'] if left else 0)
        lots.append(dict(entry=key[0], symbol=key[1], baseline=left, buffer=right,
                         delta_pnl=pnl, total_return_pp=100 * pnl / capital))
    delta = buffer.final - base.final
    if not math.isclose(sum(row['delta_pnl'] for row in lots), delta, abs_tol=1e-6, rel_tol=1e-10):
        raise ValueError('SMA200 position contributions do not reconcile to ending equity')
    return dict(first_order=base.first_difference(buffer), positions=lots, delta_pnl=delta,
                total_return_pp=100 * delta / capital)


def summary(window, audit):
    first = audit['first_order']
    lines = [f'### {window}', '']
    if first:
        lines += [f"First differing order plan on {first['signal']} (side, symbol, shares): "
                  f"v1.6 only {first['baseline_only']}, 1% only {first['buffer_only']}.", '']
    else:
        lines += ['Order plans identical.', '']
    positions = audit['positions']
    lines += [f"Ending equity difference: {audit['delta_pnl']:+.2f}; total-return difference "
              f"{audit['total_return_pp']:+.2f} percentage points. Differing positions: {len(positions)}.", '']
    gains = sorted((p for p in positions if p['delta_pnl'] > 0), key=lambda p: -p['delta_pnl'])
    if gains:
        share = sum(p['delta_pnl'] for p in gains[:2]) / sum(p['delta_pnl'] for p in gains)
        lines += [f'Two largest positive contributions: {share:.1%} of gross positive contributions. '
                  'This describes concentration within this historical path.', '']
    if gains:
        for p in gains[:2]:
            lines.append(f"Largest positive lot: {p['symbol']} entered {p['entry']}, "
                         f"{p['total_return_pp']:+.3f} total-return pp.")
        lines.append('')
    if positions:
        lines += ['First differing fills and subsequent positions (first 10; complete ledger in backtests/latest.json).',
                  '', '| Entry | Symbol | v1.6 shares | 1% shares | Difference in total return (pp) |',
                  '|---|---|---:|---:|---:|']
        for p in positions[:10]:
            lines.append(f"| {p['entry']} | {p['symbol']} | {(p['baseline'] or {}).get('shares', 0)} | "
                         f"{(p['buffer'] or {}).get('shares', 0)} | {p['total_return_pp']:+.3f} |")
        lines.append('')
    for name, match in audit['thresholds'].items():
        lines.append(f"{name} vs 1%: order plans identical = {match['plans_identical']}, "
                     f"executed positions identical = {match['positions_identical']}.")
    return lines + ['']
