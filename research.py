"""Offline, chronological comparison of simple versus signature path features.

This is a regularised return-prediction experiment using level-two signatures,
NOT a reproduction of the paper's direct mean-variance Sig-Trading optimizer.
Input: one instrument, point-in-time signals, consistently adjusted price index.
Run: python research.py observations.csv --output research-output/report.json
"""
from __future__ import annotations

import argparse
import csv
import math
from datetime import datetime, timezone

import numpy as np

from evidence import digest, number
from integrity import atomic_json
from path_features import signature2


def timestamp(value):
    stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if stamp.tzinfo is None:
        raise ValueError('Research timestamps must include a timezone')
    return stamp.astimezone(timezone.utc)


def validate(rows):
    previous = None
    for row in rows:
        now, known = timestamp(row['timestamp']), timestamp(row['known_at'])
        if known > now:
            raise ValueError('A signal was not known at its decision time')
        if previous is not None and now <= previous:
            raise ValueError('Observations must be strictly chronological and unique')
        previous = now
        if any(number(row.get(k)) is None for k in ('price', 'growth', 'inflation')):
            raise ValueError('No missing/non-finite observations or silently filled signals')
        if float(row['price']) <= 0:
            raise ValueError('Price index must be positive')
        if row.get('baseline_weight') is not None and not 0 <= float(row['baseline_weight']) <= 1:
            raise ValueError('Baseline weights must be in [0,1]')
    supplied = [r.get('baseline_weight') is not None for r in rows]
    if any(supplied) and not all(supplied):
        raise ValueError('Supply a frozen baseline weight for every observation or none')


def features(rows, t, window, kind):
    part = rows[t - window + 1:t + 1]
    logs = np.log([float(r['price']) for r in part])
    g = np.array([float(r['growth']) for r in part]) / 100
    i = np.array([float(r['inflation']) for r in part]) / 100
    returns = np.diff(logs)
    # End levels preserve information removed by signature translation invariance.
    base = [g[-1], i[-1], logs[-1] - logs[0]]
    if kind == 'levels':
        return np.array(base)
    if kind == 'simple':
        return np.array(base + [g[-1] - g[0], i[-1] - i[0], float(returns.std()),
                                float(np.mean(returns > 0))])
    if kind != 'signature2':
        raise ValueError(kind)
    start = timestamp(part[0]['timestamp'])
    elapsed = [(timestamp(r['timestamp']) - start).total_seconds() for r in part]
    points = [[e / elapsed[-1], p, a, b] for e, p, a, b in zip(elapsed, logs, g, i)]
    first, second = signature2(points)
    return np.array(base + first + [x for row in second for x in row])


def fit_predict(x, y, current, ridge):
    """All transformations fitted exclusively to the training observations."""
    mean, scale = x.mean(axis=0), x.std(axis=0)
    scale = np.where(scale < 1e-12, 1, scale)
    z, q = (x - mean) / scale, (current - mean) / scale
    average = y.mean()
    coef = np.linalg.solve(z.T @ z + ridge * np.eye(z.shape[1]), z.T @ (y - average))
    return float(average + q @ coef)


def evaluate(rows, window=21, min_train=60, ridge=10.0, cost_bps=10.0, periods_per_year=252):
    """Long-only cash/asset rules with one full bar execution delay.

    Feature at t -> fill at t+1 -> return t+1 to t+2. Training outcomes and
    feature windows end before the current feature window starts (purged).
    Transaction cost includes initial entry, drift-aware rebalancing and final
    liquidation. Costs are a first-order notional approximation; no market impact.
    """
    validate(rows)
    if window < 3 or min_train < 2 or ridge <= 0 or cost_bps < 0 or periods_per_year <= 0:
        raise ValueError('Invalid research configuration')
    kinds = ('levels', 'simple', 'signature2')
    names = ['buy_hold', 'momentum', *kinds]
    if rows and rows[0].get('baseline_weight') is not None:
        names.append('supplied_baseline')
    history = {name: [] for name in names}
    drifted = {name: 0.0 for name in names}
    xs = {kind: {} for kind in kinds}
    ys = {}
    for t in range(window - 1, len(rows) - 2):
        for kind in kinds:
            xs[kind][t] = features(rows, t, window, kind)
        ys[t] = float(rows[t + 2]['price']) / float(rows[t + 1]['price']) - 1
        # k+2 < t-window+1: no training outcome overlaps current feature window.
        train = [k for k in ys if k + 2 < t - window + 1]
        if len(train) < min_train:
            continue
        targets = np.array([ys[k] for k in train])
        vol = max(float(targets.std()), 1e-8)
        weights = {'buy_hold': 1.0, 'momentum': float(xs['levels'][t][2] > 0)}
        predictions = {}
        for kind in kinds:
            pred = fit_predict(np.array([xs[kind][k] for k in train]), targets, xs[kind][t], ridge)
            predictions[kind] = pred
            weights[kind] = float(np.clip(pred / vol, 0, 1))
        if 'supplied_baseline' in names:
            weights['supplied_baseline'] = float(rows[t]['baseline_weight'])
        for name, weight in weights.items():
            turn = abs(weight - drifted[name])
            gross = weight * ys[t]
            net = gross - turn * cost_bps / 10000
            if 1 + net <= 0:
                raise ValueError('Portfolio exhausted under selected cost assumptions')
            drifted[name] = weight * (1 + ys[t]) / (1 + gross)
            history[name].append({'decision_at': rows[t]['timestamp'],
                                  'execution_at': rows[t + 1]['timestamp'],
                                  'outcome_at': rows[t + 2]['timestamp'],
                                  'training_count': len(train),
                                  'last_training_outcome_at': rows[train[-1] + 2]['timestamp'],
                                  'weight': weight, 'gross_return': gross, 'net_return': net,
                                  'turnover': turn, 'predicted_return': predictions.get(name)})
    if not history['buy_hold']:
        raise ValueError('Insufficient history for window, purging, training and delayed execution')
    for name in names:
        last = history[name][-1]
        exit_cost = drifted[name] * cost_bps / 10000
        last['net_return'] = (1 + last['net_return']) * (1 - exit_cost) - 1
        last['turnover'] += drifted[name]
    config = {'window': window, 'min_train': min_train, 'ridge': ridge,
              'cost_bps': cost_bps, 'periods_per_year': periods_per_year,
              'execution_delay_bars': 1, 'position_bounds': [0, 1], 'cash_return': 0}
    return {'method': 'walk-forward-ridge-feature-comparison-v1', 'config': config,
            'config_sha256': digest(config), 'input_sha256': digest(rows),
            'summaries': {name: summarise(values, periods_per_year) for name, values in history.items()},
            'observations': history,
            'limitations': ['Experimental; no evidence of live profitability.',
                            'Caller must supply genuine point-in-time data and corporate-action-consistent prices.',
                            'One instrument; no portfolio correlation, market impact, funding or tax model.',
                            'Annualised metrics assume the declared sampling frequency.',
                            'This feature experiment is not the paper\'s direct Sig-Trading optimizer.']}


def summarise(values, frequency):
    returns = np.array([v['net_return'] for v in values])
    wealth = np.cumprod(1 + returns)
    highs = np.maximum.accumulate(np.r_[1.0, wealth])[1:]
    std = float(returns.std(ddof=1)) if len(returns) > 1 else 0
    return {'observations': len(values), 'net_total_return': float(wealth[-1] - 1),
            'max_drawdown': float(np.min(wealth / highs - 1)),
            'annualised_sharpe': float(returns.mean() / std * math.sqrt(frequency)) if std > 0 else None,
            'total_turnover': sum(v['turnover'] for v in values),
            'average_weight': sum(v['weight'] for v in values) / len(values)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv')
    parser.add_argument('--output', default='research-output/report.json')
    parser.add_argument('--window', type=int, default=21)
    parser.add_argument('--min-train', type=int, default=60)
    parser.add_argument('--cost-bps', type=float, default=10)
    parser.add_argument('--ridge', type=float, default=10)
    parser.add_argument('--periods-per-year', type=int, default=252)
    args = parser.parse_args()
    with open(args.csv, newline='', encoding='utf-8') as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        for key in ('price', 'growth', 'inflation', 'baseline_weight'):
            if key in row:
                row[key] = float(row[key]) if row[key] else None
    report = evaluate(rows, args.window, args.min_train, args.ridge, args.cost_bps, args.periods_per_year)
    atomic_json(args.output, report)
    print(args.output)


if __name__ == '__main__':
    main()
