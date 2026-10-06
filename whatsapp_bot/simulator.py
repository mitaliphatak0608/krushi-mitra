"""whatsapp_bot/simulator.py - Local WhatsApp simulator with voice/mic button."""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Any
from . import bot_logic, sessions

router = APIRouter()


class SimulateRequest(BaseModel):
    number: str = "91TEST0000001"
    message: str
    lang: str = "hi"


class SimulateResponse(BaseModel):
    reply: str
    lang: str
    state: str
    profile: dict[str, Any]


@router.post("/simulate", response_model=SimulateResponse)
def simulate(body: SimulateRequest) -> SimulateResponse:
    session = sessions.get(body.number)
    if body.lang in ("en", "hi", "mr"):
        session["lang"] = body.lang
        sessions.save(body.number, session)
    reply_text, _ = bot_logic.handle_message(body.number, body.message)
    session = sessions.get(body.number)
    return SimulateResponse(
        reply=reply_text,
        lang=session["lang"],
        state=session["state"],
        profile=session["profile"],
    )


_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Krushi Mitra Simulator</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',sans-serif;background:#e5ddd5;min-height:100vh;display:flex;align-items:center;justify-content:center}
.phone{width:390px;height:820px;background:#fff;border-radius:40px;box-shadow:0 20px 60px rgba(0,0,0,.3);display:flex;flex-direction:column;overflow:hidden;border:8px solid #1a1a1a}
.topbar{background:#075e54;color:#fff;padding:12px 16px;display:flex;align-items:center;gap:12px;flex-shrink:0}
.av{width:40px;height:40px;border-radius:50%;background:#25d366;display:flex;align-items:center;justify-content:center;font-size:20px}
.ti{flex:1}.ti h3{font-size:15px;font-weight:600}.ti p{font-size:12px;opacity:.8}
.ctrl{background:#f0f0f0;padding:8px 12px;display:flex;gap:6px;align-items:center;flex-shrink:0;border-bottom:1px solid #ddd;flex-wrap:wrap}
.ctrl label{font-size:12px;color:#555}
.ctrl select{font-size:12px;padding:4px 8px;border-radius:6px;border:1px solid #ccc;cursor:pointer}
.xbtn{font-size:11px;padding:4px 9px;border-radius:6px;cursor:pointer;border:none;color:#fff}
.chat{flex:1;overflow-y:auto;padding:12px;background:#e5ddd5;display:flex;flex-direction:column;gap:8px}
.bbl{max-width:82%;padding:8px 12px;border-radius:8px;font-size:13.5px;line-height:1.55;word-wrap:break-word}
.bbl .t{font-size:10px;opacity:.6;text-align:right;margin-top:4px}
.ub{background:#dcf8c6;align-self:flex-end;border-bottom-right-radius:2px}
.bb{background:#fff;align-self:flex-start;border-bottom-left-radius:2px;box-shadow:0 1px 2px rgba(0,0,0,.1)}
.vl{font-size:10px;color:#075e54;font-style:italic;margin-bottom:2px}
.typ{display:none;align-self:flex-start;background:#fff;padding:10px 14px;border-radius:8px;border-bottom-left-radius:2px;box-shadow:0 1px 2px rgba(0,0,0,.1)}
.typ span{display:inline-block;width:8px;height:8px;background:#999;border-radius:50%;animation:bn 1.2s infinite;margin:0 2px}
.typ span:nth-child(2){animation-delay:.2s}.typ span:nth-child(3){animation-delay:.4s}
@keyframes bn{0%,60%,100%{transform:translateY(0)}30%{transform:translateY(-6px)}}
.vbar{display:none;background:#e8f5e9;border-top:1px solid #a5d6a7;padding:6px 14px;font-size:12px;color:#2e7d32;flex-shrink:0;align-items:center;gap:8px}
.vbar.on{display:flex}
.vd{width:9px;height:9px;background:#43a047;border-radius:50%;animation:vp 1s infinite}
@keyframes vp{0%,100%{transform:scale(1)}50%{transform:scale(1.3)}}
.chips{display:flex;flex-wrap:wrap;gap:6px;padding:6px 12px;background:#f0f0f0;flex-shrink:0;border-top:1px solid #ddd}
.chip{font-size:11px;padding:4px 10px;border-radius:12px;background:#fff;border:1px solid #25d366;color:#075e54;cursor:pointer;white-space:nowrap}
.chip:hover{background:#e8fce8}
.ibar{background:#f0f0f0;padding:8px 10px;display:flex;gap:6px;align-items:center;flex-shrink:0}
.ibar input{flex:1;border:none;border-radius:20px;padding:10px 14px;font-size:14px;outline:none;background:#fff}
.sbtn{width:44px;height:44px;border-radius:50%;background:#25d366;border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:18px;color:#fff;flex-shrink:0}
.mbtn{width:44px;height:44px;border-radius:50%;background:#075e54;border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0;position:relative;transition:all .2s}
.mbtn.on{background:#e53935;animation:mp 1s infinite}
.mbtn.on::after{content:'';position:absolute;width:56px;height:56px;border:2px solid #e53935;border-radius:50%;animation:rp 1s infinite}
@keyframes mp{0%,100%{transform:scale(1)}50%{transform:scale(1.1)}}
@keyframes rp{0%{transform:scale(.8);opacity:1}100%{transform:scale(1.5);opacity:0}}
.pb{font-size:11px;background:#fff9c4;border:1px solid #f0c040;border-radius:6px;padding:6px 10px;color:#333}
strong{font-weight:600}
</style>
</head>
<body>
<div class="phone">
  <div class="topbar">
    <div class="av">&#127807;</div>
    <div class="ti"><h3>Krushi Mitra</h3><p id="st">Online</p></div>
  </div>
  <div class="ctrl">
    <label>Lang:</label>
    <select id="ls" onchange="cLang(this.value)">
      <option value="hi">&#2361;&#2367;&#2306;&#2342;&#2368;</option>
      <option value="mr">&#2350;&#2352;&#2366;&#2336;&#2368;</option>
      <option value="en">English</option>
    </select>
    <label>User:</label>
    <select id="us">
      <option value="91TEST0000001">Farmer 1</option>
      <option value="91TEST0000002">Farmer 2</option>
      <option value="91TEST0000003">Farmer 3</option>
    </select>
    <button class="xbtn" id="vrb" onclick="tVR()" style="background:#075e54">&#128266; Voice:ON</button>
    <button class="xbtn" onclick="doReset()" style="background:#dc3545">&#128260; Reset</button>
  </div>
  <div class="vbar" id="vb"><div class="vd"></div><span id="vbt">Listening...</span></div>
  <div class="chat" id="chat"></div>
  <div class="typ" id="typ"><span></span><span></span><span></span></div>
  <div class="chips">
    <div class="chip" onclick="qs('menu')">&#128203; Menu</div>
    <div class="chip" onclick="qs('profile')">&#128100; Profile</div>
    <div class="chip" onclick="qs('schemes')">&#127807; Schemes</div>
    <div class="chip" onclick="qs('PM-KISAN')">PM-KISAN</div>
    <div class="chip" onclick="qs('Solar Pump')">Solar Pump</div>
    <div class="chip" onclick="qs('why am I not eligible')">Not eligible?</div>
  </div>
  <div class="ibar">
    <button class="mbtn" id="mb" onclick="tMic()" title="Tap to speak in Hindi/Marathi/English">&#127908;</button>
    <input id="inp" type="text" placeholder="Type or tap &#127908; to speak..." onkeydown="if(event.key==='Enter')snd()"/>
    <button class="sbtn" onclick="snd()">&#10148;</button>
  </div>
</div>
<script>
var von=true,rec=null,isL=false;
var chat=document.getElementById('chat'),inp=document.getElementById('inp');
var typ=document.getElementById('typ'),st=document.getElementById('st');
var mb=document.getElementById('mb'),vb=document.getElementById('vb'),vbt=document.getElementById('vbt');
var SL={hi:'hi-IN',mr:'mr-IN',en:'en-IN'};
function gl(){return document.getElementById('ls').value;}
function gn(){return document.getElementById('us').value;}
function ts(){return new Date().toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit'});}
function fmt(t){return t.replace(/\\*([^*]+)\\*/g,'<strong>$1</strong>').replace(/\\n/g,'<br>');}
function bbl(txt,tp,iv){
  var d=document.createElement('div');d.className='bbl '+(tp==='user'?'ub':'bb');
  if(iv&&tp==='user')d.innerHTML='<div class="vl">&#127908; Voice</div>';
  d.innerHTML+=fmt(txt)+'<div class="t">'+ts()+(tp==='user'?' &#10003;&#10003;':'')+'</div>';
  chat.appendChild(d);chat.scrollTop=chat.scrollHeight;
}
function showT(s){typ.style.display=s?'flex':'none';if(s)chat.scrollTop=chat.scrollHeight;}
function tVR(){von=!von;var b=document.getElementById('vrb');b.textContent=(von?'&#128266;':'&#128263;')+' Voice:'+(von?'ON':'OFF');b.style.background=von?'#075e54':'#999';}
function spk(txt,lang){
  if(!von||!window.speechSynthesis)return;
  window.speechSynthesis.cancel();
  var cl=txt.replace(/\\*([^*]+)\\*/g,'$1').replace(/[^\\u0000-\\u007F\\u0900-\\u097F ]/g,'');
  var u=new SpeechSynthesisUtterance(cl);u.lang=SL[lang]||'hi-IN';u.rate=0.9;
  window.speechSynthesis.speak(u);
}
async function api(txt,iv){
  if(!txt.trim())return;
  var lang=gl();bbl(txt,'user',iv);showT(true);st.textContent='typing...';
  try{
    var r=await fetch('/simulate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({number:gn(),message:txt,lang:lang})});
    var d=await r.json();showT(false);st.textContent='Online';bbl(d.reply,'bot');
    if(d.lang)document.getElementById('ls').value=d.lang;
    if(von||iv)spk(d.reply,d.lang||lang);
    uProf(d.profile);
  }catch(e){showT(false);st.textContent='Online';bbl('Cannot reach backend on port 8000. Is it running?','bot');}
}
function snd(){var t=inp.value.trim();inp.value='';api(t,false);}
function qs(t){api(t,false);}
function cLang(l){fetch('/simulate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({number:gn(),message:l==='hi'?'Hindi':l==='mr'?'Marathi':'English',lang:l})});}
async function doReset(){
  window.speechSynthesis&&window.speechSynthesis.cancel();
  await fetch('/simulate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({number:gn(),message:'reset',lang:gl()})});
  chat.innerHTML='';var ob=document.getElementById('pb');if(ob)ob.remove();bbl('Session reset!','bot');
}
function uProf(p){
  var ob=document.getElementById('pb');if(ob)ob.remove();
  if(!p||!Object.keys(p).length)return;
  var b=document.createElement('div');b.id='pb';b.className='pb';
  b.innerHTML='<strong>Profile:</strong> '+Object.entries(p).map(function(e){return e[0]+': '+e[1];}).join(' | ');
  chat.appendChild(b);chat.scrollTop=chat.scrollHeight;
}
function iRec(){
  var SR=window.SpeechRecognition||window.webkitSpeechRecognition;if(!SR)return null;
  var r=new SR();r.continuous=false;r.interimResults=true;r.maxAlternatives=1;
  r.onstart=function(){isL=true;mb.classList.add('on');mb.textContent='&#9209;';vb.classList.add('on');vbt.textContent='Listening... speak now';st.textContent='Recording...';inp.placeholder='Listening...';};
  r.onresult=function(e){var f='',i='';for(var x=e.resultIndex;x<e.results.length;x++){if(e.results[x].isFinal)f+=e.results[x][0].transcript;else i+=e.results[x][0].transcript;}inp.value=f||i;vbt.textContent='Heard: '+(f||i);};
  r.onend=function(){isL=false;mb.classList.remove('on');mb.textContent='&#127908;';vb.classList.remove('on');st.textContent='Online';inp.placeholder='Type or tap mic to speak...';var t=inp.value.trim();if(t){inp.value='';api(t,true);}};
  r.onerror=function(e){isL=false;mb.classList.remove('on');mb.textContent='&#127908;';vb.classList.remove('on');st.textContent='Online';inp.placeholder='Type or tap mic...';var m={'not-allowed':'Mic denied. Allow mic in browser address bar.','no-speech':'No speech detected.','network':'Network error.'};bbl(m[e.error]||'Error: '+e.error,'bot');};
  return r;
}
function tMic(){if(!rec)rec=iRec();if(!rec){bbl('Voice needs Chrome or Edge browser.','bot');return;}if(isL)rec.stop();else{rec.lang=SL[gl()]||'hi-IN';rec.start();}}
window.onload=function(){
  rec=iRec();
  setTimeout(function(){bbl('*Krushi Mitra*\\n\\nTap the *MIC button* (bottom-left &#127908;) to speak in Hindi or Marathi.\\nOr type and press Enter.\\n\\nTry: menu, profile, schemes','bot');},300);
};
</script>
</body>
</html>"""


@router.get("/test", response_class=HTMLResponse)
def simulator_ui() -> str:
    return _HTML
