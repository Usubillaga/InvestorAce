/* Read-only adapters for the two independent paper journals. */
const PaperModel = (() => {
  const COST = 0.001;
  function rowsBySymbol(legs) {
    const grouped = new Map();
    for (const leg of legs) {
      if (leg.side !== 'leader') continue;
      const row = grouped.get(leg.symbol) || {symbol:leg.symbol, units:0, basis:0, value:0};
      row.units += leg.entry_units;
      row.basis += leg.entry_price * leg.entry_units;
      row.value += leg.value;
      grouped.set(leg.symbol, row);
    }
    return [...grouped.values()].map(row => ({
      symbol:row.symbol, units:row.units, price:row.basis / row.units,
      cost:row.basis * (1 + COST), value:row.value
    })).sort((a,b) => b.value - a.value);
  }

  function original(state) {
    const events = [];
    // The sell ledger retains both the original buy and closed legs.
    for (const trade of state.history) {
      events.push({day:trade.entry, status:'bought', order:trade.buy},
                  {day:trade.exit, status:'sold', order:trade.sell, symbols:rowsBySymbol(trade.legs).map(r => r.symbol)});
    }
    if (state.position) events.push({day:state.position.entry, status:'bought', order:state.position.order});
    const holdings = rowsBySymbol(state.position?.legs || []);
    return {key:'original', initial:state.initial, nav:state.equity, cash:state.cash,
      asOf:state.as_of, entry:state.position?.entry, pending:state.pending, holdings, events,
      controls:{'SPY + QQQ + DIA':state.benchmark}, warnings:state.warnings || [], missed:state.skipped || []};
  }

  function concentrated(state, size) {
    const book = state.books[size];
    return {key:String(size), size, initial:10_000, nav:book.nav, cash:book.cash, asOf:state.as_of,
      start:state.started, entry:book.entry, eligible:book.eligible, pending:book.pending,
      holdings:book.holdings.map(h => ({...h,cost:h.price*h.units*(1+COST)})),
      events:book.events, controls:book.controls, warnings:state.warnings || [], missed:state.missed_checks || []};
  }

  function latestReading(legacy, overlap) {
    return [legacy?.intraday_monitor, legacy?.monitor, overlap?.monitor]
      .filter(s => s && Number.isFinite(s.heat) && Number.isFinite(Date.parse(s.as_of)))
      .sort((a,b) => Date.parse(b.as_of) - Date.parse(a.as_of))[0] || null;
  }

  function audit(event) {
    const order = event.order;
    const picks = event.fills || order.picks || order.leaders || [];
    return {day:event.day, status:event.status, dayOfSignal:order.signal?.day || order.signal_day,
      signalTime:order.signal?.as_of || order.observed_at, heat:order.signal?.heat ?? order.heat,
      submitted:order.submitted, target:order.target, source:order.signal?.url || order.source,
      symbols:event.symbols || [...new Set(picks.map(x => x.symbol))]};
  }

  return {original, concentrated, latestReading, audit};
})();
if (typeof module !== 'undefined') module.exports = PaperModel;
