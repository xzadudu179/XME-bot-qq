/* ════════════════════════════════════════════════════

   deon-web · js/site.js   v2

   公共交互：主题(昼夜)引导/切换 · 移动端菜单(动画) ·

   FAQ details 展开收起动画 · marquee 视口自适应填充 · 滚动入场

   ════════════════════════════════════════════════════ */

(function(){

'use strict';

var root=document.documentElement,key='deon-theme';



/* 主题初始化优先级：?theme= 参数 > localStorage > 系统偏好 */

var q=(location.search.match(/theme=(\w+)/)||[])[1];

var th=q||localStorage.getItem(key)||

       (window.matchMedia&&matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');

if(q){try{localStorage.setItem(key,th);}catch(e0){}}

root.classList.toggle('dark',th==='dark');



/* 全站统一切换入口（seekeros 页复用同名实现） */

window.__setTheme=function(){

 th=th==='dark'?'light':'dark';

 try{localStorage.setItem(key,th);}catch(e1){}

 root.classList.toggle('dark',th==='dark');

 document.dispatchEvent(new CustomEvent('deon-theme',{detail:th}));

};

var tb=document.getElementById('themeBtn');

if(tb)tb.addEventListener('click',window.__setTheme);



/* 移动端菜单折叠（带展开/收起过渡） */

var mBtn=document.getElementById('mBtn'),mNav=document.getElementById('mNav');

if(mBtn&&mNav){

 if(!mNav.classList.contains('mnav-x'))mNav.classList.add('mnav-x');

 mBtn.addEventListener('click',function(){

  var on=mNav.classList.toggle('on');

  mBtn.setAttribute('aria-expanded',on?'true':'false');

 });

 /* 点了链接就自动收起 */

 mNav.addEventListener('click',function(ev){

  var t=ev.target;

  while(t&&t!==mNav&&!(t.tagName==='A'))t=t.parentNode;

  if(t&&t.tagName==='A'){mNav.classList.remove('on');mBtn.setAttribute('aria-expanded','false');}

 });

}



/* FAQ details 展开/收起动画：运行时把 summary 之后的内容包进 .dbody 再测高 */

function raf2(f){requestAnimationFrame(function(){requestAnimationFrame(f);});}

Array.prototype.slice.call(document.querySelectorAll('details')).forEach(function(d){

 if(d.dataset.faqBound)return;

 var sum=d.querySelector('summary');if(!sum)return;

 d.dataset.faqBound='1';

 var body=d.querySelector('.dbody');

 if(!body){

  body=document.createElement('div');body.className='dbody';

  while(sum.nextSibling)body.appendChild(sum.nextSibling);

  d.appendChild(body);

 }

 body.style.height=d.open?'auto':'0px';

 body.style.opacity=d.open?'1':'0';

 d.open=false;

 var busy=false;

 sum.addEventListener('click',function(ev){

  ev.preventDefault();

  if(busy)return;busy=true;

  if(d.open){                                   /* 收起 */

   d.classList.add('closing');

   body.style.height=body.scrollHeight+'px';

   raf2(function(){body.style.height='0px';body.style.opacity='0';});

   setTimeout(function(){d.open=false;d.classList.remove('closing');busy=false;},430);

  }else{                                        /* 展开 */

   d.open=true;

   var h=body.scrollHeight;

   body.style.height='0px';body.style.opacity='0';

   raf2(function(){body.style.height=h+'px';body.style.opacity='1';});

   setTimeout(function(){body.style.height='auto';busy=false;},450);

  }

 });

 sum.addEventListener('keydown',function(ev){   /* 键盘空格可达性 */

  if(ev.key===' '||ev.key==='Spacebar'){ev.preventDefault();sum.click();}

 });

});



/* 滚动入场动画 */

var els=document.querySelectorAll('.reveal');

if('IntersectionObserver' in window){

 var io=new IntersectionObserver(function(es){

  es.forEach(function(e){

   if(e.isIntersecting){e.target.classList.add('on');io.unobserve(e.target);}

  });

 },{threshold:.12});

 Array.prototype.slice.call(els).forEach(function(el){io.observe(el);});

}else{

 for(var i=0;i<els.length;i++)els[i].classList.add('on');

}



/* marquee：按视口宽度克隆填满，宽屏不再出现内容凭空生成于画面内；

   动画时长随份数同步缩放，保持恒定滚动速度与 -50% 平移无缝循环 */

var SPEED=46;                                    /* px/s */

var mqs=Array.prototype.slice.call(document.querySelectorAll('.mq-in'));

function refill(mq){

 var unit=mq.children.length?mq.children[0]:null;if(!unit)return;

 mq.innerHTML='';mq.appendChild(unit);

 var uw=unit.getBoundingClientRect().width||unit.offsetWidth||600;

 if(uw<40)return;

 var copies=Math.max(2,Math.ceil((innerWidth*1.18)/uw));

 if(copies%2)copies++;

 for(var i=1;i<copies;i++)mq.appendChild(unit.cloneNode(true));

 var dur=(copies/2*uw)/SPEED;

 mq.style.animationDuration=dur.toFixed(2)+'s';

}

function refitAll(){for(var k=0;k<mqs.length;k++)refill(mqs[k]);}

refitAll();

if(document.fonts&&document.fonts.ready)document.fonts.ready.then(refitAll);

setTimeout(refitAll,700);

var rzT=null;

addEventListener('resize',function(){clearTimeout(rzT);rzT=setTimeout(refitAll,180);});

/* v4 · 指令页分类条：滑动引导（用户滚过一点或到达尽头后，提示自动淡出） */

var tbw=document.getElementById('tabbar');

if(tbw){

 var tsc=tbw.querySelector('.tabscroll'),

     tabHi=function(){

      var nearEnd=tsc.scrollLeft>=tsc.scrollWidth-tsc.clientWidth-8;

      tbw.classList.toggle('at-end',tsc.scrollLeft>40||nearEnd);

     };

 tsc.addEventListener('scroll',tabHi,{passive:true});

 tabHi();

 addEventListener('resize',tabHi);

}

})();

