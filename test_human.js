const fs=require('fs');
let js=fs.readFileSync('game.html','utf8').match(/<script>([\s\S]*?)<\/script>/)[1];
global.window=global;
const els={};
function mkEl(id){const el={style:{},appendChild(){},scrollTop:0,scrollHeight:0,value:'',logLines:[]};
 Object.defineProperty(el,'innerHTML',{get(){return el._html||''},set(v){el._html=v}});
 Object.defineProperty(el,'textContent',{get(){return el._tc||''},set(v){el._tc=v;if(id==='log')el.logLines.push(v)}});
 return el}
global.document={getElementById:id=>(els[id]=els[id]||mkEl(id)),createElement:()=>mkEl()};
js = js.replace(/let S=null/, 'var S=null').replace(/const (alive|ghosts)=/g,'global.$1=').replace(/let (S|HUMAN|VARIANT|seed|rnd)=/g,'global.$1=');
eval(js.replace(/"use strict";/,''));
// human mode: когда появляются кнопки — жмём первую доступную
function runGame(seedVal){
 return new Promise((resolve,reject)=>{
  const realSI=setImmediate, calls=[];
  global.setTimeout=(f)=>{calls.push(f);return 0};
  document.getElementById('seedInp').value=String(seedVal);
  startGame(true); // HUMAN=true, играем за P1
  let clicks=0, guard=0;
  function tick(){
   while(calls.length&&guard<200000){const f=calls.shift();try{f()}catch(e){return reject(e)}guard++;
    if(window._ha){window._ha("РАНЕНИЕ");clicks++;delete window._ha}}
   if(S.over||guard>=200000)return resolve({over:S.over,cycle:S.cycle,clicks});
   realSI(tick);
  }
  realSI(tick);
 })}
(async()=>{
document.getElementById('variant').value='base';
for(const s of [777,778,779]){try{const r=await runGame(s);console.log('human seed',s,'-> over:',r.over,'cycle',r.cycle,'clicks',r.clicks)}catch(e){console.log('ERROR',s,e.message,(e.stack||'').split('\n')[1])}}
})();
