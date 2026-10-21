/* Current-time projection of immutable assessment-v1 evidence. */
(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports) module.exports=api;
  else root.InvestorAceAssessment=api;
})(typeof globalThis!=='undefined'?globalThis:this,()=>{
  'use strict';
  const maxQuoteAge=96*3600000;
  const stamp=value=>typeof value==='string'&&/(?:Z|[+-]\d{2}:\d{2})$/.test(value)?Date.parse(value):undefined;
  const materialObjections=items=>(items||[]).filter(x=>['major','critical'].includes(x.severity)&&!['verified','rejected'].includes(x.status));
  function project(stored,{now=Date.now(),objections=[]}={}){
    const at=typeof now==='number'?now:stamp(now);
    if(!Number.isFinite(at)) throw new Error('Assessment cutoff requires a timezone');
    if(!stored||stored.schema!=='assessment-v1') return {schema:'assessment-v1',model_score:null,
      model_band:null,rating:null,rating_score:null,quality_rank_eligible:false,new_entry_eligible:false,
      review_status:'REVIEW_REQUIRED',calculation_status:'LEGACY_SNAPSHOT',issues:[],components:[],coverage_weight:0};
    const item=JSON.parse(JSON.stringify(stored));
    const captured=stamp(item.as_of),quote=stamp(item.quote_observed_at);
    const age=at-quote;
    const quoteStatus=typeof item.price!=='number'||!Number.isFinite(item.price)||item.price<=0?'MISSING':
      !Number.isFinite(quote)?'TIME_UNKNOWN':age<0?'FUTURE':age>maxQuoteAge?'STALE':'DATED';
    const until=stamp(item.expires_at)||stamp(item.valid_until);
    const badCapture=!Number.isFinite(captured)||captured>at;
    const blocked=materialObjections(objections).length>0;
    const badReview=item.quality_rank_eligible&&(!Number.isFinite(until)||!Number.isFinite(stamp(item.reviewed_at)));
    if(badCapture||quoteStatus!=='DATED'||until<at||blocked||badReview){
      Object.assign(item,{rating:null,rating_score:null,review_status:'REVIEW_REQUIRED',
        quality_rank_eligible:false,new_entry_eligible:false});
      if(badCapture||quoteStatus!=='DATED'){
        Object.assign(item,{model_score:null,model_band:null,quote_status:quoteStatus});
        for(const c of item.components||[]) if(c.key==='pr') Object.assign(c,{value:null,contribution:null,effective_weight:0});
        item.coverage_weight=(item.components||[]).reduce((sum,c)=>sum+(c.value===null?0:c.nominal_weight),0);
        item.missing_components=(item.components||[]).filter(c=>c.value===null).map(c=>c.key);
        item.score_lower=(item.components||[]).reduce((sum,c)=>sum+(c.contribution??0),0);
        item.score_upper=item.score_lower+10*(1-item.coverage_weight);
        if(item.calculation_status==='COMPLETE') item.calculation_status='PARTIAL';
      }
      item.issues=item.issues||[];
      item.issues.push({code:blocked?'OPEN_OBJECTION':'ASSESSMENT_EXPIRED',severity:'major',status:'open',
        message:blocked?'A current material objection withdraws approval.':'Frozen assessment is not current at this cutoff.'});
    }
    return item;
  }
  function statusLabel(row,language='en'){
    const key=row.review_status==='REVIEWED'?'reviewed':materialObjections(row.objections).length?'objections':'pending';
    const labels={en:{reviewed:'Reviewed',objections:'Open objections',pending:'Unreviewed'},
      de:{reviewed:'Geprüft',objections:'Einwände offen',pending:'Ungeprüft'},
      es:{reviewed:'Revisado',objections:'Objeciones abiertas',pending:'Sin revisar'}};
    return (labels[language]||labels.en)[key];
  }
  function watch(callback,assessments=[]){
    let timer;
    const deadlines=assessments.flatMap(item=>[stamp(item?.as_of),stamp(item?.valid_until),
      stamp(item?.expires_at),stamp(item?.quote_observed_at)+maxQuoteAge]);
    function tick(){
      clearTimeout(timer);
      callback();
      const now=Date.now();
      const next=deadlines.filter(x=>Number.isFinite(x)&&x>=now).map(x=>x-now+1);
      timer=setTimeout(tick,Math.max(20,Math.min(30000,...next)));
    }
    document.addEventListener('visibilitychange',tick);
    globalThis.addEventListener('pageshow',tick);
    tick();
    return ()=>{clearTimeout(timer);document.removeEventListener('visibilitychange',tick);globalThis.removeEventListener('pageshow',tick);};
  }
  function bindReport(packet){
    const language=document.documentElement.lang||'en';
    const pending={en:'REVIEW REQUIRED',de:'PRÜFUNG ERFORDERLICH',es:'REVISIÓN NECESARIA'}[language]||'REVIEW REQUIRED';
    const number=value=>typeof value==='number'&&Number.isFinite(value)?value.toLocaleString(language,{minimumFractionDigits:2,maximumFractionDigits:2}):'—';
    const refresh=()=>{
      const current=Object.fromEntries(Object.entries(packet.assessments).map(([key,item])=>[key,project(item)]));
      for(const node of document.querySelectorAll('[data-assessment]')){
        const item=current[node.dataset.assessment];
        if(!item) continue;
        for(const target of node.querySelectorAll('[data-assessment-field]')){
          const field=target.dataset.assessmentField;
          const values={model_score:number(item.model_score),model_band:item.model_band||'—',
            rating:item.rating||pending,coverage:Math.round(item.coverage_weight*100)+'%',
            bounds:number(item.score_lower)+'–'+number(item.score_upper),
            missing:(item.missing_components||[]).join(', ')||'—',
            verdict:item.quality_rank_eligible?packet.actions[node.dataset.assessment]:pending};
          target.textContent=values[field]??'—';
          if(['verdict','rating','model_band'].includes(field)&&!item.quality_rank_eligible) target.className='pill empty';
        }
      }
      let capacity=1,filled=0;
      for(const node of document.querySelectorAll('[data-entry-assessment]')){
        const item=current[node.dataset.entryAssessment];
        const expiry=stamp(node.dataset.entryExpires);
        const eligible=item?.new_entry_eligible&&Number.isFinite(expiry)&&expiry>=Date.now();
        node.dataset.entryCurrent=String(Boolean(eligible));
        if(eligible){filled++;capacity-=Number(node.dataset.entryWeight)||0;}
        else for(const target of node.querySelectorAll('[data-entry-action]')) target.textContent=target.dataset.entryAction==='status'?pending:'—';
      }
      for(const node of document.querySelectorAll('[data-proposal-current]')){
        node.textContent=node.dataset.proposalCurrent==='filled'?String(filled):(Math.max(0,capacity)*100).toFixed(1)+'%';
      }
      const comparable=(packet.holdings||[]).every(key=>current[key]?.quality_rank_eligible);
      for(const node of document.querySelectorAll('[data-portfolio-reviewed]')) node.hidden=!comparable;
      for(const node of document.querySelectorAll('[data-portfolio-review-status]')){
        node.hidden=comparable;node.textContent=pending;
      }
    };
    document.addEventListener('investorace:portfolio',refresh);
    watch(refresh,Object.values(packet.assessments));
  }
  return {project,materialObjections,statusLabel,watch,bindReport};
});
