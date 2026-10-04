let lang=localStorage.kl||"en",tok=localStorage.kt||"",user=null,page="dashboard",charts=[],stream=null,fs=+(localStorage.kfs||16);
const esc=x=>String(x??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const $=s=>document.querySelector(s),t=k=>I18N[lang][k]||k,L=o=>o&&typeof o==="object"?(o[lang]||o.en):o;
const NAV=[["g_learn",[["learn","📚"],["toolkit","🧰"]]],["g_farm",[["dashboard","🏠"],["water","💧"],["crop","📷"]]],["g_grid",[["solar","☀️"]]],["g_fin",[["insurance","🛡️"],["credit","💳"],["carbon","🌱"],["schemes","🏛️"]]],["g_gov",[["officer","📊"]]]];
async function api(p,o={}){const h=o.body instanceof FormData?{}:{"Content-Type":"application/json"};if(tok)h.Authorization="Bearer "+tok;
 const r=await fetch("/api/"+p,{...o,headers:h,body:o.body&&!(o.body instanceof FormData)?JSON.stringify(o.body):o.body});
 if(r.status==401&&p!="login"){logout(true);throw 0}const j=await r.json();if(!r.ok)throw j;return j}
function kill(){charts.forEach(c=>c.destroy());charts=[];if(stream){stream.getTracks().forEach(x=>x.stop());stream=null}}
function chart(id,cfg){charts.push(new Chart($("#"+id),{...cfg,options:{responsive:true,maintainAspectRatio:false,...cfg.options}}))}
function shell(inner){document.documentElement.style.fontSize=fs+"px";document.documentElement.lang=lang;
 $("#root").innerHTML=`<div class="tri"></div><div class="util"><span>🇮🇳 ${t("proto")}</span><span>
 <button onclick="fsz(-1)">A-</button> <button onclick="fsz(0)">A</button> <button onclick="fsz(1)">A+</button>
 <button class="${lang=="en"?"on":""}" onclick="setL('en')">EN</button> <button class="${lang=="hi"?"on":""}" onclick="setL('hi')">हिं</button></span></div>
 <header class="gov"><div class="logo">☀️</div><div><b>${t("brand")}</b><small>${t("tag")}</small></div><div class="sp"></div>
 <div class="badge-gov">Digital India · PM-KUSUM · Atmanirbhar Krishi</div></header>${inner}${footer()}`}
const fsz=d=>{fs=d?Math.max(13,Math.min(21,fs+d)):16;localStorage.kfs=fs;boot()};
const setL=l=>{lang=l;localStorage.kl=l;boot()};
function footer(){return `<footer><div class="cols"><div><h4>${t("brand")}</h4>${t("f_text")}</div>
<div><h4>${t("f_links")}</h4><a href="https://pmkusum.mnre.gov.in" target=_blank>PM-KUSUM · MNRE</a><a href="https://pmfby.gov.in" target=_blank>PM Fasal Bima</a><a href="https://pmkisan.gov.in" target=_blank>PM-KISAN</a><a href="https://enam.gov.in" target=_blank>e-NAM</a><a href="https://soilhealth.dac.gov.in" target=_blank>Soil Health Card</a></div>
<div><h4>${t("f_help")}</h4>${t("helpline")}<br>PM-KUSUM: 1800-180-3333</div>
<div><h4>${t("f_about")}</h4>Photos: Flickr (Creative Commons) via loremflickr · replace in images.js<br>DPDP Act 2023 · Account Aggregator consent · MeghRaj-ready<br>© 2026 KisanUrja Grid</div></div><div class="bot">Made for Digital India · Data localisation: ap-south-1 (Mumbai)</div></footer>`}
function sidebar(){let h=`<nav class="side">`;NAV.forEach(([g,items])=>{const its=items.filter(([p])=>p!="officer"||user.role=="officer");if(!its.length)return;h+=`<div class="grp">${t(g)}</div>`;
 its.forEach(([p,i])=>h+=`<a class="${p==page?"on":""}" onclick="go('${p}')">${i} ${t(p)}</a>`)});
 return h+`<div class="me"><b>${esc(user.name)}</b><br><span class="mute">${user.role=="officer"?"DISCOM":esc(user.district)+", "+esc(user.state)}</span><br><button class="btn o" style="margin-top:8px;color:#fff;border-color:#4f8" onclick="logout()">${t("logout")}</button></div></nav>`}
const go=p=>{page=p;render()};
function logout(q){botHide();if(!q)api("logout",{method:"POST"}).catch(()=>{});tok="";localStorage.kt="";user=null;boot()}
function img(k,n,cls=""){return `<div class="im ${cls}" style="background-image:url('${IMG(k,n)}'),linear-gradient(135deg,#2c7a5a,#e8871e)"></div>`}
const gallery=l=>`<div class="photos mt">${l.map(([k,n])=>`<div class="im" style="background-image:url('${IMG(k,n)}'),linear-gradient(135deg,#2c7a5a,#e8871e)"></div>`).join("")}</div>`;
const kpi=(i,v,l)=>`<div class="card kpi"><i>${i}</i><b>${v}</b><span>${l}</span></div>`;
function gauge(v,max,lab,col="#165a43"){const p=Math.min(1,v/max),a=Math.PI*(1-p),x=100+80*Math.cos(a),y=100-80*Math.sin(a);
 return `<svg viewBox="0 0 200 120" width="220"><path d="M20 100A80 80 0 0 1 180 100" fill="none" stroke="#ece5d0" stroke-width="16" stroke-linecap="round"/><path d="M20 100A80 80 0 0 1 ${x} ${y}" fill="none" stroke="${col}" stroke-width="16" stroke-linecap="round"/><text x="100" y="92" text-anchor="middle" font-family="Fraunces" font-size="34" font-weight="800" fill="#0e3b2c">${v}</text><text x="100" y="112" text-anchor="middle" font-size="11" fill="#6b7a72">${lab}</text></svg>`}

/* ---------- login ---------- */
let mode="login",otpSent=false;
function loginView(){shell(`<div class="login"><div class="l" style="background-image:url('${IMG("solar,farm,india",11,1000,800)}')"><div><h1>${t("hero_t")}</h1><p>${t("hero_d")}</p>
<p class="flow"><span>☀️ ${t("flow1")}</span>→<span>📟 ${t("flow2")}</span>→<span>⚙️ ${t("flow3")}</span>→<span>₹ ${t("flow4")}</span>→<span>📈 ${t("flow5")}</span></p></div></div>
<div class="r"><div class="box"><div class="chips"><span class="chip ${mode=="login"?"on":""}" onclick="mode='login';loginView()">${t("login")}</span><span class="chip ${mode=="otp"?"on":""}" onclick="mode='otp';otpSent=false;loginView()">${t("otp")}</span><span class="chip ${mode=="register"?"on":""}" onclick="mode='register';loginView()">${t("register")}</span></div>
<div id="err" class="pill b" style="display:none"></div>
${mode=="register"?`<label>${t("name")}</label><input id="n">`:""}<label>${t("phone")}</label><input id="p" inputmode="numeric" value="${mode!="register"?"9999900001":""}">${mode=="otp"?(otpSent?`<label>OTP</label><input id="o" inputmode="numeric" maxlength="6"><p class="pill w">${t("devotp")}: ${otpSent}</p>`:""):`<label>${t("pass")}</label><input id="w" type="password" value="${mode=="login"?"demo123":""}">`}
${mode=="register"?`<div class="row"><div style="flex:1"><label>${t("state")}</label><input id="st" value="Punjab"></div><div style="flex:1"><label>${t("district")}</label><input id="di"></div></div>
<div class="row"><div style="flex:1"><label>${t("land")}</label><input id="la" type="number" value="3"></div><div style="flex:1"><label>${t("cropn")}</label><select id="cr"><option>Paddy<option>Wheat<option>Cotton<option>Maize</select></div></div>
<div class="row"><div style="flex:1"><label>${t("pump")}</label><input id="pk" type="number" value="5"></div><div style="flex:1"><label>${t("solark")}</label><input id="sk" type="number" value="0"></div></div>`:""}
<button class="btn s" style="width:100%;margin-top:16px" onclick="doAuth()">${mode=="otp"?(otpSent?t("verify"):t("sendotp")):t(mode)}</button>
<p class="mute" style="font-size:.8rem">${t("demo")}: 9999900001 (farmer) · 9999900002 (officer) · demo123</p></div></div></div>`)}
async function doAuth(){const v=i=>$("#"+i)?.value;try{
 if(mode=="otp"&&!otpSent){const r=await api("otp/request",{method:"POST",body:{phone:v("p")}});otpSent=r.dev_otp||"SMS";const ph=v("p");loginView();$("#p").value=ph;return}
 if(mode=="otp"){const r=await api("otp/verify",{method:"POST",body:{phone:v("p"),code:v("o")}});tok=r.token;localStorage.kt=tok;user=r.user;page=user.role=="officer"?"officer":"dashboard";return render()}const b=mode=="login"?{phone:v("p"),password:v("w")}:{name:v("n"),phone:v("p"),password:v("w"),state:v("st"),district:v("di"),land:v("la"),crop:v("cr"),pump_kw:v("pk"),solar_kw:v("sk")};
 const r=await api(mode,{method:"POST",body:b});tok=r.token;localStorage.kt=tok;user=r.user;page=user.role=="officer"?"officer":"dashboard";render()}catch(e){const x=$("#err");x.style.display="inline-block";x.textContent=e.error||t("invalid")}}

/* ---------- pages ---------- */
const P={};
function render(){kill();botMount();shell(`<div class="app">${sidebar()}<main id="view"></main></div>`);P[page]().catch(e=>{if(e)$("#view").innerHTML=`<div class="card">${t("err")}</div>`})}
P.dashboard=async()=>{const d=await api("dashboard"),a=d.tip,w=a.weather,s=d.stress,k=d.kpi;
 $("#view").innerHTML=`<div class="hero" style="background-image:url('${IMG("indian,farmer,wheat,field",21,1200,500)}')"><div><h1>${t("hello")}, ${esc(user.name.split(" ")[0])} 🙏</h1><p>${t("hero_d")}</p></div></div>
 <div class="grid g4">${kpi("☀️",k.solar_kwh,t("k_sol")+" · kWh")}${kpi("🔌",k.grid_kwh,t("k_grid")+" · kWh")}${kpi("💰","₹"+k.saved_inr.toLocaleString("en-IN"),t("k_sav"))}${kpi("💧",k.water_kl,t("k_wat")+" · kL")}</div>
 <div class="grid g2 mt"><div class="card"><h2>${t("today")}</h2><p><span class="pill ${a.action=="WAIT"?"w":""}">${a.action=="WAIT"?t("wait"):t("water_now")}</span></p><p style="font-size:1.1rem"><b>${a[lang]}</b></p>
  <div class="row"><div>🌱 ${t("moist")}: <b>${a.moisture}%</b><div class="bar" style="width:140px"><i style="width:${a.moisture}%"></i></div></div><div>🌧️ ${t("rain")}: <b>${w.rain_mm} mm</b> · ${w.temp}°C</div><div>${t("tomorrow")}: ${a.tomorrow.rain_mm} mm</div></div>
  <p class="mute">${t("best")}: ${a.best_hours.map(h=>h+":00").join(", ")}</p></div>
 <div class="card tc"><h2>${t("stress")}</h2>${gauge(s.stress,100,"/100",s.stress>66?"#c0392b":s.stress>40?"#e8871e":"#2e8b57")}<p class="mute">${t("block")}: <b>${s.block}</b></p></div></div>
 <div class="card mt"><h2>${t("trend")}</h2><div class="chart"><canvas id="c1"></canvas></div></div>
 <div class="row mt">${[["solar,panel,irrigation,pump",31],["drip,irrigation,crop",32],["indian,farmer,smile",33]].map(x=>`<div class="card" style="flex:1;min-width:200px;padding:0;overflow:hidden">${img(x[0],x[1])}</div>`).join("")}</div>`;
 chart("c1",{type:"line",data:{labels:d.series.map(x=>x.day.slice(5)),datasets:[{label:"Solar",data:d.series.map(x=>x.solar),borderColor:"#e8871e",backgroundColor:"#e8871e33",fill:true,tension:.35},{label:"Grid",data:d.series.map(x=>x.grid),borderColor:"#1f5fa8",tension:.35}]}})};
P.solar=async()=>{let day=new Date().toISOString().slice(0,10);const days=[0,1,2].map(i=>new Date(Date.now()+i*864e5).toISOString().slice(0,10));
 const draw=async d=>{const s=await api("solar/simulate?day="+d),T=s.totals;const led=await api("solar/ledger");
 $("#view").innerHTML=`<div class="hero" style="background-image:url('${IMG("solar,panels,field",41,1200,500)}')"><div><h1>${t("sol_t")}</h1><p>${t("sol_d")}</p></div></div>
 <p class="flow"><span>☀️ ${t("flow1")}</span>→<span>📟 ${t("flow2")}</span>→<span>⚙️ ${t("flow3")}</span>→<span>₹ ${t("flow4")}</span>→<span>📈 ${t("flow5")}</span></p>
 <div class="chips">${days.map(x=>`<span class="chip ${x==d?"on":""}" onclick="window.sd('${x}')">${x==days[0]?t("today"):x.slice(5)}</span>`).join("")}<span class="mute">☁️ ${Math.round(s.weather.cloud*100)}% · 🌧️ ${s.weather.rain_mm}mm</span></div>
 <div class="grid g4">${kpi("🏭",s.plant_kw+" kW",t("plant"))}${kpi("⚡",T.solar_served+" kWh",t("solsrv"))}${kpi("🔌",T.grid+" kWh",t("gridneed"))}${kpi("💰","₹"+T.saved_inr.toLocaleString("en-IN"),t("k_sav"))}${kpi("📈",T.utilisation+"%",t("utili"))}${kpi("⚖️",T.fairness,t("fair"))}${kpi("🌍",T.co2_kg+" kg",t("co2"))}</div>
 ${gallery([["solar,panels,field",201],["solar,farm,india",202],["irrigation,farm,water",203],["indian,farmer,smile",204]])}
 <div class="card mt"><h2>${t("hourly")}</h2><div class="chart"><canvas id="c2"></canvas></div></div>
 <div class="grid g2 mt"><div class="card"><h2>${t("members")}</h2><div style="overflow:auto"><table><tr><th>${t("member")}<th>${t("demand")}<th>${t("solarc")}<th>${t("gridc")}<th>${t("cost")}</tr>${s.members.map(m=>`<tr><td>${esc(m.name)}<div class="bar"><i style="width:${100*m.solar/Math.max(.01,m.demand)}%"></i></div><td>${m.demand}<td>${m.solar}<td>${m.grid}<td>${m.cost}</tr>`).join("")}</table></div></div>
 <div class="card"><h2>${t("ledger")}</h2><button class="btn s" onclick="window.st('${d}')">₹ ${t("settle")}</button><div style="max-height:330px;overflow:auto"><table>${led.slice(0,14).map(l=>`<tr><td>${l.day.slice(5)}<td>${esc(l.name)}<td>${l.kwh} kWh<td><b>₹${l.amount}</b><td class="mute">${l.ref}</tr>`).join("")||`<tr><td class="mute">—</tr>`}</table></div></div></div>`;
 kill();const H=s.hourly;chart("c2",{data:{labels:H.map(x=>x.h+":00"),datasets:[{type:"bar",label:"Solar served",data:H.map(x=>x.served),backgroundColor:"#e8871e",stack:"a"},{type:"bar",label:"Grid backup",data:H.map(x=>x.grid),backgroundColor:"#1f5fa8",stack:"a"},{type:"line",label:"Plant output",data:H.map(x=>x.supply),borderColor:"#165a43",tension:.4,pointRadius:0}]},options:{scales:{x:{stacked:true},y:{stacked:true}}}})};
 window.sd=draw;window.st=async d=>{await api("solar/settle",{method:"POST",body:{day:d}});draw(d)};draw(day)};
P.water=async()=>{const d=await api("water"),s=d.stress,a=d.advisor;
 $("#view").innerHTML=`<div class="hero" style="background-image:url('${IMG("irrigation,farm,water",51,1200,500)}')"><div><h1>${t("wtr_t")}</h1><p>${t("hero_d")}</p></div></div>
 <div class="grid g3"><div class="card tc"><h2>${t("stress")}</h2>${gauge(s.stress,100,"/100",s.stress>66?"#c0392b":"#e8871e")}</div>
 <div class="card"><h2>${t("over")}</h2><p style="font-size:2rem;margin:6px 0"><b>${s.per_acre}</b> <small class="mute">${t("per_acre")}</small></p><p>${t("need")}: ${s.crop_need} · ×${s.ratio}</p><p>${t("block")}: <span class="pill b">${s.block}</span></p></div>
 <div class="card"><h2>${t("today")}</h2><span class="pill ${a.action=="WAIT"?"w":""}">${a.action=="WAIT"?t("wait"):t("water_now")}</span><p><b>${a[lang]}</b></p><p class="mute">${t("moist")} ${a.moisture}%</p></div></div>
 <div class="card mt"><h2>${t("trend")} / kL</h2><div class="chart"><canvas id="c3"></canvas></div></div>
 ${gallery([["irrigation,farm,water",211],["crop,leaf,plant",212],["indian,farmer,wheat,field",213]])}<div class="card mt"><h2>${t("anom")}</h2>${d.anomalies.length?d.anomalies.map(x=>`<p>⚠️ ${esc(x.day)} · z=${x.z}</p>`).join(""):`<p>✅ ${t("noanom")}</p>`}</div>`;
 chart("c3",{type:"bar",data:{labels:d.series.map(x=>x.day.slice(5)),datasets:[{label:"Water kL",data:d.series.map(x=>x.water),backgroundColor:"#1f5fa8aa"},{type:"line",label:"Solar kWh",data:d.series.map(x=>x.solar),borderColor:"#e8871e",pointRadius:0}]}})};
P.crop=async()=>{const h=await api("crop/history");
 $("#view").innerHTML=`<div class="hero" style="background-image:url('${IMG("crop,leaf,plant",61,1200,500)}')"><div><h1>${t("crop_t")}</h1><p>${t("crop_d")}</p></div></div>
 <div class="grid g2"><div class="card"><video id="v" class="cam" autoplay playsinline muted style="display:none"></video><canvas id="cv" style="display:none"></canvas><img id="pv" class="cam" style="display:none">
 <div class="row mt"><button class="btn" onclick="camOn()">📷 ${t("cam_on")}</button><button class="btn s" id="sn" style="display:none" onclick="snap()">${t("snap")}</button><label class="btn o" style="margin:0;cursor:pointer">⬆ ${t("upl")}<input type="file" accept="image/*" id="fi" hidden onchange="upl(this.files[0])"></label></div><p id="ce" class="mute"></p></div>
 <div class="card" id="res"><p class="mute">🌿 …</p></div></div>
 <div class="card mt"><h2>${t("hist")}</h2><div class="row">${h.map(x=>`<span class="pill ${x.key=="healthy"?"":"w"}">${x[lang]} · ${x.health}</span>`).join("")}</div></div>`;
 window.camOn=async()=>{try{stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:"environment"}});const v=$("#v");v.srcObject=stream;v.style.display="block";$("#pv").style.display="none";$("#sn").style.display="inline-block"}catch{$("#ce").textContent=t("cam_err")}};
 window.snap=()=>{const v=$("#v"),c=$("#cv");c.width=v.videoWidth;c.height=v.videoHeight;c.getContext("2d").drawImage(v,0,0);c.toBlob(b=>upl(b),"image/jpeg",.9)};
 window.upl=async f=>{if(!f)return;const pv=$("#pv");pv.src=URL.createObjectURL(f);pv.style.display="block";$("#v").style.display="none";$("#res").innerHTML=`<p>⏳ ${t("analysing")}</p>`;
  const fd=new FormData();fd.append("image",f,"leaf.jpg");try{const r=await api("crop/analyze",{method:"POST",body:fd});
  $("#res").innerHTML=`<h2>${r[lang]}</h2><span class="pill ${r.key=="healthy"?"":"w"}">${t("conf")} ${Math.round(r.confidence*100)}%</span><div class="row" style="align-items:center">${gauge(r.health,100,t("health"),r.health>65?"#2e8b57":"#e8871e")}<div style="flex:1;min-width:180px">
  ${[["green","#2e8b57"],["yellow","#e8b01e"],["brown","#8b5a2b"]].map(([k,c])=>`<div>${t(k)} ${r.fractions[k]}%<div class="bar"><i style="width:${r.fractions[k]}%;background:${c}"></i></div></div>`).join("")}<small class="mute">${t("coverage")}: ${r.cover}%</small></div></div>
  <p><b>${r["adv_"+lang]}</b></p><small>${t("spots")}: ${r.spots}</small>${r.ai_note?`<div class="card" style="background:#f1f7f3"><b>🤖 ${t("aidet")}</b><br>${esc(r.ai_note).replace(/\n/g,"<br>")}</div>`:""}<small class="mute">${r.engine}</small>`}catch{$("#res").innerHTML=t("err")}}};
P.schemes=async()=>{const S=await api("schemes");let cat="all";const cats=["all",...new Set(S.map(s=>s.cat))];
 const draw=()=>{$("#view").innerHTML=`<div class="hero" style="background-image:url('${IMG("indian,village,farmers",71,1200,500)}')"><div><h1>${t("sch_t")}</h1><p>${t("sch_d")}</p></div></div>
 <div class="chips">${cats.map(c=>`<span class="chip ${c==cat?"on":""}" onclick="window.sc('${c}')">${c=="all"?t("all"):c}</span>`).join("")}</div>
 <div class="grid g3">${S.filter(s=>cat=="all"||s.cat==cat).map((s,i)=>`<div class="card scard">${img(s.img,80+i)}<div class="bd"><div class="row" style="justify-content:space-between"><h2>${L(s.n)}</h2><span class="pill">${s.match}% ${t("match")}</span></div><div class="bar"><i style="width:${s.match}%"></i></div><span class="mute">${L(s.d)}</span>${s.why.map(w=>`<small>✔ ${esc(w)}</small>`).join("")}<a class="btn s" style="margin-top:auto;text-align:center;text-decoration:none" target=_blank href="${s.url}">${t("apply")} ↗</a></div></div>`).join("")}</div>`};
 window.sc=c=>{cat=c;draw()};draw()};
P.insurance=async()=>{
 $("#view").innerHTML=`<div class="hero" style="background-image:url('${IMG("drought,crop,field",121,1200,500)}')"><div><h1>${t("ins_t")}</h1><p>${t("ins_d")}</p></div></div>
 <div class="grid g2"><div class="card"><h2>🌧️ ${t("ins_rain")}: <span id="rv">100</span> mm</h2><input type="range" id="rs" min="0" max="300" value="100" style="padding:0"><p class="mute">${t("ins_hint")}</p></div><div class="card" id="ir"></div></div>`;
 const go2=async()=>{const r=await api("insurance/simulate",{method:"POST",body:{rain_mm:+$("#rs").value}});$("#rv").textContent=r.rain;
  $("#ir").innerHTML=`<span class="pill ${r.triggered?"w":""}">${r.triggered?t("ins_on"):t("ins_off")}</span><p>${t("ins_cov")}: <b>₹${r.insured.toLocaleString("en-IN")}</b> · ${esc(r.crop)} · ${t("ins_th")} ${r.threshold} mm</p><h1>₹${r.payout.toLocaleString("en-IN")}</h1><p class="mute">${t("ins_short")}: ${r.shortfall_pct}%${r.ref?" · UPI "+r.ref:""}</p><small class="mute">${esc(r.source)}</small>`};
 $("#rs").oninput=go2;go2()};
const catImg={Solar:"solar,panel",Schemes:"india,farmers",Water:"irrigation",Credit:"farmer,bank",Crop:"crop,leaf",Insurance:"drought,field"};
P.learn=async(open_)=>{let cat="",qs="";const draw=async()=>{const A=await api("articles?cat="+cat+"&q="+encodeURIComponent(qs)),f=A.find(a=>a.featured);const cats=["","Solar","Schemes","Water","Credit","Crop","Insurance"];
 $("#view").innerHTML=`${f&&!cat&&!qs?`<div class="hero" style="background-image:url('${IMG(f.img,f.id+130,1200,500)}');cursor:pointer" onclick="window.oa(${f.id})"><div><span class="pill w">⭐ ${t("featured")}</span><h1>${L(f.title)}</h1><p>${L(f.summ)}</p></div></div>`:""}
 <div class="row"><input id="qs" style="max-width:320px" placeholder="🔍 ${t("search")}" value="${esc(qs)}" onchange="window.qq(this.value)"></div>
 <div class="chips">${cats.map(c=>`<span class="chip ${c==cat?"on":""}" onclick="window.cc('${c}')">${c||t("all")}</span>`).join("")}</div>
 <div class="grid g3">${A.map(a=>`<div class="card scard" style="cursor:pointer" onclick="window.oa(${a.id})">${img(a.img,a.id+130)}<div class="bd"><span class="pill">${a.cat} · ${a.mins} min</span><h2>${L(a.title)}</h2><span class="mute">${L(a.summ)}</span></div></div>`).join("")||`<p class="mute">—</p>`}</div>
 <div class="card mt"><h2>🔗 ${t("official")}</h2><div class="row"><a href="https://mnre.gov.in" target=_blank>MNRE</a><a href="https://pmkusum.mnre.gov.in" target=_blank>PM-KUSUM</a><a href="https://farmer.gov.in" target=_blank>farmer.gov.in</a><a href="https://icar.org.in" target=_blank>ICAR</a><a href="https://mausam.imd.gov.in" target=_blank>IMD Mausam</a><a href="https://cgwb.gov.in" target=_blank>CGWB</a></div></div>`};
 window.cc=c=>{cat=c;draw()};window.qq=v=>{qs=v;draw()};
 window.oa=async id=>{const a=await api("articles/"+id);$("#view").innerHTML=`<button class="btn o" onclick="go('learn')">← ${t("back")}</button><div class="hero mt" style="background-image:url('${IMG(a.img,a.id+130,1200,500)}')"><div><span class="pill">${a.cat} · ${a.mins} min</span><h1>${L(a.title)}</h1></div></div><div class="card" style="max-width:760px;font-size:1.05rem;line-height:1.7"><div class="photos" style="margin-bottom:12px">${[1,2,3].map(i=>`<div class="im" style="background-image:url('${IMG(a.img,a.id*10+i)}')"></div>`).join("")}</div>${a.body[lang].map(p=>`<p>${esc(p)}</p>`).join("")}<button class="btn s" onclick="go('${a.cta}')">${t("tryit")} → ${t(a.cta)}</button></div>`};
 await draw()};
P.toolkit=async()=>{
 $("#view").innerHTML=`<div class="hero" style="background-image:url('${IMG("solar,pump,irrigation",141,1200,500)}')"><div><h1>🧰 ${t("tk_t")}</h1><p>${t("tk_d")}</p></div></div>
 <div class="grid g2"><div class="card">${[["flow",30,"tk_flow"],["head",40,"tk_head"],["hours",6,"tk_hrs"],["days",200,"tk_days"],["diesel",92,"tk_dsl"]].map(([k,v,l])=>`<label>${t(l)}</label><input id="t_${k}" type="number" value="${v}">`).join("")}<button class="btn s mt" onclick="window.tk()">${t("calc")}</button></div><div class="card" id="tr"><p class="mute">…</p></div></div>`;
 window.tk=async()=>{const b={};["flow","head","hours","days","diesel"].forEach(k=>b[k]=+$("#t_"+k).value);const r=await api("toolkit/solar-pump",{method:"POST",body:b}),n=x=>"₹"+x.toLocaleString("en-IN");
  $("#tr").innerHTML=`<div class="grid g4" style="grid-template-columns:1fr 1fr">${kpi("⚙️",r.pump_hp+" HP",t("tk_pump")+" ("+r.pump_kw+" kW)")}${kpi("☀️",r.panel_kwp+" kWp",t("tk_panel"))}${kpi("💳",n(r.farmer_pays),t("tk_pay")+" ("+n(r.subsidy)+" "+t("tk_sub")+")")}${kpi("⏱️",r.payback_years+" yr",t("tk_back"))}</div><p><b>${t("tk_sav")}: ${n(r.saving_year)}</b> · ${r.diesel_l_year} L · ${r.co2_t_year} t CO₂</p><small class="mute">${r.assumptions.map(esc).join(" · ")}</small>`};tk()};
P.credit=async()=>{const c=await api("credit");
 $("#view").innerHTML=`<div class="hero" style="background-image:url('${IMG("india,farmer,bank,rupees",91,1200,500)}')"><div><h1>${t("cr_t")}</h1><p>${t("cr_d")}</p></div></div>
 <div class="grid g2"><div class="card tc">${gauge(c.score-300,600,c.band)}<h1 style="margin-top:-6px">${c.score}</h1><p>${t("lim")}: <b>₹${c.eligible_limit.toLocaleString("en-IN")}</b></p><small class="mute">${c.note}</small><br><small class="mute">🤖 ${esc(c.model)} · ${t("pd")} ${c.pd}%</small></div>
 <div class="card">${c.factors.map(f=>`<p><b>${L(f)}</b> · ${f.points}/${f.max} ${t("pts")}<div class="bar"><i style="width:${100*f.points/f.max}%"></i></div></p>`).join("")}</div></div>`};
P.carbon=async()=>{const c=await api("carbon");
 $("#view").innerHTML=`<div class="hero" style="background-image:url('${IMG("green,farm,sunrise",101,1200,500)}')"><div><h1>${t("ca_t")}</h1><p>${t("ca_d")}</p></div></div>
 <div class="grid g4">${kpi("🌱",c.score+"/100","Score")}${kpi("☀️",c.solar_kwh,t("c_sol"))}${kpi("🛢️",c.diesel_l,t("c_dsl"))}${kpi("🌍",c.co2_t,t("c_co2"))}${kpi("💧",c.water_saved_kl,t("c_wat"))}${kpi("₹","₹"+c.credit_inr,t("c_inr"))}</div>`};
P.officer=async()=>{if(user.role!="officer"){page="dashboard";return P.dashboard()}const d=await api("officer/overview"),T=d.sim;
 $("#view").innerHTML=`<div class="hero" style="background-image:url('${IMG("power,grid,substation,india",111,1200,500)}')"><div><h1>${t("of_t")}</h1><p>${t("of_d")}</p></div></div>
 <div class="grid g4">${kpi("👨‍🌾",d.farmers.length,t("member"))}${kpi("⚡",T.solar_served+" kWh",t("solsrv"))}${kpi("💰","₹"+T.saved_inr,t("k_sav"))}${kpi("🌍",T.co2_kg+" kg",t("co2"))}</div>
 <div class="card mt"><div class="chart"><canvas id="c4"></canvas></div></div>
 ${gallery([["solar,farm,india",221],["indian,farmer,smile",222],["power,grid,substation,india",223]])}<div class="card mt" style="overflow:auto"><table><tr><th>${t("member")}<th>${t("district")}<th>${t("cropn")}<th>${t("stress")}<th>Solar kWh<th>${t("credit")}</tr>${d.farmers.map(f=>`<tr><td>${esc(f.name)}<td>${esc(f.district)}<td>${esc(f.crop)}<td><span class="pill ${f.stress>66?"b":f.stress>40?"w":""}">${f.stress}</span><td>${f.solar}<td>${f.credit}</tr>`).join("")}</table></div>`;
 chart("c4",{type:"bar",data:{labels:d.farmers.map(f=>f.name.split(" ")[0]),datasets:[{label:t("stress"),data:d.farmers.map(f=>f.stress),backgroundColor:"#c0392baa"},{label:"Solar kWh/10",data:d.farmers.map(f=>f.solar/10),backgroundColor:"#e8871eaa"}]}})};

async function boot(){if(!tok)return loginView();if(!user)try{user=await api("me")}catch{return loginView()}render()}
boot();

/* ---------- floating chatbot ---------- */
let chatLog=[],botOpen=false;
function botHide(){$("#bot").innerHTML="";}
function botMount(){if(!user)return;const sug=lang=="hi"?["आज सिंचाई करूं?","मेरी योजनाएं","लोन सीमा"]:["Should I irrigate today?","Best scheme for me","My loan limit"];
 if(!$("#bot").firstChild)$("#bot").innerHTML=`<div class="botp" id="bp"><header><b>🤖 <span id="bt"></span></b><button onclick="botToggle()" aria-label="close">✕</button></header><div class="chat" id="bch"></div><div class="sug" id="bs"></div><div class="in"><input id="bi" onkeydown="if(event.key=='Enter')botAsk()"><button class="btn o" onclick="botMic()" aria-label="mic">🎤</button><button class="btn s" onclick="botAsk()">➤</button></div></div><button class="fab" onclick="botToggle()" aria-label="Chat">💬</button>`;
 $("#bt").textContent=t("assistant");$("#bi").placeholder=t("as_ph");$("#bs").innerHTML=sug.map(s=>`<span onclick="botAsk(this.textContent)">${s}</span>`).join("");
 if(!chatLog.length)chatLog.push({u:0,en:"Namaste! Ask me about irrigation, schemes, loans or solar.",hi:"नमस्ते! सिंचाई, योजना, ऋण या सौर के बारे में पूछें।"});
 $("#bch").innerHTML=chatLog.map(m=>`<div class="msg ${m.u?"u":""}">${esc(m.u?m.en:m[lang])}</div>`).join("");$("#bp").classList.toggle("open",botOpen);$("#bch").scrollTop=1e5}
function botToggle(){botOpen=!botOpen;$("#bp").classList.toggle("open",botOpen);if(botOpen)$("#bi").focus()}
async function botAsk(m){m=(m||$("#bi").value).trim();if(!m)return;$("#bi").value="";chatLog.push({u:1,en:m});botMount();
 try{const r=await api("chat",{method:"POST",body:{message:m}});chatLog.push({u:0,en:r.en,hi:r.hi})}catch{chatLog.push({u:0,en:t("err"),hi:t("err")})}botMount()}
function botMic(){const R=window.SpeechRecognition||window.webkitSpeechRecognition;if(!R)return;const r=new R();r.lang=lang=="hi"?"hi-IN":"en-IN";r.onresult=e=>botAsk(e.results[0][0].transcript);r.start()}
