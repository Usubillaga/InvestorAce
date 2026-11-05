const assert=require('node:assert/strict');
const {test}=require('node:test');
const view=require('../assessment_view.js');
const frozen=()=>({schema:'opportunity-v17.1',as_of:'2026-10-28T10:00:00Z',
  price:60,quote_observed_at:'2026-10-27T16:35:03Z',financial_period:'2026-06-30',
  quote_status:'DATED',score:7.92,label:'Buy',score_lower:7.92,score_upper:7.92,
  review_status:'REVIEW_REQUIRED',profile:{tags:['DEFENSIVE','QUALITY','VALUE']},
  current_fit:52,current_fit_bounds:[52,52],regime_fit:{REFLATION:52},
  regime_fit_bounds:{REFLATION:[52,52]},metrics:{valuation_pe:12,fcf_yield_pct:8,operating_margin_pct:35},
  components:[{key:'pe',value:9,contribution:.9},{key:'p',value:9,contribution:1.08}],
  implied_growth_pct:-5});

test('manual review pending leaves a fresh automatic Buy visible',()=>{
  assert.equal(typeof view.projectOpportunity,'function','Automatic opportunity projection is missing');
  const result=view.projectOpportunity(frozen(),{now:'2026-10-28T12:00:00Z'});
  assert.equal(result.label,'Buy');assert.equal(result.review_status,'REVIEW_REQUIRED');
});
test('quote expiry withdraws label, interval, valuation metrics and regime matrix',()=>{
  const source=frozen();
  const result=view.projectOpportunity(source,{now:'2026-10-31T16:35:04Z'});
  for(const key of ['label','score','score_lower','score_upper','current_fit','implied_growth_pct']) assert.equal(result[key],null,key);
  assert.equal(result.metrics.valuation_pe,undefined);assert.deepEqual(result.regime_fit,{});
  assert.equal(result.components[0].contribution,null);
  assert.equal(result.components[1].contribution,1.08);
  assert.deepEqual(result.profile.tags,['DEFENSIVE','QUALITY']);
  assert.equal(source.label,'Buy');
});
test('unknown/future quote time and future capture cannot carry current labels',()=>{
  for(const changes of [{quote_observed_at:'2026-10-27'},
      {quote_observed_at:'2026-10-29T20:00:00Z'},{as_of:'2026-10-29T20:00:00Z'}]) {
    assert.equal(view.projectOpportunity({...frozen(),...changes},{now:'2026-10-28T12:00:00Z'}).label,null);
  }
});
test('the fiscal age deadline withdraws a signal even with a fresh quote',()=>{
  const source={...frozen(),financial_period:'2025-04-26'};
  assert.equal(view.projectOpportunity(source,{now:'2026-10-28T12:00:00Z'}).label,'Buy');
  assert.equal(view.projectOpportunity(source,{now:'2026-10-29T12:00:00Z'}).label,null);
});
test('a concrete valuation input conflict cannot revive an old Buy packet',()=>{
  const source={...frozen(),schema:'opportunity-v18.1',
    valuation_input_conflicts:[{code:'COMMON_EQUITY_CLAIMS_OMITTED',reason:'Preferred claims missing'}]};
  const result=view.projectOpportunity(source,{now:'2026-10-28T12:00:00Z'});
  for(const key of ['label','score','score_lower','score_upper','implied_growth_pct']) assert.equal(result[key],null,key);
  assert.equal(result.status,'BLOCKED_INPUTS');
  assert.equal(result.metrics.valuation_pe,undefined);
  assert.equal(source.label,'Buy');
});
test('conflicted cached valuation breakdowns cannot retain old exact values',()=>{
  const source={...frozen(),schema:'opportunity-v18.1',valuation_bounds:[9,9],
    valuation_input_conflicts:[{code:'COMMON_EQUITY_CLAIMS_OMITTED',reason:'Preferred claims missing'}]};
  const result=view.projectOpportunity(source,{now:'2026-10-28T12:00:00Z'});
  assert.equal(result.components[0].value,null);
  assert.equal(result.components[0].contribution,null);
  assert.equal(result.components[1].value,9);
  assert.deepEqual(result.valuation_bounds,[0,10]);
  assert.equal(result.current_fit,null);
  assert.deepEqual(result.regime_fit_bounds,{});
  const targets=['components','regimes'].map(field=>({dataset:{opportunityField:field},
    replaceChildren(...rows){this.rows=rows;}}));
  const original=global.document;
  global.document={documentElement:{lang:'en'},
    querySelectorAll:()=>[{dataset:{opportunity:'OXY'},querySelectorAll:()=>targets}],
    createElement:()=>({append(cell){this.cell=cell;}})};
  try{
    view.refreshOpportunityNodes({OXY:result});
    for(const target of targets) assert.equal(target.rows[0].cell.textContent,'Valuation blocked');
  }finally{global.document=original;}
});
test('freshly recalculated safe regime bounds survive the valuation block',()=>{
  const source={...frozen(),schema:'opportunity-v18.1',status:'BLOCKED_INPUTS',
    regime_fit_basis:'UNKNOWN_COVER_BOUNDS',current_fit:null,current_fit_bounds:[34,74],
    regime_fit:{REFLATION:null},regime_fit_bounds:{REFLATION:[34,74]},
    valuation_input_conflicts:[{code:'COMMON_EQUITY_CLAIMS_OMITTED',reason:'Preferred claims missing'}]};
  const result=view.projectOpportunity(source,{now:'2026-10-28T12:00:00Z'});
  assert.deepEqual(result.current_fit_bounds,[34,74]);
  assert.deepEqual(result.regime_fit_bounds,{REFLATION:[34,74]});
  assert.equal(result.label,null);
});
