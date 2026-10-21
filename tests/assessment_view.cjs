const assert = require('node:assert/strict');
const {test} = require('node:test');
const {project,materialObjections,statusLabel} = require('../assessment_view.js');
const frozen = () => ({schema:'assessment-v1',as_of:'2026-10-20T16:15:00Z',
  price:100,quote_observed_at:'2026-10-20T15:40:00Z',quote_status:'DATED',
  valid_until:'2026-10-21T16:00:00Z',expires_at:'2026-10-21T16:00:00Z',
  reviewed_at:'2026-10-20T16:00:00Z',review_status:'REVIEWED',calculation_status:'COMPLETE',
  rating:'BUY',rating_score:8,model_score:8,model_band:'BUY',quality_rank_eligible:true,
  new_entry_eligible:true,coverage_weight:1,score_lower:8,score_upper:8,missing_components:[],
  components:[['g',.15],['p',.20],['c',.15],['b',.15],['v',.10],['pr',.15],['r',.05],['d',.05]]
    .map(([key,w])=>({key,nominal_weight:w,value:8,effective_weight:w,contribution:8*w})),issues:[]});

test('review expiry withdraws approval while fresh model arithmetic remains',()=>{
  const original=frozen();
  const result=project(original,{now:'2026-10-21T16:00:01Z'});
  assert.equal(result.model_score,8);
  assert.equal(result.rating,null);
  assert.equal(result.quality_rank_eligible,false);
  assert.equal(result.new_entry_eligible,false);
  assert.equal(original.rating,'BUY');
});
test('stale quotes withdraw the price-dependent category with original weights',()=>{
  const result=project(frozen(),{now:'2026-10-24T15:40:01Z'});
  assert.equal(result.model_score,null);
  assert.equal(result.model_band,null);
  assert.equal(result.quote_status,'STALE');
  assert.ok(Math.abs(result.coverage_weight-.85)<1e-12);
  assert.deepEqual(result.missing_components,['pr']);
  assert.ok(Math.abs(result.score_lower-6.8)<1e-12);
  assert.ok(Math.abs(result.score_upper-8.3)<1e-12);
});
test('current unresolved objections withdraw approval; corrected is still open',()=>{
  for (const status of ['open','corrected']) {
    const objections=[{severity:'critical',status}];
    assert.equal(materialObjections(objections).length,1);
    assert.equal(project(frozen(),{now:'2026-10-20T17:00:00Z',objections}).rating,null);
  }
  assert.equal(project(frozen(),{now:'2026-10-20T17:00:00Z',
    objections:[{severity:'major',status:'verified'}]}).rating,'BUY');
});
test('future captures, invalid quote times and absent contracts cannot confer approval',()=>{
  for (const changes of [{as_of:'2026-10-22T00:00:00Z'},
      {quote_observed_at:'2026-10-20'}, {expires_at:null,valid_until:null}]) {
    const result=project({...frozen(),...changes},{now:'2026-10-20T17:00:00Z'});
    assert.equal(result.rating,null);
  }
  assert.equal(project(null).quality_rank_eligible,false);
});
test('scanner status vocabulary distinguishes reviewed and unresolved research',()=>{
  assert.equal(statusLabel({review_status:'REVIEWED'},'de'),'Geprüft');
  assert.equal(statusLabel({review_status:'REVIEW_REQUIRED',objections:[{severity:'major',status:'open'}]},'de'),'Einwände offen');
  assert.equal(statusLabel({review_status:'REVIEW_REQUIRED'},'de'),'Ungeprüft');
});
