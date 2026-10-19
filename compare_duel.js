/* Five declared financial rounds. Independent of InvestorAce model scoring. */
((root, factory) => {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.InvestorAceDuel = api;
})(globalThis, () => {
  'use strict';
  const ROUNDS = Object.freeze([
    Object.freeze({metric:'revenue_growth',label:'roundGrowth',direction:1,unit:'percent',digits:1}),
    Object.freeze({metric:'operating_margin',label:'roundProfit',direction:1,unit:'percent',digits:1}),
    Object.freeze({metric:'fcf_margin',label:'roundCash',direction:1,unit:'percent',digits:1}),
    Object.freeze({metric:'net_debt_ebitda',label:'roundDebt',direction:-1,unit:'multiple',digits:2}),
    Object.freeze({metric:'dilution',label:'roundDilution',direction:-1,unit:'percent',digits:1}),
  ]);
  const finite = value => typeof value === 'number' && Number.isFinite(value);
  const day = 86400000;
  const displayed = (value,digits) => Number(new Intl.NumberFormat('en-US',{
    useGrouping:false,minimumFractionDigits:digits,maximumFractionDigits:digits}).format(value));
  function date(value) {
    if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return NaN;
    const stamp=Date.parse(value+'T00:00:00Z');
    return Number.isFinite(stamp) && new Date(stamp).toISOString().slice(0,10)===value ? stamp : NaN;
  }
  function judge(a,b,{period=0,now=new Date().toISOString()}={}) {
    const asOf=Number.isFinite(Date.parse(now)) ? Date.parse(now) : Date.now();
    const fiscal=[a?.annual?.[period] ?? {}, b?.annual?.[period] ?? {}];
    const dates=fiscal.map(fy=>date(fy.period_end));
    const flags=[];
    [a,b].forEach((row,i)=>{
      const retrieved=Date.parse(row?.retrieved_at);
      if (retrieved>asOf+300000 || dates[i]>asOf) flags.push('FUTURE_DATA');
      if (!Number.isFinite(retrieved)) flags.push('SOURCE_TIME_UNKNOWN');
      else if (asOf-retrieved>14*day) flags.push('STALE_DATA');
      if (row?.status==='CACHED') flags.push('CACHED_DATA');
      if (period===0 && asOf-dates[i]>550*day) flags.push('OLD_FINANCIALS');
      if ((row?.warnings ?? []).some(w=>['SECURITY_TYPE_REVIEW','FINANCIAL_CURRENCY_UNKNOWN'].includes(w))) flags.push('DATA_REVIEW');
    });
    if (Number.isFinite(dates[0]) && Number.isFinite(dates[1]) && Math.abs(dates[0]-dates[1])>183*day) flags.push('PERIOD_MISMATCH');
    const usable=[a,b].map((row,i)=>Number.isFinite(dates[i]) && dates[i]<=asOf &&
      !(Date.parse(row?.retrieved_at)>asOf+300000));
    const rounds=ROUNDS.map(rule=>{
      const values=fiscal.map((fy,i)=>{
        let value=usable[i] ? fy[rule.metric] : null;
        if (rule.metric==='net_debt_ebitda' && !(finite(fy.ebitda) && fy.ebitda>0)) value=null;
        return finite(value) ? value : null;
      });
      let winner='missing';
      if (values.every(finite)) {
        const difference=(displayed(values[0],rule.digits)-displayed(values[1],rule.digits))*rule.direction;
        winner=difference===0 ? 'tie' : difference>0 ? 'a' : 'b';
      }
      return {...rule,left:values[0],right:values[1],winner};
    });
    const leftPoints=rounds.filter(r=>r.winner==='a').length;
    const rightPoints=rounds.filter(r=>r.winner==='b').length;
    const missing=rounds.filter(r=>r.winner==='missing').length;
    const tied=rounds.filter(r=>r.winner==='tie').length;
    const leader=leftPoints===rightPoints ? null : leftPoints>rightPoints ? 'a' : 'b';
    const same=!!(a?.ticker && a.ticker===b?.ticker);
    const uniqueFlags=[...new Set(flags)];
    const status=same ? 'SAME_STOCK' : !leader ? missing ? 'OPEN' : 'DRAW' :
      missing || uniqueFlags.length ? 'PROVISIONAL' : 'WINNER';
    const modelScores=[a?.model?.score,b?.model?.score];
    const validScores=modelScores.every(v=>finite(v) && v>=0 && v<=10);
    const modelDifference=validScores ? displayed(modelScores[0],2)-displayed(modelScores[1],2) : 0;
    const modelLeader=modelDifference===0 ? null : modelDifference>0 ? 'a' : 'b';
    let counterargument=null;
    if (leader && !same) {
      const other=leader==='a'?'b':'a';
      const lost=rounds.find(round=>round.winner===other);
      if (lost) counterargument={...lost,side:other,outsideRounds:false};
      else if (usable.every(Boolean)) {
        // A second leverage lens is shown as a counterargument, never as a bonus point.
        const values=fiscal.map(fy=>fy.debt_equity);
        if (values.every(v=>finite(v) && v>=0)) {
          const delta=displayed(values[0],2)-displayed(values[1],2);
          const better=delta===0?null:delta<0?'a':'b';
          if (better===other) counterargument={metric:'debt_equity',unit:'multiple',direction:-1,
            left:values[0],right:values[1],side:other,outsideRounds:true};
        }
      }
    }
    return {policy:'finance-duel-v1',status,rounds,leftPoints:same?0:leftPoints,
      rightPoints:same?0:rightPoints,missing,tied,leader:same?null:leader,
      winner:status==='WINNER'?leader:null,flags:uniqueFlags,counterargument,
      modelLeader,rankDisagreement:!!(!same && leader && modelLeader && leader!==modelLeader)};
  }
  return Object.freeze({ROUNDS,judge});
});
