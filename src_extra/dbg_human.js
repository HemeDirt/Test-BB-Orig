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
document.getElementById('variant').value='base';
document.getElementById('seedInp').value='777';
const realSI=setImmediate, calls=[];
global.setTimeout=(f)=>{calls.push(f);return 0};
startGame(true);
let clicks=0,guard=0;
function tick(){
 while(calls.length&&guard<5000){const f=calls.shift();f();guard++;
  if(window._ha){window._ha("РАНЕНИЕ");clicks++;delete window._ha}}
 const logEl=document.getElementById('log');
 console.log('tick guard=',guard,'clicks=',clicks,'over=',S.over,'cycle=',S.cycle,'cur=',S.cur&&S.cur.seat,'idx=',S.idx,'lastLog=',logEl.logLines.slice(-1)[0]);
 if(S.over||guard>=5000)return console.log('STOP over=',S.over);
 realSI(tick);
}
realSI(tick);
