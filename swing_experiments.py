"""Research-only pilot. Replay identical swing fills and monitor a preselected pair."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from hashlib import sha256
from html import escape
import json
import logging
import re
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

import codex_trading as trading
from integrity import atomic_json
from war_scenario import shell
from swing_backtest import replay

SCHEMA = 'swing-experiments-v1'
REPORT = Path('history/swing_experiments.json')
PAIR = ('AR', 'CNX')
PAIR_START = '2022-01-01'
PAIR_SPLIT = '2025-01-01'
SIZE = .12
RISK_NAV = .12 * .08
LOOKBACK = 252
MIN_GAPS = 126
PAIR_HORIZON = 20


def yahoo_daily(symbol, end):
    start_epoch = int(datetime.fromisoformat(PAIR_START).replace(tzinfo=timezone.utc).timestamp())
    end_epoch = int(datetime.fromisoformat(end).replace(tzinfo=timezone.utc).timestamp()) + 86400
    url = (f'https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol, safe="")}'
           f'?period1={start_epoch}&period2={end_epoch}&interval=1d')
    with urlopen(Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=15) as response:
        results = json.load(response)['chart']['result']
    result = results[0]
    exchange = ZoneInfo(result['meta']['exchangeTimezoneName'])
    days = [datetime.fromtimestamp(t, exchange).date().isoformat() for t in result['timestamp']]
    bars = result['indicators']['quote'][0]
    adjusted = result['indicators']['adjclose'][0]['adjclose']
    df = pd.DataFrame({'open': bars['open'], 'close': bars['close'], 'adj': adjusted}, index=days)
    df = df.loc[df.index <= end].sort_index()
    if not df.index.is_unique or df.empty:
        raise ValueError(f'Missing or duplicate daily bars for {symbol}')
    df = df.where(np.isfinite(df) & df.gt(0))
    df['adjusted_open'] = df['open'] * df['adj'] / df['close']
    gaps = (df['adjusted_open'] / df['adj'].shift(1) - 1).replace([np.inf, -np.inf], np.nan)
    # A provider omission must not turn a multi-session return into an overnight gap.
    calendar = np.busday_count(df.index.values[:-1].astype('datetime64[D]'),
                               df.index.values[1:].astype('datetime64[D]'))
    # Older gaps cannot be stitched across several weekdays. Single exchange holidays
    # can also be excluded conservatively. Friday to Monday counts as one weekday.
    gaps.iloc[1:] = gaps.iloc[1:].where(calendar == 1)
    return pd.DataFrame({'adj': df['adj'], 'gap': gaps,
                         'previous': df.index.to_series().shift(1)})


def gap_size(gaps, decision_day):
    history = gaps.loc[gaps.index < decision_day].dropna().tail(LOOKBACK)
    if len(history) < MIN_GAPS:
        return SIZE, None
    loss = max(0., -float(history.quantile(.01)))
    return min(SIZE, RISK_NAV / loss) if loss > 0 else SIZE, loss


def size_trial(ledger, price, daily, use_cap):
    events = {}
    for order in ledger['accounts']['timing']['orders']:
        if order['status'] == 'Filled':
            events.setdefault(order['day'], []).append(order)
    first, last = (ledger['decisions'][i]['session'] for i in (0, -1))
    sessions = sorted(d for d, _ in price['tracked']['^GSPC'] if first <= d <= last)
    fx = dict(price['paper_eurusd'])
    bars = {symbol: {d: (previous, rel) for d, previous, rel, _ in observations}
            for symbol, observations in price['paper_returns'].items()}
    cash, nav = trading.CAPITAL, trading.CAPITAL
    held, curve, opening_losses, entries = {}, [nav], [], []
    equity_at, incomplete_marks = {}, 0
    decisions = {d['at']: d['session'] for d in ledger['decisions']}
    for day in sessions:
        if held and all(day in daily[p['symbol']].index
                        and pd.notna(daily[p['symbol']].at[day, 'gap'])
                        and daily[p['symbol']].at[day, 'previous'] == p['day'] for p in held.values()):
            overnight = sum(p['local'] / p['rate'] * daily[p['symbol']].at[day, 'gap'] for p in held.values())
            opening_losses.append(100 * overnight / nav)

        for p in held.values():
            bar = bars[p['symbol']].get(day)
            if bar and bar[0] == p['day']:
                p.update(local=p['local'] * bar[1], day=day)
            if p['currency'] == 'EUR':
                p['rate'] = 1.
            elif day in fx:
                p['rate'] = fx[day]
        incomplete_marks += int(any(p['day'] != day or (p['currency'] == 'USD' and day not in fx)
                                    for p in held.values()))
        nav = cash + sum(p['local'] / p['rate'] for p in held.values())

        for o in events.get(day, []):
            t = o['ticker']
            if o['side'] == 'Sell':
                p = held.pop(t)
                cash += p['local'] / p['rate'] * (1 - trading.COST)
                continue
            cap, loss = gap_size(daily[o['symbol']]['gap'], o['submitted'][:10])
            weight = cap if use_cap else SIZE
            entries.append((weight, loss))
            # Both arms use the same entry and exit decisions and execution dates.
            # Control orders preserve their original decision-time euro budget.
            decision_day = decisions[o['submitted']]
            value = equity_at[decision_day] * weight if use_cap else o['euros']
            if value * (1 + trading.COST) > cash + 1e-8:
                raise ValueError('Matched-fill comparison would exceed available cash')
            cash -= value * (1 + trading.COST)
            rate = float(o['fx'])
            held[t] = dict(symbol=o['symbol'], local=value * rate, rate=rate, currency=o['currency'], day=day)
        nav = cash + sum(p['local'] / p['rate'] for p in held.values())
        curve.append(nav)
        equity_at[day] = nav
    peak = np.maximum.accumulate(curve)
    return dict(ending_pct=round(100 * (curve[-1] / trading.CAPITAL - 1), 4),
                max_drawdown_pct=round(100 * float(np.min(curve / peak - 1)), 4),
                incomplete_marks=incomplete_marks, buys=len(entries), capped=sum(weight < SIZE for weight, _ in entries),
                sizing_coverage=sum(loss is not None for _, loss in entries),
                max_weight_pct=round(100 * max((w for w, _ in entries), default=0), 4),
                worst_observed_open_pct=round(min(opening_losses), 4) if opening_losses else None,
                observed_opens=len(opening_losses))


def pair_trial(daily):
    from statsmodels.tsa.stattools import adfuller, coint

    log = np.log(pd.concat({s: daily[s]['adj'] for s in PAIR}, axis=1).dropna())
    train = log.loc[log.index < PAIR_SPLIT]
    test = log.loc[log.index >= PAIR_SPLIT]
    if len(train) < 252 or len(test) < 253:
        raise ValueError('Insufficient aligned pair observations')
    y, x = train.iloc[:, 0], train.iloc[:, 1]
    _, p_value, _ = coint(y, x, trend='c', autolag='aic')
    slope, intercept = np.polyfit(x, y, 1)
    residual = y - intercept - slope * x
    phi = float(np.polyfit(residual.iloc[:-1].values, residual.iloc[1:].values, 1)[0])
    half_life = -np.log(2) / np.log(phi) if 0 < phi < 1 else None
    std = residual.std(ddof=1)
    if not np.isfinite(std) or std <= 0:
        raise ValueError('Degenerate calibration spread')
    z = (test.iloc[:, 0] - intercept - slope * test.iloc[:, 1] - residual.mean()) / std
    _, recent_p, _ = coint(log.iloc[-253:-1, 0], log.iloc[-253:-1, 1], trend='c', autolag='aic')
    i1_compatible = all(adfuller(values)[1] >= .05 and adfuller(values.diff().dropna())[1] < .05
                        for values in (y, x))
    supported = i1_compatible and p_value < .05 and slope > 0 and half_life is not None and half_life <= PAIR_HORIZON
    events, reverted, next_idx = 0, 0, 1
    if supported:
        for i in range(1, len(z) - PAIR_HORIZON):
            if i < next_idx or not abs(z.iloc[i-1]) < 2 <= abs(z.iloc[i]):
                continue
            events += 1
            future = z.iloc[i+1:i+1+PAIR_HORIZON]
            reverted += int(any(abs(v) <= .5 or v * z.iloc[i] <= 0 for v in future))
            next_idx = i + PAIR_HORIZON + 1
    if not supported or recent_p >= .05:
        status = 'UNSUPPORTED'
    else:
        status = 'DIVERGENCE' if abs(z.iloc[-1]) >= 2 else 'NEUTRAL'
    return dict(symbols=list(PAIR), status=status, i1_compatible=i1_compatible, as_of=z.index[-1], z=round(float(z.iloc[-1]), 4),
                beta=round(float(slope), 4), train_p=round(float(p_value), 4), recent_p=round(float(recent_p), 4),
                half_life=round(float(half_life), 2) if half_life is not None else None,
                train_days=len(train), test_days=len(test), training_end=train.index[-1], test_start=test.index[0],
                events=events if supported else None, reverted_within_20=reverted if supported else None)


def experiment(history, through_build=None):
    build, price, _, _, _, ledgers = replay(history, through_build)
    ledger = ledgers['confirmed_swing']
    sessions = ledger['decisions']
    if not sessions:
        raise ValueError('No archived swing sessions')
    last = sessions[-1]['session']
    symbols = set(PAIR) | {o['symbol'] for o in ledger['accounts']['timing']['orders'] if o['status'] == 'Filled'}
    with ThreadPoolExecutor(max_workers=8) as pool:
        daily = dict(zip(sorted(symbols), pool.map(yahoo_daily, sorted(symbols), [last] * len(symbols))))
    control = size_trial(ledger, price, daily, use_cap=False)
    capped = size_trial(ledger, price, daily, use_cap=True)
    expected = sessions[-1]['outcomes']['timing']['equity']
    if expected is None or abs(control['ending_pct'] - 100 * (expected / trading.CAPITAL - 1)) > .000051:
        raise ValueError('Control portfolio does not reconcile to the archived swing replay')
    pair = pair_trial(daily)
    if pair['as_of'] != last:
        raise ValueError('The pair lacks a common close in the latest archived session')
    return dict(schema=SCHEMA, as_of=last, first_session=sessions[0]['session'], session_count=len(sessions),
                archive_build=build['manifest']['run_id'], price_source='Yahoo Finance adjusted daily OHLC',
                source_hashes={s: sha256(frame.to_csv().encode()).hexdigest() for s, frame in sorted(daily.items())},
                gap=dict(control=control, capped=capped,
                         scenarios=[dict(asset_drop_pct=drop, control_loss_pct=round(drop*SIZE, 4),
                                         capped_loss_pct=round(drop*capped['max_weight_pct']/100, 4))
                                    for drop in (10, 15, 25)]), pair=pair)


PAGES = {'en': 'swing-experiments.html', 'de': 'swing-experiments.de.html', 'es': 'swing-experiments.es.html'}
TEXT = {
    'en': dict(
        title='Swing experiments', fixed='Fixed size 12%', capped='Size capped by gaps',
        cols=('Variant', 'Buys', 'Cuts', 'Return EUR', 'Max drawdown', 'Worst opening gap', 'Opens observed',
              'Incomplete closes'),
        scen_cols=('Asset drop', 'Loss with fixed size', 'Loss with larger adjusted size'),
        status={'UNSUPPORTED': 'Insufficient cointegration', 'NEUTRAL': 'No divergence',
                'DIVERGENCE': 'Divergence to review'},
        pair_cols=('Pair', 'Status', 'Z', 'Training p', 'Recent p', 'Estimated half-life'),
        intro='Paper research. Cut-off {day} · {n} comparable swing sessions.', build='Reference build',
        gap_h='Gap risk and position size',
        gap_p=('Sizing history available for {k} buys. Same entry, exit and cost per fill. The experimental cap uses '
               'the adverse 1% percentile of up to 252 previous gaps (minimum 126). The loss budget is 0.96% of '
               'equity and the position cap is 12%. Opening measurements exclude overnight FX and days with '
               'incomplete data. The close valuation carries the last price forward when a quote is missing.'),
        scen_h='Single-position scenarios', scen_p='Hypothetical jumps without assigned probabilities and without extra costs.',
        pair_h='Pair watch · Engle–Granger and Ornstein–Uhlenbeck',
        pair_p=('Last common close {asof}. Training up to {tend} ({tdays} closes) and evaluation from {tstart} '
                '({edays} closes). Retrospective evaluation of a pair fixed for this study. The alert requires recent '
                'evidence of cointegration and an estimated half-life of up to 20 sessions.'),
        pair_note='The pair is a research alert. Swing entries follow InvestorAce\'s double confirmation.',
        data='Data and hashes', code='Reproducible code'),
    'de': dict(
        title='Swing-Experimente', fixed='Feste Größe 12 %', capped='Größe durch Gaps begrenzt',
        cols=('Variante', 'Käufe', 'Kürzungen', 'Rendite EUR', 'Max. Drawdown', 'Schlechtester Eröffnungsgap',
              'Beobachtete Eröffnungen', 'Unvollständige Schlusskurse'),
        scen_cols=('Kursrückgang', 'Verlust mit fester Größe', 'Verlust mit größerer angepasster Größe'),
        status={'UNSUPPORTED': 'Kointegration unzureichend', 'NEUTRAL': 'Keine Divergenz',
                'DIVERGENCE': 'Divergenz prüfen'},
        pair_cols=('Paar', 'Status', 'Z', 'p Training', 'p aktuell', 'Geschätzte Halbwertszeit'),
        intro='Papierforschung. Stichtag {day} · {n} vergleichbare Swing-Sitzungen.', build='Referenz-Build',
        gap_h='Gap-Risiko und Positionsgröße',
        gap_p=('Größenhistorie für {k} Käufe verfügbar. Gleicher Einstieg, Ausstieg und gleiche Kosten je Ausführung. '
               'Die experimentelle Grenze nutzt das ungünstige 1-%-Perzentil von bis zu 252 früheren Gaps (mindestens '
               '126). Das Verlustbudget beträgt 0,96 % des Kapitals, die Positionsgrenze 12 %. Die Eröffnungsmessung '
               'schließt Devisenbewegungen über Nacht und Tage mit unvollständigen Daten aus. Fehlt ein Kurs, wird '
               'der letzte Schlusskurs fortgeschrieben.'),
        scen_h='Szenarien für eine einzelne Position',
        scen_p='Hypothetische Kurssprünge ohne zugewiesene Wahrscheinlichkeiten und ohne zusätzliche Kosten.',
        pair_h='Paarbeobachtung · Engle–Granger und Ornstein–Uhlenbeck',
        pair_p=('Letzter gemeinsamer Schlusskurs {asof}. Training bis {tend} ({tdays} Schlusskurse), Auswertung ab '
                '{tstart} ({edays} Schlusskurse). Rückblickende Auswertung eines für diese Studie festgelegten Paars. '
                'Der Alarm verlangt aktuelle Belege für Kointegration und eine geschätzte Halbwertszeit von höchstens '
                '20 Sitzungen.'),
        pair_note='Das Paar ist ein Forschungsalarm. Swing-Einstiege folgen der doppelten Bestätigung von InvestorAce.',
        data='Daten und Hashes', code='Reproduzierbarer Code'),
    'es': dict(
        title='Experimentos de swing', fixed='Tamaño fijo 12 %', capped='Tamaño limitado por gaps',
        cols=('Variante', 'Compras', 'Recortes', 'Rendimiento EUR', 'Caída máxima', 'Peor gap de apertura',
              'Aperturas observadas', 'Cierres incompletos'),
        scen_cols=('Caída del activo', 'Pérdida con tamaño fijo', 'Pérdida con mayor tamaño ajustado'),
        status={'UNSUPPORTED': 'Cointegración insuficiente', 'NEUTRAL': 'Sin divergencia',
                'DIVERGENCE': 'Divergencia para revisar'},
        pair_cols=('Par', 'Estado', 'Z', 'p de formación', 'p reciente', 'Semivida estimada'),
        intro='Investigación en papel. Corte al {day} · {n} sesiones de swing comparables.', build='Build de referencia',
        gap_h='Riesgo de gaps y tamaño de posición',
        gap_p=('Histórico de sizing disponible para {k} compras. Misma entrada, salida y coste por ejecución. '
               'El límite experimental usa el percentil adverso del 1 % de hasta 252 gaps anteriores (mínimo de 126). '
               'El presupuesto de pérdida es 0,96 % del patrimonio y el tope de posición es 12 %. '
               'La medición de aperturas excluye FX nocturno y días con datos incompletos. La valoración al cierre '
               'arrastra el último precio cuando falta una cotización.'),
        scen_h='Escenarios de una sola posición', scen_p='Saltos hipotéticos sin probabilidades asignadas y sin costes adicionales.',
        pair_h='Vigilancia de pares · Engle–Granger y Ornstein–Uhlenbeck',
        pair_p=('Último cierre común {asof}. Formación hasta {tend} ({tdays} cierres) y evaluación desde {tstart} '
                '({edays} cierres). Evaluación retrospectiva de un par fijado para este estudio. La alerta exige '
                'evidencia reciente de cointegración y una semivida estimada de hasta 20 sesiones.'),
        pair_note='El par es una alerta de investigación. Las entradas de swing se rigen por la doble confirmación de InvestorAce.',
        data='Datos y hashes', code='Código reproducible'),
}


def render(report, report_day, lang):
    """One language edition; numbers are identical in every edition."""
    t = TEXT[lang]

    def pct(value):
        return '—' if value is None else (f'{value:+.2f} %' if lang == 'en' else f'{value:+.2f} %'.replace('.', ','))

    def num(value, digits=2):
        return f'{value:.{digits}f}' if lang == 'en' else f'{value:.{digits}f}'.replace('.', ',')

    gap = report['gap']
    rows = [(label, v['buys'], v['capped'], pct(v['ending_pct']), pct(v['max_drawdown_pct']),
             pct(v['worst_observed_open_pct']), v['observed_opens'], v['incomplete_marks'])
            for label, v in [(t['fixed'], gap['control']), (t['capped'], gap['capped'])]]
    sample = trading.table(t['cols'], rows)
    scenarios = trading.table(t['scen_cols'], [(f"−{x['asset_drop_pct']} %", f"−{num(x['control_loss_pct'])} %",
                                                f"−{num(x['capped_loss_pct'])} %") for x in gap['scenarios']])
    pair = report['pair']
    pair_rows = trading.table(t['pair_cols'], [(' / '.join(pair['symbols']), t['status'][pair['status']], pair['z'],
                                                pair['train_p'], pair['recent_p'],
                                                pair['half_life'] if pair['half_life'] is not None else '—')])
    switch = ' · '.join(f'<a href="{PAGES[code]}" lang="{code}"' + (' aria-current="page"' if code == lang else '')
                        + f'>{name}</a>' for code, name in (('en', 'English'), ('de', 'Deutsch'), ('es', 'Español')))
    body = (f'<p>{switch}</p><h1>{escape(t["title"])}</h1><p>'
            + escape(t['intro'].format(day=report_day.isoformat(), n=int(report['session_count'])))
            + f' <a href="https://github.com/Usubillaga/InvestorAce/tree/main/history/_builds/{report["archive_build"]}">'
            f'{escape(t["build"])}</a>.</p><h2>{escape(t["gap_h"])}</h2>' + sample
            + '<p>' + escape(t['gap_p'].format(k=int(gap['capped']['sizing_coverage']))) + '</p>'
            f'<h3>{escape(t["scen_h"])}</h3>' + scenarios + f'<p>{escape(t["scen_p"])}</p>'
            f'<h2>{escape(t["pair_h"])}</h2>' + pair_rows
            + '<p>' + escape(t['pair_p'].format(asof=pair['as_of'], tend=pair['training_end'], tdays=int(pair['train_days']),
                                                tstart=pair['test_start'], edays=int(pair['test_days']))) + '</p>'
            f'<p>{escape(t["pair_note"])}</p>'
            f'<p><a href="swing-experiments.json">{escape(t["data"])}</a> · '
            f'<a href="https://github.com/Usubillaga/InvestorAce/blob/main/swing_experiments.py">{escape(t["code"])}</a></p>')
    html = shell(t['title'], body)
    return html if lang == 'en' else html.replace('lang="en"', f'lang="{lang}"', 1)


def site_pages(root):
    """Render the last complete result even if the latest data refresh failed."""
    try:
        report = json.loads((Path(root) / REPORT).read_text(encoding='utf-8'))
        if report['schema'] != SCHEMA or not re.fullmatch(r'[0-9]{8}T[0-9]{12}-[a-f0-9]{32}', report['archive_build']):
            return []
        manifest = Path(root) / 'history' / '_builds' / report['archive_build'] / 'manifest.json'
        if not manifest.is_file():
            return []
        report_day = date.fromisoformat(report['as_of'])
        pages = [(Path(PAGES[lang]), render(report, report_day, lang)) for lang in PAGES]
        json_page = json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2)
        return pages + [(Path('swing-experiments.json'), json_page)]
    except (OSError, TypeError, ValueError, KeyError, AttributeError) as err:
        if not isinstance(err, FileNotFoundError):
            logging.warning('Optional swing experiment report unavailable: %s', err)
        return []


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--through-build', help='Pin the archived reference build')
    args = parser.parse_args()
    result = experiment(args.root / 'history', args.through_build)
    atomic_json(args.root / REPORT, result)
    print(f"{result['session_count']} matched swing sessions; pair {result['pair']['status']} "
          f"as of {result['as_of']}")


if __name__ == '__main__':
    main()
