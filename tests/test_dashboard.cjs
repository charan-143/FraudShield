const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const nodes = new Map();
function element(key){if(!nodes.has(key))nodes.set(key,{innerHTML:'',textContent:'',value:'',hidden:false,disabled:false,focus(){},addEventListener(){},classList:{toggle(){}},setAttribute(){},removeAttribute(){},showModal(){},close(){}});return nodes.get(key);}
const context = vm.createContext({console,Intl,Map,Set,Array,Number,String,Math,JSON,Object,Promise,Error,Blob,URL,setTimeout,clearTimeout,
    document:{querySelector:element,querySelectorAll:()=>[],createElement:()=>({click(){}})},
    window:{addEventListener(){},scrollTo(){}},location:{hash:'#overview'},
    fetch:()=>new Promise(()=>{})});
vm.runInContext(fs.readFileSync(path.join(root,'web/app.js'),'utf8'),context);
const payload=JSON.parse(fs.readFileSync(path.join(root,'web/benchmark.json'),'utf8'));
context.payload=payload;
vm.runInContext('data=payload;run=data.run;tx=data.transactions;modelId=run.champion_id;',context);
const actual=JSON.parse(vm.runInContext('JSON.stringify(calculate(selectedIndices()))',context));
const expected=payload.run.models.find(m=>m.id===payload.run.champion_id).operating;
assert.equal(actual.tp,expected.tp);assert.equal(actual.fp,expected.fp);assert.equal(actual.fn,expected.fn);assert.equal(actual.tn,expected.tn);
assert.ok(Math.abs(actual.captured-expected.captured_exposure)<1e-7);
assert.equal(vm.runInContext("parseCSV('V1,Amount\\r\\n\"1.2\",\"30\"')[0].Amount",context),30);
assert.throws(()=>vm.runInContext("parseCSV('V1,Amount\\n1,')",context),/Invalid number/);
assert.throws(()=>vm.runInContext("parseCSV('V1,V1\\n1,2')",context),/Duplicate/);
assert.throws(()=>vm.runInContext("parseCSV('V1,Amount\\n\"1,2')",context),/unclosed/);
for(const view of ['overview','models','cases','health','score','reports']){
    context.location.hash='#'+view;
    vm.runInContext('render()',context);
    assert.ok(nodes.get('#content').innerHTML.length>500,view+' renders');
    assert.ok(!nodes.get('#content').innerHTML.includes('NaN'),view+' contains no NaN');
    assert.ok(!nodes.get('#content').innerHTML.includes('${run.'),view+' contains no unexpanded run expressions');
}
vm.runInContext("policyMode='budget';budget=1",context);
assert.equal(vm.runInContext('selectedIndices().size',context),Math.ceil(payload.transactions.id.length*.01));
assert.equal(vm.runInContext('calculate(selectedIndices()).tp',context),Math.round(expected.recall*payload.run.splits.test.frauds));
assert.ok(vm.runInContext('workloadCurve()',context).includes('1.25%'));
context.window.FRAUDSHIELD_POLICY=JSON.parse(fs.readFileSync(path.join(root,'web/policy.json'),'utf8'));
vm.runInContext(fs.readFileSync(path.join(root,'web/policy.js'),'utf8'),context);
assert.ok(vm.runInContext('overview()',context).includes('cannot meet both research constraints'));
assert.ok(vm.runInContext('overview()',context).includes('177.1'));
(async()=>{
    let release;
    context.fetch=()=>new Promise(resolve=>{release=resolve;});
    vm.runInContext("page='score';checkAPI()",context);
    vm.runInContext("page='overview';viewVersion++",context);
    release({ok:true,json:async()=>({ready:true,model:'test',max_rows:500})});
    await new Promise(resolve=>setTimeout(resolve,0));
    console.log('Dashboard checks passed: six views, metrics parity, budget selection, CSV validation, late-response navigation guard.');
})().catch(error=>{console.error(error);process.exitCode=1;});
