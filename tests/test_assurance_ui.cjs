const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const root=path.resolve(__dirname,'..');
const nodes=new Map();
function element(key){if(!nodes.has(key))nodes.set(key,{innerHTML:'',textContent:'',value:'',open:false,disabled:false,hidden:false,onclick:null,
    addEventListener(){},setAttribute(){},removeAttribute(){},classList:{toggle(){}},focus(){},
    insertAdjacentHTML(_position,html){this.innerHTML+=html;},showModal(){this.open=true;},close(){this.open=false;}});return nodes.get(key);}
const context=vm.createContext({console,Intl,Map,Set,Array,Number,String,Math,JSON,Object,Promise,Error,Blob,URL,encodeURIComponent,setTimeout,clearTimeout,
    document:{querySelector:element,querySelectorAll:()=>[],createElement:()=>({click(){}})},window:{addEventListener(){},scrollTo(){}},location:{hash:'#overview'},fetch:()=>new Promise(()=>{})});
vm.runInContext(fs.readFileSync(path.join(root,'web/app.js'),'utf8'),context);
context.payload=JSON.parse(fs.readFileSync(path.join(root,'web/benchmark.json'),'utf8'));
context.window.FRAUDSHIELD_ASSURANCE=JSON.parse(fs.readFileSync(path.join(root,'web/assurance.json'),'utf8'));
vm.runInContext('data=payload;run=data.run;tx=data.transactions;modelId=run.champion_id;',context);
// Replace the base case renderer with a small DOM-state fixture; exercise the real review overlay and callbacks.
vm.runInContext("openCase=function(i){document.querySelector('#caseDialog').open=true;document.querySelector('#caseTitle').textContent=tx.id[i];}",context);
vm.runInContext(fs.readFileSync(path.join(root,'web/assurance.js'),'utf8'),context);
context.location.hash='#assurance';
vm.runInContext('render()',context);
const html=nodes.get('#content').innerHTML;
assert.ok(html.includes('Eight limits, eight explicit responses.'));
assert.ok(html.includes('synthetic account-opening'));
assert.ok(html.includes('NOT COMPARABLE'));
assert.ok(!html.includes('NaN')&&!html.includes('${'));
const historyResponse={ok:true,json:async()=>({events:[],integrity:{valid:true}})};
const tick=()=>new Promise(resolve=>setTimeout(resolve,0));
(async()=>{
    let requests=[];
    context.fetch=(url,options)=>new Promise(resolve=>requests.push({url,options,resolve}));
    vm.runInContext('openCase(0)',context);
    const old=requests.shift();
    nodes.get('#caseDialog').close();
    vm.runInContext('openCase(0)',context);
    const fresh=requests.shift();
    fresh.resolve(historyResponse);await tick();
    assert.equal(nodes.get('#saveReview').disabled,false);
    element('#reviewActor').value='reviewer-01';element('#reviewDisposition').value='inconclusive';element('#reviewReason').value='Need more evidence.';
    const save=nodes.get('#saveReview').onclick();
    const post=requests.shift();
    old.resolve(historyResponse);await tick();
    assert.equal(nodes.get('#saveReview').disabled,true,'old same-case GET cannot reenable an active POST');
    post.resolve({ok:true,json:async()=>({event:{}})});await tick();
    const refresh=requests.shift();
    nodes.get('#caseDialog').close();
    vm.runInContext('openCase(1)',context);
    nodes.get('#reviewReason').value='Unsaved reason for a different case.';
    refresh.resolve(historyResponse);await save;await tick();
    assert.equal(nodes.get('#reviewReason').value,'Unsaved reason for a different case.','old save refresh cannot clear a new case reason');
    console.log('Assurance UI checks passed: measured evidence view, task separation, same-case generation guard, cross-case pending-refresh guard.');
})().catch(error=>{console.error(error);process.exitCode=1;});
