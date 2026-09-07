/* ══════════════════════════════════════════════════════════

   deon-web · js/ocean.js          v2 rebuild

   SeekerOS — Endless Sea  (three.js r128, WebGL)

   「海面之上阳光明媚，海面之下暗流涌动」

   · Gerstner 波 ×5 叠加（顶点位移 + 解析法线导数）
   · 折射层 RT（layer1）：穹顶背景 × 体积光柱 × 荧光尘埃，
     水面片元按波法线扰动采样得到扭曲水下影像
   · 主屏直视层（layer0）：天空 + 触手实体 + 半透明水面 + 漂流瓶
     —— 水体菲涅尔加权透明：俯视能真正看进海里见到触手游弋
   · 解析式天空函数（穹顶与反射共用）+ Schlick 菲涅尔
   · 太阳 glitter / 波峰泡沫 / 焦散网纹
   · 程序化水下暗流纹理 + 锥形扭动触手（周期性破水）
   · 低多边形漂流瓶（LatheGeometry + 物理透射玻璃）：
     26~34s 首次现身 → 漂入近岸停驻(60s 自沉倒计时)
     → 点读信件 → 「让它继续漂」/点击遮罩放行 → 20~36s 后再来一只
   · 昼夜主题联动站点主题；#night/#day hash 可强制；?auto=1 免点击入场
   ══════════════════════════════════════════════════════════ */

(function(){

'use strict';

function fail(msg){

 var d=document.getElementById('intro');

 if(d){d.style.display='flex';d.style.zIndex=999;

 d.innerHTML='<div style="padding:2rem;text-align:center">'+msg+'</div>';}

}

if(typeof THREE==='undefined'){fail('THREE.js 加载失败…请检查网络后刷新。');return;}

var canvas=document.getElementById('sea');

var isMobile=Math.min(innerWidth,innerHeight)<720;

var W=innerWidth,H=innerHeight;

var DPR_BASE=Math.min(window.devicePixelRatio||1,1.7);

var renderer=null;

try{

 renderer=new THREE.WebGLRenderer({canvas:canvas,antialias:true,powerPreference:'high-performance'});

}catch(err){

 fail('这个浏览器不支持 WebGL…<br>无尽之海暂时无法对意识开放。');

 return;

}

renderer.setSize(W,H,false);

renderer.setPixelRatio(DPR_BASE);

var scene=new THREE.Scene();

var cam=new THREE.PerspectiveCamera(55,W/H,0.5,2600);

var RT_SCALE=.8;

var rt=new THREE.WebGLRenderTarget(

 Math.max(320,Math.floor(W*DPR_BASE*RT_SCALE)),

 Math.max(240,Math.floor(H*DPR_BASE*RT_SCALE)));

/* ───────────── 共享 GLSL ───────────── */

var GLSL_COMMON='uniform float uTime;uniform float uDay;uniform vec3 uSunDir;\n'+

'float hash21(vec2 p){p=fract(p*vec2(123.34,456.21));p+=dot(p,p+45.32);return fract(p.x*p.y);}\n'+

'float vnoise(in vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);\n'+

' float a=hash21(i),b=hash21(i+vec2(1.,0.)),c=hash21(i+vec2(0.,1.)),d=hash21(i+vec2(1.,1.));\n'+

' return mix(mix(a,b,f.x),mix(c,d,f.x),f.y);}\n'+

'float fbm(vec2 p){float v=vnoise(p)*.5;v+=vnoise(p*2.03+13.7)*.25;v+=vnoise(p*4.11+91.3)*.125;return v;}\n';

/* 解析天空（穹顶与水面反射共用） */

var SKY_FN='\n'+

'vec3 skyCol(vec3 rd,float day){\n'+

' float y=clamp(rd.y,-1.,1.);\n'+

' vec3 zenD=mix(vec3(.014,.026,.058),vec3(.152,.34,.61),day);\n'+

' vec3 midD=mix(vec3(.05,.09,.155),vec3(.52,.71,.86),day);\n'+

' vec3 horD=mix(vec3(.11,.138,.205),vec3(.93,.87,.76),day);\n'+

' float h=pow(1.-max(abs(y),0.),3.);\n'+

' vec3 col=mix(mix(midD,zenD,pow(clamp(y,0.,1.),.72)),horD,h*(y<0.?1.35:1.));\n'+

' col=mix(col,horD,smoothstep(.02,-.12,y));\n'+

' float sd=max(dot(rd,normalize(uSunDir)),0.);\n'+

' vec3 sunC=mix(vec3(.78,.86,1.),vec3(1.,.8,.44),day);\n'+

' col+=sunC*pow(sd,1400.)*mix(7.,13.,day);\n'+          /* 日/月盘 */

' col+=sunC*pow(sd,220.)*mix(.24,.75,day);\n'+          /* 内晕 */

' col+=sunC*pow(sd,7.)*mix(.06,.17,day);\n'+            /* 外辉 */

' float cl=fbm(rd.xz/(abs(rd.y)+.18)*1.55+vec2(uTime*.008,uTime*.003));\n'+

' float cAmt=smoothstep(.56,.82,cl)*smoothstep(-.02,.3,y);\n'+

' vec3 cSh=mix(vec3(.13,.15,.23),vec3(.62,.66,.78),day);\n'+

' float lit=pow(sd,5.)*.9;\n'+

' vec3 cc=mix(cSh,vec3(1.,.98,.93),lit);\n'+

' col=mix(col,cc,cAmt*.62*mix(.85,1.,day));\n'+

' if(day<.6&&y>.08){\n'+                                 /* 星空（仅夜间） */

'  vec2 spq=vec2(atan(rd.z,rd.x)*7.6,asin(clamp(rd.y,-1.,1.))*40.);\n'+

'  vec2 cell=floor(spq);vec2 fr2=fract(spq)-.5;\n'+

'  float st=hash21(cell);\n'+

'  float tw=.55+.45*sin(uTime*(1.5+st*5.)+st*39.);\n'+

'  float ds=length(fr2);\n'+

'  col+=vec3(.88,.93,1.)*smoothstep(.34,.02,ds)*smoothstep(.985,1.,st)*tw*(1.-day/.6)*1.15;\n'+

' }\n'+

' return col;\n'+

'}\n';

var SKY_VERT='varying vec3 vDir;\n'+

'void main(){\n'+

' vec4 wp=modelMatrix*vec4(position,1.);\n'+

' vDir=wp.xyz-cameraPosition;\n'+

' gl_Position=projectionMatrix*viewMatrix*wp;\n'+

'}\n';

/* ───────────── 天穹 ───────────── */

var skyUniforms={uTime:{value:0},uDay:{value:1},uSunDir:{value:new THREE.Vector3(-.34,.33,-.88)}};

var skyMesh=new THREE.Mesh(new THREE.SphereGeometry(2000,48,30),

 new THREE.ShaderMaterial({side:THREE.BackSide,depthWrite:false,

 uniforms:skyUniforms,vertexShader:SKY_VERT,

 fragmentShader:'varying vec3 vDir;\n'+GLSL_COMMON+SKY_FN+

 '\nvoid main(){gl_FragColor=vec4(skyCol(normalize(vDir),clamp(uDay,0.,1.)),1.);}\n'}));

scene.add(skyMesh);

/* ───────────── 水面·顶点（Gerstner） ───────────── */

var WATER_VERT='uniform float uTime;\n'+

'varying vec3 vWPos;varying vec3 vN;varying float vCrest;\n'+

'void gw(vec2 p,vec2 dirIn,float steep,float wl,float sp,inout vec3 acc,inout float dhx,inout float dhz){\n'+

' vec2 d=normalize(dirIn);\n'+

' float k=6.2831853/wl;\n'+

' float om=sqrt(9.81*k)*sp;\n'+

' float f=k*dot(d,p)-om*uTime;\n'+

' float a=steep/k;\n'+

' float sf=sin(f),cf=cos(f);\n'+

' dhx+=-k*d.x*a*cf;\n'+                 /* 高度场解析偏导 → 法线 */

' dhz+=-k*d.y*a*cf;\n'+

' acc+=vec3(d.x*a*cf,a*sf,d.y*a*cf);\n'+

'}\n'+

'void main(){\n'+

' vec3 pos=position;\n'+

' vec3 acc=vec3(0.);\n'+

' float dhx=0.;float dhz=0.;\n'+

' gw(pos.xz,vec2( 1. , .28),.300,52., .96,acc,dhx,dhz);\n'+

' gw(pos.xz,vec2(-.68, .42),.215,29.,1.02,acc,dhx,dhz);\n'+

' gw(pos.xz,vec2( .87,-.50),.115,16.5,1.1,acc,dhx,dhz);\n'+

' gw(pos.xz,vec2(-.23,-.88),.085, 8.8,1.22,acc,dhx,dhz);\n'+

' gw(pos.xz,vec2( .41, .91),.060, 4.4,1.34,acc,dhx,dhz);\n'+

' pos+=acc;\n'+

' vCrest=acc.y;\n'+

' vN=normalize(vec3(-dhx,1.,-dhz));\n'+

' vec4 wp=modelMatrix*vec4(pos,1.);\n'+

' vWPos=wp.xyz;\n'+

' gl_Position=projectionMatrix*viewMatrix*wp;\n'+

'}\n';

/* ───────────── 水面·片元 ───────────── */

var WATER_FRAG='varying vec3 vWPos;varying vec3 vN;varying float vCrest;\n'+

'uniform vec2 useres;uniform vec3 uCamPos;uniform sampler2D uRefr;\n'+GLSL_COMMON+SKY_FN+'\n'+

'void main(){\n'+

' vec3 V=normalize(cameraPosition-vWPos);\n'+

' float dist=length(uCamPos-vWPos);\n'+

' vec2 pq=vWPos.xz;\n'+

/* 微法线细节：多层 value-noise 梯度扰动 */

' float e=.4;\n'+

' float n0=vnoise(pq*1.15+uTime*.26);\n'+

' float nx=vnoise((pq+vec2(e,0.))*1.15+uTime*.26);\n'+

' float nz=vnoise((pq+vec2(0.,e))*1.15+uTime*.26);\n'+

' float n2=vnoise(pq*3.4-uTime*.34);\n'+

' float n3=vnoise(pq*6.2+uTime*.51);\n'+

' vec3 N=normalize(vN*1.1+vec3(nx-n0,0.,nz-n0)*.62+vec3(n2-.5+n3-.5)*.08);\n'+

' float ndv=max(dot(N,V),0.);\n'+

' float fr=.024+.976*pow(1.-ndv,5.);\n'+          /* Schlick 菲涅尔 */

' vec3 R=reflect(-V,N);\n'+

' R.y=abs(R.y)*.94+.03;R=normalize(R);\n'+

' vec3 refl=skyCol(R,clamp(uDay,0.,1.));\n'+

/* 太阳/月亮 glitter 与宽角 sheen */

' vec3 L=normalize(uSunDir);\n'+

' vec3 Hh=normalize(L+V);\n'+

' float shin=mix(460.,260.,clamp(uDay,0.,1.));\n'+

' float gMask=smoothstep(650.,100.,dist)*(0.35+0.65*smoothstep(50.,160.,dist));\n'+

' vec3 sunC=mix(vec3(.58,.74,1.06),vec3(1.,.6,.24),clamp(uDay,0.,1.));\n'+

' float spec=pow(max(dot(N,Hh),0.),shin);\n'+

' float sheen=pow(max(dot(N,Hh),0.),30.)*.11;\n'+

/* 泡沫：波峰高度 × 双噪声破洞 */

' float crest=smoothstep(.8,1.5,vCrest);\n'+

' float fnz=vnoise(pq*2.8+vec2(uTime*.42,-uTime*.31))*vnoise(pq*5.3-uTime*.24);\n'+

' float foam=crest*smoothstep(.36,.78,fnz)*clamp(uDay+.15,0.,1.);\n'+

/* 折射：RT 扭曲采样 */

' vec2 suv=gl_FragCoord.xy/useres;\n'+

' vec2 ruv=suv+N.xz*mix(.13,.04,fr)*(320./max(dist,30.));\n'+

' ruv=clamp(ruv,vec2(.002),vec2(.998));\n'+

' vec3 refr=texture2D(uRefr,ruv).rgb;\n'+

' float steeplook=smoothstep(.42,.95,ndv);\n'+

' vec3 abys=mix(vec3(.002,.006,.014),vec3(.004,.03,.056),clamp(uDay,0.,1.));\n'+

' refr=mix(refr,abys,steeplook*.42);\n'+           /* 俯视越深越暗 */

/* 程序化暗流纹理（配合真实触手实体作氛围补充） */

' float nmz=smoothstep(240.,36.,dist);\n'+

' float tS1=sin(vWPos.x*.16+sin(vWPos.z*.11+uTime*.5)*1.9+uTime*.14);\n'+

' float tS2=sin(vWPos.x*.09-vWPos.z*.13+uTime*.21+2.1);\n'+

' float tend=max(smoothstep(.55,.98,tS1),smoothstep(.62,.97,tS2))*\n'+

'  smoothstep(.72,.25,vnoise(vec2(vWPos.x*.045+uTime*.05,vWPos.z*.06)));\n'+

' refr*=1.-tend*nmz*(.30+.10*uDay);\n'+

' float shft=pow(.5+.5*sin(vWPos.x*.21+sin(uTime*.12+vWPos.z*.03)*1.25),7.)*nmz;\n'+

' refr+=vec3(.10,.4,.35)*shft*(.11+.15*uDay)*(0.4+0.6*tend);\n'+

/* 焦散网纹 */

' vec2 cq=vWPos.xz*.5+vec2(uTime*.05,uTime*.036);\n'+

' float c1=vnoise(cq*2.1);float c2=vnoise(cq*3.65+47.3);\n'+

' float caus=pow(max(c1*c2*2.35-1.02,0.),2.4);\n'+

' vec3 causC=mix(vec3(.28,.9,.74),vec3(1.,.84,.48),clamp(uDay,0.,1.));\n'+

' refr+=causC*caus*(.42+.58*uDay)*(1.-steeplook)*smoothstep(420.,80.,dist)*.78;\n'+

/* 合成 */

' vec3 col=mix(refr,refl,clamp(fr,0.,1.));\n'+

' col+=sunC*(spec*mix(2.,5.,uDay)+sheen)*gMask*(1.-clamp(foam,0.,1.)*.8);\n'+

' vec3 foamC=vec3(.965,.975,.945)*(.72+.28*fnz);\n'+

' col=mix(col,foamC,clamp(foam*.92,0.,1.));\n'+

' vec3 fz=normalize(vec3(vWPos.x-uCamPos.x,0.,vWPos.z-uCamPos.z));\n'+

' vec3 hzs=mix(vec3(.14,.17,.23),vec3(.87,.83,.73),clamp(uDay,0.,1.));\n'+

' col=mix(col,hzs,smoothstep(330.,720.,dist));\n'+

/* v2 · 半透明水体：俯视可透视见底，掠射角近乎实心；远海收敛为实感 */

' float aW=mix(.32,.97,fr);\n'+

' aW=mix(aW,1.,smoothstep(190.,540.,dist));\n'+

' aW=max(aW,clamp(foam,0.,1.))*.985;\n'+

' gl_FragColor=vec4(pow(col,vec3(.98)),aW);\n'+

'}\n';

var waterGeo=new THREE.PlaneGeometry(1750,1750,isMobile?150:235,isMobile?150:235);

waterGeo.rotateX(-Math.PI/2);

var waterUniforms={

 uTime:{value:0},uDay:{value:1},uSunDir:{value:skyUniforms.uSunDir.value},

 uCamPos:{value:new THREE.Vector3()},uRefr:{value:rt.texture},

 useres:{value:new THREE.Vector2(W*DPR_BASE,H*DPR_BASE)}

};

var water=new THREE.Mesh(waterGeo,new THREE.ShaderMaterial({

 uniforms:waterUniforms,vertexShader:WATER_VERT,fragmentShader:WATER_FRAG,

 transparent:true}));

scene.add(water);

/* ───────────── 水下世界 ───────────── */

var uw=new THREE.Group();scene.add(uw);

/* 穹顶背景：折射层(L1)提供 RT 底色，主屏(L0)保证直视时海面之下仍是深海 */

var uwDomeMat=new THREE.ShaderMaterial({

 side:THREE.BackSide,

 uniforms:{uTime:{value:0},uDay:{value:1}},

 vertexShader:'varying vec3 vP;void main(){vP=position;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}\n',

 fragmentShader:'varying vec3 vP;\n'+GLSL_COMMON+'\n'+

 'void main(){\n'+

 ' vec3 r=normalize(vP);\n'+

 ' float y=clamp(r.y,-1.,1.);\n'+

 ' vec3 up=mix(vec3(.02,.16,.19),vec3(.09,.56,.58),uDay);\n'+

 ' vec3 deep=mix(vec3(.001,.003,.008),vec3(.006,.02,.04),uDay);\n'+

 ' vec3 col=mix(deep,up,pow(smoothstep(-.55,.4,y),1.6));\n'+

 ' float shaft=vnoise(vec2(atan(r.z,r.x)*7.+sin(uTime*.06)*2.,r.y*4.-uTime*.02));\n'+

 ' col+=up*shaft*.2*smoothstep(-.1,.5,y);\n'+

 ' gl_FragColor=vec4(col,1.);\n'+

 '}\n'});

/* v4 · 穹顶只保留"水下碗"：削掉上半球，不再遮挡真天空

   —— 白天的太阳、夜晚的月亮星空因此重新出现在主屏视野 */

var dome=new THREE.Mesh(new THREE.SphereGeometry(950,48,26,0,Math.PI*2,1.594,Math.PI-1.594),uwDomeMat);

dome.layers.mask=3;

uw.add(dome);

skyMesh.layers.enable(1);        /* 折射 RT 里给碗外区域一个天空兜底色 */

/* 体积光柱（加性平面，垂直微摆动）——仅折射层出现 */

var rayVert='uniform float uTime;uniform float uPhase;varying vec2 vUv;\n'+

'void main(){\n'+

' vec3 p=position;p.x+=sin(uTime*.5+uPhase+p.y*.05)*2.4;\n'+

' vUv=uv;\n'+

' gl_Position=projectionMatrix*modelViewMatrix*vec4(p,1.);\n'+

'}\n';

var rayFrag='uniform float uTime;uniform float uPhase;uniform float uDay;varying vec2 vUv;\n'+

'void main(){\n'+

' float x=(vUv.x-.5)*2.;\n'+

' float body=pow(max(1.-abs(x),0.),2.3);\n'+

' float stripes=.55+.45*sin(vUv.x*34.+uPhase+uTime*1.6);\n'+

' float fade=pow(clamp(vUv.y,0.,1.),2.1);\n'+

' vec3 c=mix(vec3(.34,.8,.6),vec3(1.,.87,.5),uDay);\n'+

' float flick=.5+.5*sin(uTime*.85+uPhase*2.2);\n'+

' gl_FragColor=vec4(c,body*stripes*fade*flick*(.3+.2*uDay));\n'+

'}\n';

var rays=[];

for(var i0=0;i0<(isMobile?9:14);i0++){

 var rm=new THREE.Mesh(new THREE.PlaneGeometry(isMobile?3.2:4.6,isMobile?110:150),

 new THREE.ShaderMaterial({transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,side:THREE.DoubleSide,

  uniforms:{uTime:{value:0},uPhase:{value:Math.random()*24},uDay:{value:1}},

  vertexShader:rayVert,fragmentShader:rayFrag}));

 var angA=Math.random()*Math.PI*2,rA=30+Math.random()*175;

 rm.position.set(Math.sin(angA)*rA,-9-Math.random()*17,Math.cos(angA)*rA);

 rm.rotation.y=Math.random()*Math.PI;rm.rotation.z=(Math.random()-.5)*.45;

 rm.layers.set(1);

 rays.push(rm);uw.add(rm);

}

/* 锥形触手：Catmull-Rom 曲线 + Frenet 框架手工构网（半径渐变）——主屏实体 */

function buildTentGeo(curve,rad,tub,radSeg){

 var frames=curve.computeFrenetFrames(tub,false);

 var pos=[],nor=[],uvs=[],idx=[];

 var P=new THREE.Vector3(),NV=new THREE.Vector3();

 for(var i=0;i<=tub;i++){

  var t=i/tub;

  curve.getPointAt(t,P);

  var taper=Math.pow(1-t,1.3)*.92+.07;

  var Nr=frames.normals[i],Br=frames.binormals[i];

  var rr=rad*taper;

  for(var j=0;j<=radSeg;j++){

   var vv=j/radSeg*Math.PI*2;

   var sv=Math.sin(vv),cv=-Math.cos(vv);

   NV.set(Nr.x*cv+Br.x*sv,Nr.y*cv+Br.y*sv,Nr.z*cv+Br.z*sv).normalize();

   nor.push(NV.x,NV.y,NV.z);

   pos.push(P.x+rr*NV.x,P.y+rr*NV.y,P.z+rr*NV.z);

   uvs.push(t,j/radSeg);

  }

 }

 for(var i2=1;i2<=tub;i2++)for(var j2=1;j2<=radSeg;j2++){

  var a=(radSeg+1)*(i2-1)+(j2-1),b=(radSeg+1)*i2+(j2-1),

      c=(radSeg+1)*i2+j2,dd=(radSeg+1)*(i2-1)+j2;

  idx.push(a,b,dd,b,c,dd);

 }

 var g=new THREE.BufferGeometry();

 g.setIndex(idx);

 g.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));

 g.setAttribute('normal',new THREE.Float32BufferAttribute(nor,3));

 g.setAttribute('uv',new THREE.Float32BufferAttribute(uvs,2));

 return g;

}

var tentVert='uniform float uTime;uniform float uPhase;uniform float uAmp;\n'+

'varying vec3 vNw;varying vec3 vWp;varying vec2 vUv2;\n'+

'void main(){\n'+

' vec3 p=position;\n'+

' float t=clamp(uv.x,0.,1.);\n'+

' float sw=pow(t,2.)*uAmp;\n'+                     /* 愈近尖端摆幅愈大 */

' p.x+=sin(uTime*.7+uPhase+p.y*.12)*sw;\n'+

' p.z+=cos(uTime*.53+uPhase*1.7+p.y*.1)*sw*.8;\n'+

' vUv2=uv;\n'+

' vec4 wp=modelMatrix*vec4(p,1.);\n'+

' vWp=wp.xyz;\n'+

' vNw=normalize(mat3(modelMatrix)*normal);\n'+

' gl_Position=projectionMatrix*viewMatrix*wp;\n'+

' }\n';

var tentFrag='uniform float uDay;varying vec3 vNw;varying vec3 vWp;varying vec2 vUv2;\n'+

'void main(){\n'+

' vec3 V=normalize(cameraPosition-vWp);\n'+

' float ndv=max(dot(normalize(vNw),V),0.);\n'+

' float rim=pow(1.-ndv,2.2);\n'+                   /* 边缘发光 */

' vec3 base=vec3(.008,.011,.018);\n'+

' vec3 glowC=mix(vec3(.14,.6,.46),vec3(.16,.04,.21),(1.-uDay));\n'+ /* 白日青苔绿 / 夜间暗紫荧光 */

' float ridges=.55+.45*sin(vUv2.y*84.)*sin(vUv2.x*160.);\n'+

' float lum=.14+rim*(.92+.38*(1.-uDay))+ridges*.05;\n'+   /* v4 · 夜荧光收敛，不再刺眼 */

' gl_FragColor=vec4(base+glowC*lum,1.);\n'+

'}\n';

var tentacles=[];

/* v4 · 曲线自海底粗端(t=0)长向水面细端(t=1)，尖端悬停于水下 3~8m —— 不再破水跳出 */

function spawnTentacle(xx,zz,len,rad){

 var pts=[],x=0,z=0,n=7,i3,t3;

 for(i3=0;i3<=n;i3++){t3=i3/n;

  pts.push(new THREE.Vector3(x,-len*(1-t3),z));

  x+=(Math.random()-.5)*len*.26;z+=(Math.random()-.5)*len*.26;}

 var curve=new THREE.CatmullRomCurve3(pts);

 var geo=buildTentGeo(curve,rad,isMobile?40:60,isMobile?6:8);

 var mat=new THREE.ShaderMaterial({uniforms:{

  uTime:{value:0},uPhase:{value:Math.random()*36},uAmp:{value:1.05+Math.random()*1.4},uDay:{value:1}},

  vertexShader:tentVert,fragmentShader:tentFrag});

 var m=new THREE.Mesh(geo,mat);

 var topY=-(3.2+Math.random()*4.5);

 m.position.set(xx,topY,zz);

 m.userData={baseY:topY,ph:Math.random()*10,spd:.22+Math.random()*.2};

 tentacles.push(m);

 m.layers.set(0);

 uw.add(m);

}

for(var i4=0;i4<(isMobile?6:10);i4++){

 var angB=-Math.PI*.15+(Math.random()-.5)*Math.PI*1.25;

 var rB=(i4<4)?(46+Math.random()*70):(85+Math.random()*165);   /* 前四根靠近相机 */

 var lenB=isMobile?(26+Math.random()*44):(34+Math.random()*56);

 spawnTentacle(Math.sin(angB)*rB,-Math.abs(Math.cos(angB))*rB*.82-45,lenB,.75+Math.random()*1.1);

}

/* 荧光尘埃（上浮粒子）——仅折射层出现 */

var moteN=isMobile?320:650;

var mg=new THREE.BufferGeometry();

var mp=new Float32Array(moteN*3),mr=new Float32Array(moteN);

for(var i5=0;i5<moteN;i5++){

 mp[i5*3]=(Math.random()-.5)*600;

 mp[i5*3+1]=-172+Math.random()*170;

 mp[i5*3+2]=(Math.random()-.5)*600-60;

 mr[i5]=Math.random();

}

mg.setAttribute('position',new THREE.BufferAttribute(mp,3));

mg.setAttribute('aR',new THREE.BufferAttribute(mr,1));

var moteMat=new THREE.ShaderMaterial({transparent:true,depthWrite:false,

 uniforms:{uTime:{value:0},uDay:{value:1}},

 vertexShader:'attribute float aR;uniform float uTime;varying float vA;\n'+

 'void main(){\n'+

 ' vec3 p=position;\n'+

 ' p.y=mod(p.y+uTime*(.3+aR*.55),172.)-172.;\n'+

 ' vec4 mv=modelViewMatrix*vec4(p,1.);\n'+

 ' gl_PointSize=(1.1+aR*2.5)*(150./max(-mv.z,1.));\n'+

 ' vA=aR;\n'+

 ' gl_Position=projectionMatrix*mv;\n'+

 '}\n',

 fragmentShader:'uniform float uDay;varying float vA;\n'+

 'void main(){\n'+

 ' vec2 q=gl_PointCoord-.5;\n'+

 ' float a=smoothstep(.5,.05,length(q));\n'+

 ' vec3 c=mix(vec3(.32,.95,.78),vec3(.95,.9,.7),uDay);\n'+

 ' gl_FragColor=vec4(c,a*(.15+.2*vA));\n'+

 '}\n'});

var motePts=new THREE.Points(mg,moteMat);

motePts.layers.set(1);

uw.add(motePts);

/* ───────────── 环境贴图（给玻璃瓶用） ───────────── */

var envTex=null;

try{

 var ec=document.createElement('canvas');ec.width=128;ec.height=64;

 var cx2=ec.getContext('2d');

 var gr=cx2.createLinearGradient(0,0,0,64);

 gr.addColorStop(0,'#3a5779');gr.addColorStop(.47,'#cdb188');

 gr.addColorStop(.53,'#265059');gr.addColorStop(1,'#04121c');

 cx2.fillStyle=gr;cx2.fillRect(0,0,128,64);

 var et=new THREE.CanvasTexture(ec);

 et.mapping=THREE.EquirectangularReflectionMapping;

 var pmrem=new THREE.PMREMGenerator(renderer);

 envTex=pmrem.fromEquirectangular(et).texture;

 et.dispose();pmrem.dispose();

}catch(err2){envTex=null;}

/* ───────────── 漂流瓶 ───────────── */

var MSGS=[

 {t:"今天也在忒利亚的沙丘上等你。—— Deon"},

 {t:"550W：这不是漂流瓶，是常规数据采样。……才怪。"},

 {t:"我们星球只有沙漠，海是从别人那里听来的故事。所以捞到什么都算新鲜。—— Deon"},

 {t:"请问你看见一块饼干了吗？编号 179。很重要。—— 漠月"},

 {t:"瓶身上的微光，是峡谷深处捡的坭晶石。放心，剂量很安全。—— Deon"},

 {t:"海的对岸还没有人找到过。如果你读到这张纸条，替我看看明天的日出吧。"},

 {t:"awmc."},

 {t:"请输入文本"},

 {t:"点赞可以让海的混乱值降低一点点哦。真的。"},

 {t:"d.n. 不是米。1 d.n. ≈ 5～20 米。越深，越安静。"},

 {t:"有漠月，有漠星，但是没有漠日（？"},

 {t:"和你说话的时候，浪都变得温柔了一点。—— 一只路过的龙龙"},

 {t:"记得早八。否则下次醒来你会在 seek 里。"},

 {t:"𝐚𝐧𝐝 𝐢𝐧 𝐭𝐡𝐚𝐭 𝐥𝐢𝐠𝐡𝐭, 𝐈 𝐟𝐢𝐧𝐝 𝐝𝐞𝐥𝐢𝐯𝐞𝐫𝐚𝐧𝐜𝐞.",gold:true},

 {t:"小心不要被编造的话骗到哦（？ —— 某只 AI 助手"},

 {t:"其实你捡到的每一只瓶子，都是有人决定与世界再说一句话。"}

];

function buildBottleModel(scale){

 var grp=new THREE.Group();

 var profile=[[0,-1.05],[.34,-1],[.42,-.72],[.43,.1],[.4,.55],[.2,.8],

              [.14,1.02],[.13,1.22],[.19,1.28],[.2,1.34]]

  .map(function(p){return new THREE.Vector2(p[0],p[1]);});

 var glass=new THREE.Mesh(new THREE.LatheGeometry(profile,26),

  new THREE.MeshPhysicalMaterial({

   color:0xaedcd2,transmission:.86,thickness:1.1,roughness:.09,metalness:0,ior:1.44,

   transparent:true,opacity:1,side:THREE.DoubleSide,clearcoat:.55,clearcoatRoughness:.28,

   envMap:envTex,envMapIntensity:1.15}));

 glass.scale.setScalar(scale);grp.add(glass);

 var paper=new THREE.Mesh(new THREE.CylinderGeometry(.26*scale,.3*scale,1.05*scale,10),

  new THREE.MeshStandardMaterial({color:0xe8dcbb,roughness:.9,metalness:0,

   emissive:0x2a2415,emissiveIntensity:.5}));

 paper.position.y=-.28*scale;paper.rotation.z=.12;grp.add(paper);

 var cork=new THREE.Mesh(new THREE.CylinderGeometry(.145*scale,.165*scale,.16*scale,10),

  new THREE.MeshStandardMaterial({color:0x74512e,roughness:.95}));

 cork.position.y=1.4*scale;grp.add(cork);

 /* v4 · 橙色信标环：自发光加强并随昼夜动态调整，任何角度都能认出瓶子 */

 var band=new THREE.Mesh(new THREE.TorusGeometry(.205*scale,.028*scale,8,22),

  new THREE.MeshStandardMaterial({color:0xff7c2d,roughness:.45,metalness:.3,

   emissive:0xff7c2d,emissiveIntensity:.45}));

 band.position.y=1.2*scale;band.rotation.x=Math.PI/2;grp.add(band);

 grp.userData.band=band;

 /* v4 · 隐形命中球：colorWrite=false 任何情况下都不产生颜色（含淡出时），仅参与射线检测 */

 var hit=new THREE.Mesh(new THREE.SphereGeometry(3.2,8,6),

  new THREE.MeshBasicMaterial({transparent:true,opacity:0,depthWrite:false,depthTest:false,colorWrite:false}));

 hit.userData.noFade=true;

 hit.position.y=.1;grp.add(hit);

 return grp;

}

var cards={wrap:document.getElementById('cardWrap'),text:document.getElementById('cardText'),

 no:document.getElementById('cardNo'),close:document.getElementById('closeCard'),

 ttl:document.getElementById('ttl')};

var intro=document.getElementById('intro'),enterBtn=document.getElementById('enterBtn');

var dnEl=document.getElementById('dn'),sigEl=document.getElementById('signal');



var FAST_SEED=(window.FORCE_FAST===true)||/[?&]fast=1/.test(location.search);   /* 调试：?fast=1 或预置 window.FORCE_FAST 让漂流瓶提前现身 */
var st={mode:'OUT',nextIn:FAST_SEED?2.5:26+Math.random()*8,bottle:null,x:0,z:0,zFrom:0,prog:0,ttl:60,lt:0,spin:.14,msg:null,count:0};



function pickMsg(){return MSGS[Math.floor(Math.random()*MSGS.length)];}



function spawnBottle(){

 var lane=[[-5.5,-13.5],[6,-15],[-7,-12.5],[5.5,-14]][Math.floor(Math.random()*4)];

 var g=buildBottleModel(2.9+Math.random()*.5);

 st.x=lane[0]+(Math.random()-.5)*6;st.z=lane[1];

 st.zFrom=st.z-52;

 g.position.set(st.x,1.1,st.zFrom);

 g.rotation.y=Math.random()*Math.PI*2;

 scene.add(g);

 st.bottle=g;st.mode='IN';st.prog=0;st.msg=pickMsg();

}

function openCard(){

 cards.text.textContent=st.msg.t;

 cards.text.className=st.msg.gold?'gold':'';

 cards.no.textContent='BOTTLE №0'+String(179+(++st.count)).slice(-4)+' · SEA MAIL'+(st.msg.gold?' ✦':'');

 cards.wrap.classList.remove('gone');

 st.mode='READ';cards.ttl.textContent='';

}

function releaseBottle(){

 cards.wrap.classList.add('gone');

 if(!st.bottle)return;

 st.mode='LEAVE';st.lt=0;

}

cards.close.addEventListener('click',releaseBottle);

cards.wrap.addEventListener('click',function(e){if(e.target===cards.wrap&&st.mode==='READ')releaseBottle();});

/* 点按开瓶：与拖拽共用一套手势，短触且未滑动才算点击（手机友好） */

canvas.addEventListener('pointerup',function(ev){

 if((!FINE&&camCtl.moved>9)||st.mode!=='IDLE'||!st.bottle)return;   /* 桌面点击免滑动判定 */

 var rc=new THREE.Raycaster();

 rc.setFromCamera(new THREE.Vector2(ev.clientX/W*2-1,-(ev.clientY/H)*2+1),cam);

 if(rc.intersectObject(st.bottle,true).length)openCard();

});

/* ───────────── 主题联动 ─────────────

   hash #night/#day > 站点主题 class > 默认昼 */

var seed=null;

try{if(location.hash==='#night')seed='night';

    else if(location.hash==='#day')seed='day';}catch(e0){}

var uDayTarget=(seed==='night')?0:(seed==='day')?1:

 (document.documentElement.classList.contains('dark')?0:1);

function applySeaTheme(){

 if(seed)return;

 uDayTarget=document.documentElement.classList.contains('dark')?0:1;

}

applySeaTheme();

window.__setTheme=function(){

 var root=document.documentElement,key='deon-theme';

 var th=root.classList.contains('dark')?'light':'dark';

 try{localStorage.setItem(key,th);}catch(e3){}

 root.classList.toggle('dark',th==='dark');

 document.dispatchEvent(new CustomEvent('deon-theme',{detail:th}));applySeaTheme();

};

document.getElementById('seaThemeBtn').addEventListener('click',window.__setTheme);

document.addEventListener('deon-theme',applySeaTheme);

/* ───────────── 相机 v4：第一人称环视 ─────────────

   桌面（精确指针）：移动鼠标即环顾四周，指向哪看到哪，点击即可开瓶

   触屏：按住拖动、景色跟手；短按开瓶                                */

var FINE=window.matchMedia&&matchMedia('(hover: hover) and (pointer: fine)').matches;

/* v5 · 视野增幅收紧：只允许几度的环视（桌面 hover / 移动拖拽共用上限），移动端松手回正 */
var MAX_YAW=.085,MAX_PIT=.05;
var camCtl={baseYaw:0,basePit:.065,offYaw:0,offPit:0,yaw:0,pitch:.065,down:false,lx:0,ly:0,moved:0};

function clampPitch(p){return Math.max(-.12,Math.min(1.02,p));}

canvas.style.touchAction='none';

canvas.addEventListener('pointerdown',function(ev){

 if(FINE&&ev.pointerType==='mouse')return;            /* 桌面无需按住拖拽 */

 if(ev.button!==undefined&&ev.button!==0)return;

 camCtl.down=true;camCtl.moved=0;

 camCtl.lx=ev.clientX;camCtl.ly=ev.clientY;

 if(canvas.setPointerCapture){try{canvas.setPointerCapture(ev.pointerId);}catch(eP){}}

});

addEventListener('pointermove',function(ev){

 if(FINE&&ev.pointerType==='mouse'){                  /* hover 环视：指哪看哪 */

  camCtl.offYaw=-((ev.clientX/W)*2-1)*MAX_YAW;

  camCtl.offPit=-((ev.clientY/H)*2-1)*MAX_PIT;

  return;

 }

 if(!camCtl.down)return;

 var dx=ev.clientX-camCtl.lx,dy=ev.clientY-camCtl.ly;

 camCtl.lx=ev.clientX;camCtl.ly=ev.clientY;

 camCtl.moved+=Math.abs(dx)+Math.abs(dy);

 camCtl.baseYaw=Math.max(-MAX_YAW,Math.min(MAX_YAW,camCtl.baseYaw+dx*.0031));                            /* 跟手：景色随手指方向移动 */

 camCtl.basePit=Math.max(.065-MAX_PIT*1.6,Math.min(.065+MAX_PIT*1.6,camCtl.basePit+dy*.0024));

});

function endDrag(){camCtl.down=false;}

addEventListener('pointerup',endDrag);

addEventListener('pointercancel',endDrag);

addEventListener('blur',endDrag);

function placeCamera(t,dt){

 if(!FINE){                                    /* 触屏：松手缓动回正，空闲时轻微巡游 */
 if(camCtl.down){camCtl.baseYaw+=Math.sin(t*.042)*.00028;}
 else{
  var kr=Math.min(dt*2.2,1),kr2=Math.min(dt*3.2,1);
  camCtl.baseYaw+=(0-camCtl.baseYaw)*kr;
  camCtl.basePit+=(.065-camCtl.basePit)*kr;
  camCtl.offYaw+=(0-camCtl.offYaw)*kr2;
  camCtl.offPit+=(0-camCtl.offPit)*kr2;
 }
}

 var k=Math.min(dt*7,1),

     ty=camCtl.baseYaw+camCtl.offYaw,

     tp=clampPitch(camCtl.basePit+camCtl.offPit);

 camCtl.yaw+=(ty-camCtl.yaw)*k;

 camCtl.pitch+=(tp-camCtl.pitch)*k;

 cam.position.set(Math.sin(t*.31)*.9,9.6+Math.sin(t*.52)*.32,4);  /* 随涌浪轻微起伏漂移 */

 cam.rotation.set(camCtl.pitch,camCtl.yaw,Math.sin(t*.23)*.006,'YXZ');

 cam.getWorldPosition(waterUniforms.uCamPos.value);

}

/* ───────────── HUD 深度计 ───────────── */

var dn=4.2;

setInterval(function(){

 if(st.mode==='OUT'||st.mode==='IN'||document.hidden)return;

 dn+=(Math.random()-.48)*.4;dn=Math.max(.01,Math.min(96.3,dn));

 dnEl.textContent=dn.toFixed(2).padStart(5,'0');

 if(Math.random()<.07)sigEl.textContent=[

  'SIGNAL ▂▃▅ STABLE','SIGNAL ▁▂▄ DRIFTING',' Something moved under you.',

  'NODES 179 ONLINE','水的记忆正在上传……'][Math.floor(Math.random()*5)];

},900);

/* ───────────── 瓶子状态机 ───────────── */

function esh(x){x=Math.max(0,Math.min(1,x));return x*x*(3-2*x);}

function stepBottle(t,dt){

 switch(st.mode){

  case 'OUT':

   cards.ttl.textContent='';

   st.nextIn-=dt;

   if(st.nextIn<=0)spawnBottle();

   break;

  case 'IN':                                     /* 从远处漂来 */

   st.prog+=dt/7.5;

   var kk=esh(st.prog);

   st.bottle.position.z=st.zFrom+(st.z-st.zFrom)*kk;

   st.bottle.position.x=st.x+Math.sin(st.prog*5)*3*(1-kk);

   st.bottle.position.y=1.28+Math.sin(t*1.3)*.18;   /* v4 · 浮力平衡点上移，瓶身半露易于辨认 */

   st.bottle.rotation.y+=dt*.16;

   st.bottle.rotation.z=Math.sin(t*.9)*.08;

   if(st.prog>=1){st.mode='IDLE';st.ttl=60;}

   break;

  case 'IDLE':                                   /* 停驻等待点击 */

   st.ttl-=dt;

   st.bottle.position.y=1.32+Math.sin(t*1.05)*.16;

   st.bottle.rotation.x=Math.sin(t*.8)*.06;

   st.bottle.rotation.y+=dt*st.spin;

   cards.ttl.textContent='最近一瓶自沉倒计时 · '+Math.ceil(Math.max(st.ttl,0))+'s';

   if(st.ttl<=0)releaseBottle();

   break;

  case 'READ':                                    /* 阅读中暂停计时 */

   st.bottle.position.y=1.42+Math.sin(t*.7)*.08;

   break;

  case 'LEAVE':                                   /* 漂走并淡出 */

   st.lt+=dt;

   var kl=st.lt;

   st.bottle.position.z+=dt*(6+kl*9);

   st.bottle.position.y-=dt*kl*.3;

   st.bottle.rotation.z+=dt*kl*.4;

   st.bottle.rotation.y+=dt*1.6;

   var fade=Math.max(0,1-kl/5.5);

   st.bottle.traverse(function(o){

    if(o.material&&!o.userData.noFade){o.material.transparent=true;o.material.opacity=fade;}});

   if(kl>=5.5){

    scene.remove(st.bottle);

    st.bottle.traverse(function(o){

     if(o.geometry)o.geometry.dispose();

     if(o.material)o.material.dispose();});

     st.bottle=null;st.mode='OUT';st.nextIn=FAST_SEED?3.5:20+Math.random()*16;

   }

   break;

 }

}

/* v4 · 触手全程潜于水下，仅做深浅呼吸式浮动 */

function animTentacles(t,dt){

 for(var k=0;k<tentacles.length;k++){

  var tc=tentacles[k],ud=tc.userData;

  tc.material.uniforms.uTime.value=t;

  tc.position.y=ud.baseY+Math.sin(t*ud.spd+ud.ph)*1.7;

  tc.rotation.z=Math.sin(t*.16+ud.ph)*.05;

 }

}

/* ───────────── 渲染主循环（双 pass 分层） ───────────── */

var sunDay=new THREE.Vector3(-.34,.33,-.88).normalize();

var sunNight=new THREE.Vector3(.30,.36,-.88).normalize();

var last=performance.now(),frameAcc=0,frameN=0,degraded=false;



function _tickBody(now){

 var dt=Math.min((now-last)/1000,.05);last=now;

 if(document.hidden)return;

 var t=now/1000;



 /* 昼夜插值 */

 var cur=waterUniforms.uDay.value;

 var nv=cur+(uDayTarget-cur)*Math.min(dt*1.3,1);

 waterUniforms.uDay.value=nv;

 skyUniforms.uDay.value=nv;

 uwDomeMat.uniforms.uDay.value=nv;

 moteMat.uniforms.uDay.value=nv;

 for(var q=0;q<rays.length;q++)rays[q].material.uniforms.uDay.value=nv;

 for(var q2=0;q2<tentacles.length;q2++)tentacles[q2].material.uniforms.uDay.value=nv;

 skyUniforms.uSunDir.value.copy(sunDay).lerp(sunNight,1-nv).normalize();

 if(st.bottle&&st.bottle.userData.band)

  st.bottle.userData.band.material.emissiveIntensity=.42+(1-nv)*.85;   /* 夜里信标更亮 */



 waterUniforms.uTime.value=t;

 skyUniforms.uTime.value=t;

 uwDomeMat.uniforms.uTime.value=t;

 moteMat.uniforms.uTime.value=t;

 for(var q3=0;q3<rays.length;q3++)rays[q3].material.uniforms.uTime.value=t;

 for(var q4=0;q4<tentacles.length;q4++)tentacles[q4].material.uniforms.uTime.value=t;

 waterUniforms.useres.value.set(W*renderer.getPixelRatio(),H*renderer.getPixelRatio());



 placeCamera(t,dt);

 animTentacles(t,dt);

 stepBottle(t,dt);



 /* pass1 : 折射层 RT —— 仅渲染 layer1（穹顶背景×光柱×荧光尘埃） */

 water.visible=false;

 if(st.bottle)st.bottle.visible=false;

 cam.layers.set(1);

 renderer.setRenderTarget(rt);

 renderer.render(scene,cam);

 /* pass2 : 主屏 —— 天空 + 水下实体触手(直视可见) + 半透明水面 + 瓶子 */

 cam.layers.set(0);

 water.visible=true;

 if(st.bottle)st.bottle.visible=true;

 renderer.setRenderTarget(null);

 renderer.render(scene,cam);



 /* 性能看门狗：平均帧时超标则降 DPR */

 frameAcc+=dt;frameN++;

 if(frameN>=90&&!degraded&&frameAcc/frameN>.05){

  degraded=true;renderer.setPixelRatio(Math.max(1,DPR_BASE-.7));onResize();

 }

 if(frameN>=90){frameAcc=0;frameN=0;}

}

function tick(now){

 requestAnimationFrame(tick);

 try{_tickBody(now);}catch(err9){}

}



function onResize(){

 W=innerWidth;H=innerHeight;

 renderer.setSize(W,H,false);

 cam.aspect=W/H;cam.updateProjectionMatrix();

 var pr=renderer.getPixelRatio();

 rt.setSize(Math.max(320,Math.floor(W*pr*RT_SCALE)),Math.max(240,Math.floor(H*pr*RT_SCALE)));

}

addEventListener('resize',onResize);



/* 进入方式：?auto=1 自动下潜；否则点击 ENTER */

/* v4 · 底部提示按输入方式自适应 */

var iFoot=document.querySelector('.ifoot');

if(iFoot)iFoot.textContent=FINE?

 'WEBGL REQUIRED · MOVE MOUSE TO LOOK · CLICK A DRIFTING BOTTLE':

 'WEBGL REQUIRED · DRAG TO LOOK · TAP A DRIFTING BOTTLE';

function begin(){intro.classList.add('gone');}

if(/[?&]auto=1/.test(location.search)){

 setTimeout(begin,500);

}else{

 enterBtn.addEventListener('click',begin);

}

requestAnimationFrame(tick);

})();

