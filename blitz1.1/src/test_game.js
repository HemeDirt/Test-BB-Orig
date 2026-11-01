const fs=require('fs');
const path=require('path');
let js=fs.readFileSync(path.join(__dirname,'..','viewer','game.html'),'utf8').match(/<script>([\s\S]*?)<\/script>/)[1];
global.window=global;
const els={};
function mkEl(id){const el={style:{},appendChild(){},scrollTop:0,scrollHeight:0,value:'',logLines:[]};
 Object.defineProperty(el,'innerHTML',{get(){return el._html||''},set(v){el._html=v}});
 Object.defineProperty(el,'textContent',{get(){return el._tc||''},set(v){el._tc=v;if(id==='log')el.logLines.push(v)}});
 return el}
global.document={getElementById:id=>(els[id]=els[id]||mkEl(id)),createElement:()=>mkEl()};
js = js.replace(/let S=null/, 'var S=null').replace(/const (alive|ghosts)=/g,'global.$1=').replace(/let (S|HUMAN|VARIANT|seed|rnd)=/g,'global.$1=');
eval(js.replace(/"use strict";/,''));
// прогон партии с реальными setImmediate-шагами (Promise-цепочки разворачиваются между тиками)
function runGame(seedVal){
 return new Promise((resolve,reject)=>{
  const realSI=setImmediate, calls=[];
  global.setTimeout=(f)=>{calls.push(f);return 0};
  document.getElementById('seedInp').value=String(seedVal);
  startGame(false);
  let guard=0;
  function tick(){
   // выполняем все отложенные шаги цикла
   while(calls.length&&guard<100000){const f=calls.shift();try{f()}catch(e){return reject(e)}guard++}
   if(S.over||guard>=100000)return resolve({over:S.over,cycle:S.cycle,deaths:S.deaths,aliveN:alive().length,firstDeath:S.firstDeath,harvest:S.harvest,bets:S.betHits,revive:S.tokenRevive,guard});
   realSI(tick);
  }
  realSI(tick);
 })}
(async()=>{
document.getElementById('variant').value='base';
const res=[];
for(let i=1;i<=30;i++){try{res.push(await runGame(i))}catch(e){console.log('ERROR seed',i,e.message,'\n',(e.stack||'').split('\n')[1]);break}}
console.log('completed:',res.length,'/30   all over:',res.length===30&&res.every(r=>r.over));
if(res.length){
console.log('end cycle:',Math.min(...res.map(r=>r.cycle)),'-',Math.max(...res.map(r=>r.cycle)));
console.log('alive end:',[...new Set(res.map(r=>r.aliveN))].join(','));
console.log('deaths:',Math.min(...res.map(r=>r.deaths)),'-',Math.max(...res.map(r=>r.deaths)));
console.log('harvest:',res.filter(r=>r.harvest).length+'/30  bets>0:',res.filter(r=>r.bets>0).length+'/30  revive:',res.filter(r=>r.revive).length+'/30');
}
for(const v of ['harvest_off','or5','fast']){document.getElementById('variant').value=v;try{const r=await runGame(99);console.log(v,'-> ok, cycle',r.cycle,'alive',r.aliveN,'over',r.over)}catch(e){console.log(v,'ERROR',e.message)}}
})();
