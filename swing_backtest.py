"""Compare swing entries over InvestorAce's verified point-in-time archive."""
import argparse
import json
from datetime import datetime
from pathlib import Path

import codex_trading as trading
import evidence
import opportunity


def replay(history, through_build=None):
    builds = list(reversed(list(evidence.committed_builds(Path(history)))))
    if through_build is not None:
        index = next((i for i, build in enumerate(builds) if build['manifest']['run_id'] == through_build), None)
        if index is None:
            raise ValueError('Requested build is outside the verified archive')
        builds = builds[:index + 1]

    variants = {
        'opportunity_only': ('opportunity', None),
        'legacy_timing': ('timing', None),
        'confirmed_swing': ('timing', trading.SWING_ENTRY_POLICY),
    }
    ledgers = {}
    for variant, (account, _) in variants.items():
        ledger = trading.fresh()
        ledger['accounts'] = {account: ledger['accounts'][account]}
        ledgers[variant] = ledger

    if not builds:
        raise ValueError('No verified builds')
    price_build = builds[-1]
    price_evidence = price_build['record']['_evidence']['macro']['pulse']
    price_fields = {k: price_evidence[k] for k in ('tracked', 'paper_returns', 'paper_eurusd')}
    eligible_builds = 0
    for build in builds:
        record = build['record']
        captured = datetime.fromisoformat(record['_evidence']['captured_at'])
        if not any((row.get('opportunity') or {}).get('schema') == opportunity.VERSION
                   for ticker, row in record.items() if not ticker.startswith('_')):
            continue
        eligible_builds += 1
        # Only execution prices are taken from the latest verified archive.
        # advance() truncates those series at the completed decision session.
        inputs = record['_evidence']
        macro = inputs.get('macro') or {}
        pulse = {**(macro.get('pulse') or {}), **price_fields}
        replay_record = {**record, '_evidence': {**inputs, 'macro': {**macro, 'pulse': pulse}}}
        observation = {**build, 'record': replay_record}
        for variant, (_, policy) in variants.items():
            trading.advance(ledgers[variant], observation, captured, entry_policy=policy, include_exit_experiment=False)

    return price_build, price_fields, len(builds), eligible_builds, variants, ledgers


def compare(history, through_build=None):
    price_build, _, build_count, eligible_builds, variants, ledgers = replay(history, through_build)
    timeline = ledgers['confirmed_swing']['decisions']
    summary = {}
    for variant, (account, _) in variants.items():
        ledger = ledgers[variant]
        orders = ledger['accounts'][account]['orders']
        buys = [order for order in orders if order['side'] == 'Buy']
        sells = [order for order in orders if order['side'] == 'Sell']
        marked = [d['outcomes'][account]['equity'] for d in ledger['decisions']]
        fills = sum(o['status'] == 'Filled' for o in buys)
        summary[variant] = dict(
            buy_signals=len(buys), buy_fills=fills, sell_fills=sum(o['status'] == 'Filled' for o in sells),
            sessions_with_mark_gaps=marked.count(None),
            ending_return_pct=round(100 * (marked[-1] / trading.CAPITAL - 1), 4)
            if fills and marked and marked[-1] is not None else None,
        )
    legacy_orders = ledgers['legacy_timing']['accounts']['timing']['orders']
    confirmed_orders = ledgers['confirmed_swing']['accounts']['timing']['orders']
    same_timing_orders = legacy_orders == [
        {key: value for key, value in order.items() if key != 'entry_policy'}
        for order in confirmed_orders
    ]
    return dict(
        same_timing_orders=same_timing_orders, price_build=price_build['manifest']['run_id'], builds_reviewed=build_count,
        eligible_signal_builds=eligible_builds, eligible_sessions=len(timeline),
        market_uptrend_sessions=sum(d['market'] == 'UPTREND' for d in timeline),
        first_session=timeline[0]['session'] if timeline else None,
        last_session=timeline[-1]['session'] if timeline else None,
        variants=summary,
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('history', nargs='?', type=Path, default=Path('history'))
    parser.add_argument('--through-build', help='Use this archived build as the last observation')
    args = parser.parse_args()
    print(json.dumps(compare(args.history, args.through_build), indent=2))
