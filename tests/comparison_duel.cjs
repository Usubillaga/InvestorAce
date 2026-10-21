// Deterministic financial rounds. Run with: node tests/comparison_duel.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const source = path.resolve(__dirname,'../compare_duel.js');
assert.ok(fs.existsSync(source),'The comparison does not yet have an explainable duel judge');
const {judge,ROUNDS} = require(source);
const now='2026-10-19T13:54:00Z';
function row(ticker, values={}) {
  return {ticker,retrieved_at:now,financial_currency:'USD',status:'OK',warnings:[],
    annual:[{period_end:'2025-12-31',revenue_growth:10,operating_margin:20,
      fcf_margin:15,net_debt_ebitda:2,dilution:1,ebitda:100,debt_equity:1,...values}]};
}
const evaluate = (a,b,options={}) => judge(a,b,{now,...options});
const reviewedModel = score => ({score, assessment_schema:'assessment-v1',
  quality_rank_eligible:true, review_required:false, assessed_at:now,
  expires_at:'2026-10-20T13:54:00Z'});

test('unreviewed legacy totals cannot win the current model comparison',()=>{
  const a=row('A',{revenue_growth:20}),b=row('B');
  a.model={score:9.8,score_status:'PUBLISHED_TOTAL',review_required:true};
  b.model={score:7.5,review_required:true};
  const result=evaluate(a,b);
  assert.equal(result.winner,'a');
  assert.equal(result.modelLeader,null);
  assert.equal(result.rankDisagreement,false);
});

test('the winner follows five named financial rounds and explains every point',()=>{
  const result=evaluate(row('A',{revenue_growth:20,operating_margin:30,fcf_margin:25}),
    row('B',{net_debt_ebitda:1,dilution:-2}));
  assert.equal(ROUNDS.length,5);
  assert.equal(result.status,'WINNER');
  assert.equal(result.winner,'a');
  assert.equal(result.leftPoints,3);
  assert.equal(result.rightPoints,2);
  assert.equal(result.rounds.filter(r=>r.winner==='a').length,3);
  assert.ok(result.counterargument && result.counterargument.side==='b');
});
test('size, quote currency, float, regime and model score do not award fight points',()=>{
  const a=row('A'), b=row('B');
  a.annual[0].revenue=1e12;b.annual[0].revenue=100;
  a.market={float_pct:100};a.regime_fit=100;a.model={score:10};
  b.financial_currency='EUR';b.model={score:1};
  const result=evaluate(a,b);
  assert.equal(result.status,'DRAW');
  assert.equal(result.winner,null);
  assert.equal(result.leftPoints,0);
});
test('less dilution and lower net debt to positive EBITDA win their rounds',()=>{
  const result=evaluate(row('A',{dilution:-3,net_debt_ebitda:-1}),row('B'));
  assert.equal(result.rounds.find(r=>r.metric==='dilution').winner,'a');
  assert.equal(result.rounds.find(r=>r.metric==='net_debt_ebitda').winner,'a');
});
test('missing figures are neither zero nor a loss',()=>{
  const result=evaluate(row('A',{revenue_growth:20,fcf_margin:null}),row('B'));
  assert.equal(result.leftPoints,1);
  assert.equal(result.rightPoints,0);
  assert.equal(result.missing,1);
  assert.equal(result.status,'PROVISIONAL');
  assert.equal(result.winner,null);
  assert.equal(result.leader,'a');
});
test('booleans, strings, infinity and negative EBITDA cannot create a win',()=>{
  const result=evaluate(row('A',{revenue_growth:true,operating_margin:'30',fcf_margin:Infinity,
    ebitda:-100,net_debt_ebitda:-5,dilution:NaN}),row('B'));
  assert.equal(result.missing,5);
  assert.equal(result.status,'OPEN');
  assert.equal(result.winner,null);
});
test('swapping the fighters mirrors the result without changing the verdict',()=>{
  const a=row('A',{revenue_growth:15,operating_margin:30}),b=row('B');
  const first=evaluate(a,b),second=evaluate(b,a);
  assert.equal(first.winner,'a');assert.equal(second.winner,'b');
  assert.equal(first.leftPoints,second.rightPoints);
  assert.equal(first.status,second.status);
});
test('choosing another fiscal year changes the fight rather than the model score',()=>{
  const a=row('A',{revenue_growth:20}),b=row('B');
  a.annual.push({...a.annual[0],period_end:'2024-12-31',revenue_growth:5});
  b.annual.push({...b.annual[0],period_end:'2024-12-31',revenue_growth:25});
  a.model=reviewedModel(8);b.model=reviewedModel(6);
  assert.equal(evaluate(a,b).winner,'a');
  const past=evaluate(a,b,{period:1});
  assert.equal(past.winner,'b');
  assert.equal(past.rankDisagreement,true);
});
test('near-equal displayed percentages and multiples count as round draws',()=>{
  const result=evaluate(row('A',{revenue_growth:10.01,net_debt_ebitda:2.001}),row('B'));
  assert.equal(result.status,'DRAW');
  assert.equal(result.tied,5);
});
test('different year ends beyond 183 days qualify the leader as provisional',()=>{
  const a=row('A',{revenue_growth:20,period_end:'2026-07-31'}),b=row('B');
  const result=evaluate(a,b);
  assert.equal(result.status,'PROVISIONAL');
  assert.ok(result.flags.includes('PERIOD_MISMATCH'));
  assert.equal(result.winner,null);
});
test('stale and failed refresh data qualify the leader, without adding penalties',()=>{
  const a=row('A',{revenue_growth:20});a.retrieved_at='2026-09-01T00:00:00Z';
  const stale=evaluate(a,row('B'));
  assert.equal(stale.status,'PROVISIONAL');assert.equal(stale.leftPoints,1);
  assert.ok(stale.flags.includes('STALE_DATA'));
  a.retrieved_at=now;a.status='CACHED';
  assert.ok(evaluate(a,row('B')).flags.includes('CACHED_DATA'));
});
test('the same stock cannot defeat itself',()=>{
  const result=evaluate(row('A',{revenue_growth:20}),row('A'));
  assert.equal(result.status,'SAME_STOCK');assert.equal(result.winner,null);
});
test('an outside-round balance-sheet advantage remains visible for the loser',()=>{
  const result=evaluate(row('A',{revenue_growth:20,operating_margin:30,fcf_margin:25,
    net_debt_ebitda:1,dilution:-3,debt_equity:6}),row('B',{debt_equity:.4}));
  assert.equal(result.leftPoints,5);
  assert.equal(result.counterargument.metric,'debt_equity');
  assert.equal(result.counterargument.side,'b');
  assert.equal(result.counterargument.outsideRounds,true);
});
test('judging never mutates either stock, financial period or model score',()=>{
  const a=row('A',{revenue_growth:20}),b=row('B');
  a.model=reviewedModel(5);b.model=reviewedModel(9);
  const before=JSON.stringify([a,b]);
  assert.equal(evaluate(a,b).rankDisagreement,true);
  assert.equal(JSON.stringify([a,b]),before);
});
