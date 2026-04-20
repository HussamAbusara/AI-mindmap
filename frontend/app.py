"""
AI Research Assistant — Frontend
Streamlit app with Chat + Mind Map modes

Public version — see README for full setup.
"""

import streamlit as st
import streamlit.components.v1 as components
import requests
import json
import os
import re
import io
import time
import concurrent.futures
from datetime import datetime

# ── Configuration ──
API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000/api")

st.set_page_config(
    page_title="مساعد البحث الذكي",
    page_icon="🔬",
    layout="centered",
)

# ── Session state defaults ──
for k, v in {
    "history": [], "doc_count": 0,
    "mm_raw_text": "", "mm_summary": "", "mm_data": None, "mm_step": 0,
    "theme": "light", "backend_warm": False,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ══════════════════════════════════════════
# Theme System
# ══════════════════════════════════════════
THEMES = {
    "light": dict(
        BG="#f8f9fc", BG3="#f0f2f8", BORDER="#dde1f0",
        TEXT="#1a1d2e", TEXT2="#6b7280",
        ACCENT="#4f5ef0", ACCENT2="#3b4bd4",
        MSG_U="#eef0ff", MSG_A="#ffffff",
        SHADOW="rgba(79,94,240,0.08)", SVG="#f8f9fc",
        N0="#4f5ef0", N1="#ffffff", N2="#f0f2f8",
        TC="#1a1d2e", BB="#ffffff", BBD="#dde1f0", BBT="#6b7280",
    ),
    "dark": dict(
        BG="#0f1117", BG3="#23273a", BORDER="#2e3248",
        TEXT="#e8eaf0", TEXT2="#8b90a7",
        ACCENT="#5b6ef5", ACCENT2="#3d4fd4",
        MSG_U="#23273a", MSG_A="#1e2238",
        SHADOW="rgba(0,0,0,0.3)", SVG="#0f1117",
        N0="#5b6ef5", N1="#1e2238", N2="#13151f",
        TC="#e8eaf0", BB="#1e2238", BBD="#2e3248", BBT="#8b90a7",
    ),
}
C = THEMES[st.session_state.theme]


# ══════════════════════════════════════════
# API Helpers
# ══════════════════════════════════════════
def warmup():
    """Ping backend to wake it from sleep (HuggingFace Spaces idle)."""
    if not st.session_state.backend_warm:
        try:
            requests.get(f"{API_BASE.replace('/api','')}/health", timeout=15)
            st.session_state.backend_warm = True
        except:
            pass


def fetch_count() -> int:
    try:
        return requests.get(f"{API_BASE}/documents/count", timeout=5).json().get("count", 0)
    except:
        return st.session_state.doc_count


def ask_chat(q: str) -> str:
    try:
        r = requests.post(
            f"{API_BASE}/query",
            json={"question": q, "history": st.session_state.history, "stream": False},
            timeout=300,
        )
        d = r.json()
        if "documents_count" in d:
            st.session_state.doc_count = d["documents_count"]
        return d.get("answer") or "لا توجد إجابة."
    except requests.exceptions.Timeout:
        return "⏳ انتهت المهلة — أعد المحاولة."
    except Exception as e:
        return f"❌ {e}"


def ask_llm(prompt: str) -> str:
    """Direct LLM call without history — used for mind map summarization."""
    try:
        r = requests.post(
            f"{API_BASE}/query",
            json={"question": prompt, "history": [], "stream": False},
            timeout=300,
        )
        return r.json().get("answer", "")
    except:
        return ""


def upload_backend(f) -> tuple[bool, str]:
    try:
        r = requests.post(
            f"{API_BASE}/upload",
            files={"file": (f.name, f.getvalue(), f.type)},
            timeout=30,
        )
        d = r.json()
        if not r.ok or "error" in d:
            return False, d.get("error") or d.get("detail", "خطأ")
        return True, d.get("message", "تم الرفع")
    except Exception as e:
        return False, str(e)


# ══════════════════════════════════════════
# Local Text Extraction (no backend needed)
# ══════════════════════════════════════════
def extract_locally(f) -> tuple[bool, str]:
    """
    Extract text from PDF/DOCX directly in the browser environment.
    This avoids sending the file to the backend just for extraction.
    """
    name = f.name.lower()
    data = f.getvalue()

    if name.endswith(".pdf"):
        # Try PyMuPDF first (faster, better Arabic support)
        try:
            import fitz
            doc = fitz.open(stream=data, filetype="pdf")
            txt = "".join(p.get_text("text", flags=48) + "\n\n" for p in doc).strip()
            doc.close()
            if txt:
                return True, txt
        except ImportError:
            pass
        # Fallback to pypdf
        try:
            from pypdf import PdfReader
            txt = "\n\n".join(
                p.extract_text() or "" for p in PdfReader(io.BytesIO(data)).pages
            ).strip()
            if txt:
                return True, txt
        except Exception as e:
            return False, str(e)

    elif name.endswith(".docx"):
        try:
            from docx import Document
            txt = "\n".join(
                p.text for p in Document(io.BytesIO(data)).paragraphs if p.text.strip()
            )
            if txt:
                return True, txt.strip()
        except Exception as e:
            return False, str(e)

    return False, "نوع الملف غير مدعوم"


# ══════════════════════════════════════════
# Mind Map Pipeline
# ══════════════════════════════════════════
def summarize_for_mindmap(text: str) -> str:
    """
    Uses the LLM to convert free text into a structured outline.

    Prompt engineering notes:
    - Written in English for better instruction following
    - Strict format enforced with positive + negative examples
    - Short labels required to fit mind map nodes
    """
    prompt = f"""Output ONLY a structured Arabic outline. Nothing else. No intro. No explanation.

STRICT FORMAT:
Line 1: title (max 5 Arabic words, no ## prefix)
Then exactly 3-5 branches, each on its own line starting with ##
Each ## branch: max 4 Arabic words
Under each branch: 2-4 bullet points starting with -
Each bullet: max 7 Arabic words

EXAMPLE OUTPUT:
التجارة الإلكترونية
## النمو والأرقام
- نمو 265٪ في المبيعات
- 4.88 تريليون بحلول 2021
## فوائد الشركات
- التميز عن المنافسين
- خفض التكاليف

Text to summarize:
{text[:3000]}

OUTPUT:"""
    return ask_llm(prompt).strip()


def parse_mindmap(text: str) -> dict:
    """Parse structured outline text into D3-compatible JSON tree."""
    text = re.sub(r'(##[^\n]+?)\s+-\s+', r'\1\n- ', text)
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    if not lines:
        return {"topic": "الموضوع", "children": []}

    title = ' '.join(re.sub(r'^#+\s*', '', lines[0]).strip().split()[:6])
    branches, cur, kids = [], None, []

    for line in lines[1:]:
        if line.startswith('#'):
            if cur is not None:
                branches.append({
                    "topic": cur,
                    "children": [{"topic": k, "children": []} for k in kids]
                })
            cur = ' '.join(re.sub(r'^#+\s*', '', line).strip().split()[:5])
            kids = []
        elif line.startswith(('-', '•', '*')):
            k = ' '.join(re.sub(r'^[-•*]\s*', '', line).strip().split()[:8])
            if k and cur is not None:
                kids.append(k)
        elif cur is None and len(line) > 3:
            cur = ' '.join(line.split()[:5])
            kids = []

    if cur is not None:
        branches.append({
            "topic": cur,
            "children": [{"topic": k, "children": []} for k in kids]
        })

    if not branches:
        branches = [
            {"topic": ' '.join(l.split()[:5]), "children": []}
            for l in lines[1:] if len(l) > 8
        ][:7]

    return {"topic": title, "children": branches[:6]}


# ══════════════════════════════════════════
# Live Progress (runs API call in thread)
# ══════════════════════════════════════════
WAIT_MSGS = [
    ("🧠", "الذكاء يقرأ النص"), ("🔍", "يحدد الأفكار الرئيسية"),
    ("📌", "يستخرج النقاط المهمة"), ("🌿", "يرتب الفروع"),
    ("✍️", "يصيغ الملخص"), ("🔗", "يربط الأفكار"),
    ("⚡", "لحظات أخيرة"), ("🗺️", "الخريطة على وشك الظهور"),
]
CHAT_MSGS = [
    ("🤔", "يفكر في إجابتك"), ("📚", "يراجع المعلومات"),
    ("🔎", "يبحث عن أفضل رد"), ("✍️", "يصيغ الإجابة"),
    ("⚡", "لحظات أخيرة"),
]
TIPS = [
    "💡 الخريطة تُحسّن الفهم والحفظ",
    "💡 اسحب وكبّر الخريطة بعد الانتهاء",
    "💡 اضغط 💾 لحفظ الخريطة PNG",
    "💡 جرّب إعادة التلخيص للحصول على نتيجة مختلفة",
]


def live_run(fn, msgs, tips=None):
    """Run fn in a thread while showing animated progress bar."""
    result = {"val": None}
    def _run(): result["val"] = fn()

    pb = st.empty()
    tp = st.empty()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(_run)
        step = 0
        while not future.done():
            icon, msg = msgs[step % len(msgs)]
            pb.progress(min(10 + step * 9, 90), text=f"{icon} {msg}...")
            if tips:
                tp.markdown(
                    f'<div style="text-align:center;font-size:12px;'
                    f'color:{C["TEXT2"]};margin-top:4px">{tips[step // 3 % len(tips)]}</div>',
                    unsafe_allow_html=True,
                )
            time.sleep(1.1)
            step += 1

    pb.progress(100, text="✅ جاهز!")
    tp.empty()
    time.sleep(0.3)
    pb.empty()
    return result["val"]


# ══════════════════════════════════════════
# D3.js Mind Map Renderer
# ══════════════════════════════════════════
def render_mindmap(data: dict):
    """
    Renders an interactive radial mind map using D3.js v7.

    Layout algorithm:
    - Each branch gets an equal angular sector (360/n degrees)
    - Sub-branches distributed within parent's sector only (20% margin each side)
    - Prevents overlap between sibling branches
    - Responsive to container width/height
    """
    sv = C['SVG']; n0 = C['N0']; n1 = C['N1']; n2 = C['N2']
    tc = C['TC'];  bb = C['BB']; bbd = C['BBD']; bbt = C['BBT']
    js = json.dumps(data, ensure_ascii=False)

    # Full D3 renderer implementation
    # See render_mindmap() in the live deployment for complete code
    html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"/>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:{sv};overflow:hidden;font-family:'Tajawal','Segoe UI',sans-serif}}
#cv{{width:100%;height:560px;display:block;cursor:grab}}
#cv:active{{cursor:grabbing}}
.ctrl{{position:absolute;bottom:10px;left:10px;display:flex;gap:5px;z-index:99}}
.btn{{background:{bb};border:1px solid {bbd};color:{bbt};padding:5px 11px;
  border-radius:6px;cursor:pointer;font-size:12px;font-family:inherit;transition:all .2s}}
.btn:hover{{border-color:#4f5ef0;color:#4f5ef0}}
#sb{{background:#4f5ef0;color:#fff;border-color:#4f5ef0}}
.wrap{{position:relative;width:100%;height:560px}}
</style>
<link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&display=swap" rel="stylesheet"/>
</head><body>
<div class="wrap">
<svg id="cv"></svg>
<div class="ctrl">
  <button class="btn" id="zm">−</button>
  <button class="btn" id="zp">+</button>
  <button class="btn" id="zr">⟳</button>
  <button class="btn" id="sb">💾 PNG</button>
</div>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
<script>
const DATA={js};
const COLS=['#4f5ef0','#16a34a','#d97706','#7c3aed','#0891b2','#db2777','#dc2626','#10b981'];
const N0='{n0}',N1='{n1}',N2='{n2}',TC='{tc}',SV='{sv}';

function box(text,depth){{
  const maxW=depth===0?130:depth===1?115:100;
  const fs=depth===0?13:depth===1?12:10.5;
  const lh=fs+5;
  const words=text.split(' ');
  let line='',lines=[];
  words.forEach(w=>{{
    const t=line?line+' '+w:w;
    if(t.length*fs*0.50>maxW&&line){{lines.push(line);line=w;}}
    else line=t;
  }});
  if(line)lines.push(line);
  if(!lines.length)lines=[text];
  const w=Math.min(maxW,Math.max(60,lines.reduce((a,l)=>Math.max(a,l.length*fs*0.50),0)+20));
  return{{w,h:Math.max(lines.length*lh+14,34),lines,fs,lh}};
}}

function drawTxt(g,bx,x,y,depth){{
  const{{lines,fs,lh,h}}=bx;
  const sy=y-h/2+(h-lines.length*lh)/2+lh*0.72;
  lines.forEach((l,i)=>
    g.append('text').attr('x',x).attr('y',sy+i*lh)
      .attr('text-anchor','middle').attr('font-size',fs+'px')
      .attr('font-family',"'Tajawal','Segoe UI',sans-serif")
      .attr('font-weight',depth<=1?'600':'400')
      .attr('fill',depth===0?'#fff':TC).attr('pointer-events','none').text(l));
}}

function layout(data,W,H){{
  const nodes=[],links=[];
  const rb=box(data.topic,0);
  nodes.push({{depth:0,x:W/2,y:H/2,box:rb,fill:N0,stroke:'none',topic:data.topic}});
  const ch=data.children||[],n=ch.length;
  if(!n)return{{nodes,links}};
  const base=Math.min(W,H);
  const hasDeep=ch.some(c=>c.children&&c.children.length>0);
  const R1=base*(hasDeep?0.34:0.30);
  const R2=base*0.20;
  ch.forEach((child,ci)=>{{
    const aCenter=(2*Math.PI*ci/n)-Math.PI/2;
    const sector=2*Math.PI/n;
    const cx=W/2+R1*Math.cos(aCenter),cy=H/2+R1*Math.sin(aCenter);
    const col=COLS[ci%COLS.length];
    const cb=box(child.topic,1);
    const cNode={{depth:1,x:cx,y:cy,box:cb,fill:N1,stroke:col,topic:child.topic}};
    nodes.push(cNode);
    links.push({{sx:W/2,sy:H/2,tx:cx,ty:cy,col:col+'88',w:2}});
    const subs=child.children||[],ns=subs.length;
    if(!ns)return;
    const margin=sector*0.20,usable=sector-2*margin;
    subs.forEach((sub,si)=>{{
      const t=ns===1?0.5:si/(ns-1);
      const sa=aCenter-usable/2+usable*t;
      const sx=cx+R2*Math.cos(sa),sy=cy+R2*Math.sin(sa);
      nodes.push({{depth:2,x:sx,y:sy,box:box(sub.topic,2),fill:N2,stroke:col+'cc',topic:sub.topic}});
      links.push({{sx:cx,sy:cy,tx:sx,ty:sy,col:col+'55',w:1.3}});
    }});
  }});
  return{{nodes,links}};
}}

let gAll;
function draw(){{
  const svgEl=document.getElementById('cv');
  const W=svgEl.clientWidth||760,H=svgEl.clientHeight||560;
  d3.select('#cv').attr('viewBox',`0 0 ${{W}} ${{H}}`).selectAll('*').remove();
  gAll=d3.select('#cv').append('g');
  const{{nodes,links}}=layout(DATA,W,H);
  links.forEach(l=>{{
    const mx=(l.sx+l.tx)/2;
    gAll.append('path')
      .attr('d',`M${{l.sx}},${{l.sy}} Q${{mx}},${{l.sy}} ${{l.tx}},${{l.ty}}`)
      .attr('style',`fill:none;stroke:${{l.col}};stroke-width:${{l.w}};stroke-opacity:0.8`);
  }});
  nodes.forEach(n=>{{
    const{{w,h}}=n.box,rx=n.depth===0?14:n.depth===1?10:8;
    if(n.depth<=1){{
      gAll.append('rect').attr('x',n.x-w/2+2).attr('y',n.y-h/2+3)
        .attr('width',w).attr('height',h).attr('rx',rx)
        .attr('style',`fill:${{n.depth===0?COLS[0]:n.stroke}};opacity:0.1;stroke:none`);
    }}
    const hov=n.depth===0?'#3b4bd4':n.depth===1?(SV==='#f8f9fc'?'#e8eaff':'#2a2e45'):(SV==='#f8f9fc'?'#e4e7f5':'#1e2238');
    gAll.append('rect').attr('x',n.x-w/2).attr('y',n.y-h/2)
      .attr('width',w).attr('height',h).attr('rx',rx)
      .attr('style',`fill:${{n.fill}};stroke:${{n.stroke}};stroke-width:${{n.depth===0?2.5:n.depth===1?1.8:1.2}};cursor:pointer`)
      .on('mouseover',function(){{this.style.fill=hov;}})
      .on('mouseout', function(){{this.style.fill=n.fill;}});
    drawTxt(gAll,n.box,n.x,n.y,n.depth);
  }});
}}

const sel=d3.select('#cv');
const zB=d3.zoom().scaleExtent([0.2,4]).on('zoom',e=>gAll&&gAll.attr('transform',e.transform));
sel.call(zB);
document.getElementById('zm').onclick=()=>sel.transition().duration(200).call(zB.scaleBy,.72);
document.getElementById('zp').onclick=()=>sel.transition().duration(200).call(zB.scaleBy,1.38);
document.getElementById('zr').onclick=()=>sel.transition().duration(280).call(zB.transform,d3.zoomIdentity);
document.getElementById('sb').onclick=function(){{
  const svgEl=document.getElementById('cv');
  let vx=0,vy=0,vw=760,vh=560;
  try{{const g=svgEl.querySelector('g');if(g){{const b=g.getBBox(),p=50;vx=b.x-p;vy=b.y-p;vw=b.width+p*2;vh=b.height+p*2;}}}}catch(e){{}}
  const cl=svgEl.cloneNode(true);
  cl.setAttribute('xmlns','http://www.w3.org/2000/svg');
  cl.setAttribute('viewBox',`${{vx}} ${{vy}} ${{vw}} ${{vh}}`);
  cl.setAttribute('width',vw*2);cl.setAttribute('height',vh*2);
  const ns='http://www.w3.org/2000/svg';
  const defs=document.createElementNS(ns,'defs');
  const sty=document.createElementNS(ns,'style');
  sty.textContent="@import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&display=swap');";
  defs.appendChild(sty);
  const bg=document.createElementNS(ns,'rect');
  bg.setAttribute('x',vx);bg.setAttribute('y',vy);bg.setAttribute('width',vw);bg.setAttribute('height',vh);bg.setAttribute('fill',SV);
  cl.insertBefore(bg,cl.firstChild);cl.insertBefore(defs,cl.firstChild);
  cl.querySelectorAll('*').forEach(el=>{{
    ['stroke-width','stroke-opacity'].forEach(a=>{{const v=el.getAttribute(a);if(v){{let s=el.getAttribute('style')||'';s+=`;${{a}}:${{v}}`;el.setAttribute('style',s.replace(/^;/,''));el.removeAttribute(a);}}}});
    ['onclick','onmouseover','onmouseout'].forEach(a=>el.removeAttribute(a));
  }});
  const src=new XMLSerializer().serializeToString(cl);
  const url=URL.createObjectURL(new Blob([src],{{type:'image/svg+xml;charset=utf-8'}}));
  const img=new Image();
  img.onload=function(){{
    const cv=document.createElement('canvas');cv.width=vw*2;cv.height=vh*2;
    const ctx=cv.getContext('2d');ctx.fillStyle=SV;ctx.fillRect(0,0,cv.width,cv.height);
    ctx.drawImage(img,0,0,cv.width,cv.height);URL.revokeObjectURL(url);
    const a=document.createElement('a');a.download='mindmap_'+Date.now()+'.png';a.href=cv.toDataURL('image/png',1.0);a.click();
  }};
  img.onerror=function(){{URL.revokeObjectURL(url);const a=document.createElement('a');a.download='mindmap_'+Date.now()+'.svg';a.href=URL.createObjectURL(new Blob([src],{{type:'image/svg+xml'}}));a.click();}};
  img.src=url;
}};
let rt;window.addEventListener('resize',()=>{{clearTimeout(rt);rt=setTimeout(draw,250);}});
draw();
</script></body></html>"""
    components.html(html, height=575, scrolling=False)


# ══════════════════════════════════════════
# UI — Header
# ══════════════════════════════════════════
warmup()
st.session_state.doc_count = fetch_count()
mc = "rag" if st.session_state.doc_count > 0 else ""
mt = f"RAG ✓ — {st.session_state.doc_count} وثيقة" if st.session_state.doc_count > 0 else "chat"

col_title, col_theme = st.columns([5, 1])
with col_title:
    st.markdown(
        f'<div style="display:flex;align-items:center;justify-content:space-between;'
        f'padding:10px 0 14px;border-bottom:2px solid {C["BORDER"]};margin-bottom:18px">'
        f'<h2 style="margin:0;font-size:18px;font-weight:700;color:{C["TEXT"]}">'
        f'🔬 مساعد البحث الذكي</h2>'
        f'<span style="font-size:11px;padding:3px 10px;border-radius:20px;'
        f'border:1px solid {"#22c55e" if mc else C["BORDER"]};'
        f'color:{"#22c55e" if mc else C["TEXT2"]}">{mt}</span></div>',
        unsafe_allow_html=True,
    )
with col_theme:
    if st.button("🌙" if st.session_state.theme == "light" else "☀️", key="th"):
        st.session_state.theme = "dark" if st.session_state.theme == "light" else "light"
        st.rerun()

tab_chat, tab_mm = st.tabs(["💬 دردشة ذكية", "🗺️ خريطة ذهنية"])

# Sidebar, Chat tab, and Mind map tab implementation continues...
# See live deployment for complete UI code
