import shutil
import subprocess
import unittest

import dashboard_view


class DashboardSearchTests(unittest.TestCase):
    def test_search_shortcut_precedes_earnings_alert(self):
        html = dashboard_view.render('', '', stats=[], sections=[], alert='<aside id="earnings-alert"></aside>')
        self.assertLess(html.index('href="#dashboard-query"'), html.index('id="earnings-alert"'))
        self.assertEqual(html.count('id="dashboard-query"'), 1)

    def test_every_universe_member_is_searchable_by_company_name(self):
        import json
        import engine
        issuers = json.load(open('source_reviews.json')).get('entries', {})
        nameless = [t for t, row in engine.DATA.items()
                    if not row.get('name') and not issuers.get(t, {}).get('issuer')]
        self.assertEqual(nameless, [])

    def test_the_company_name_is_in_the_rendered_search_text(self):
        import engine
        self.assertEqual(engine.DATA['MU']['name'], 'Micron Technology')
        self.assertNotIn('companyNames', dashboard_view.JS)

    @unittest.skipUnless(shutil.which('node'), 'Node is required to execute the dashboard script')
    def test_company_names_and_existing_filters(self):
        setup = """
const assert=require('node:assert/strict');
const create=()=>({events:{}, value:'', dataset:{}, checked:false, addEventListener(k,v){this.events[k]=v;}});
const elements={};
const element=id=>elements[id]??=create();
const rows=['ALM','ELE','LMT','OKLO','TEAM'].map((ticker,i)=>({
  dataset:{assessment:ticker,dashboardSearch:ticker+' '+{ALM:'Almirall',ELE:'Endesa',LMT:'Lockheed Martin',OKLO:'Oklo',TEAM:'Atlassian'}[ticker],dashboardHeld:i===2?'1':'0'},
  cells:[{}, {}, {textContent:i===2?'Industrials':'Other'}]
}));
element('master-table').tBodies=[{rows}];
global.document={getElementById:element,querySelector:()=>create(),addEventListener(){}};
global.window=create();
global.location={hash:''};
"""
        assertions = """
const query=element('dashboard-query');
const shown=()=>rows.filter(row=>!row.hidden).map(row=>row.dataset.assessment);
for(const [term,ticker] of Object.entries({
  'lockheed martin':'LMT','endesa':'ELE','almirall':'ALM','atlassian':'TEAM',
  'oklo':'OKLO','industrials':'LMT','lmt':'LMT'
})){
  query.value=term;
  query.events.input();
  assert.deepEqual(shown(),[ticker]);
}
query.value='';
const held=element('dashboard-held');
held.checked=true;
held.events.change();
assert.deepEqual(shown(),['LMT']);
assert.equal(element('dashboard-count').textContent,'1 / 5');
"""
        subprocess.run(['node', '-'], input=setup + dashboard_view.JS + assertions, text=True, check=True)


if __name__ == '__main__':
    unittest.main()
