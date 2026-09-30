"""
app.py -- SIH26142 | NTRO Satellite Super-Resolution
Satellite Earth background with animated orbital mechanics
"""
import streamlit as st
import os, time, random
from pathlib import Path

st.set_page_config(
    page_title="NTRO | Satellite SR | SIH26142",
    page_icon="\U0001f30d",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from database import init_db, SessionLocal, JobRepository, MetricsRepository
init_db()
from models import MODEL_REGISTRY
from tools import run_super_resolution, compute_metrics, geotiff_to_png
from models.bicubic import run_bicubic

if "page" not in st.session_state:
    st.session_state.page = "home"

# =========================================================================
#  BASE CSS — injected once, affects the whole Streamlit shell
# =========================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Space+Mono:wght@400;700&family=Barlow+Condensed:wght@400;600;700&display=swap');

/* ── Color tokens — Bold Satellite Command ── */
:root {
  --white:  #ffffff;
  --red:    #ff1744;
  --green:  #00e676;
  --yellow: #ffd600;
  --cyan:   #00e5ff;
  --orange: #ff6d00;
  --bg:     #060810;
  --bg2:    rgba(6,8,18,.92);
  --panel:  rgba(6,10,22,.88);
  --border: rgba(255,255,255,.15);
  --border-h:rgba(255,255,255,.45);
  --text:   #ffffff;
  --muted:  #4a5a70;
}

/* ── ALL CSS var overrides mapped to new palette ── */
/* --cyan  → white/cyan accents  */
/* --green → #00e676 bright green */
/* --red   → #ff1744 hot red      */
/* --yellow → #ffd600 bright yellow */

*,*::before,*::after{box-sizing:border-box;}
html,body,[class*="css"]{font-family:'Space Grotesk',sans-serif;background:var(--bg);color:var(--text);}

/* Hide Streamlit chrome */
.stApp{background:transparent !important;}
.block-container{padding:0 !important;max-width:100% !important;}
section[data-testid="stSidebar"]{display:none !important;}
header[data-testid="stHeader"]{display:none !important;}
div.stToolbar{display:none !important;}
#MainMenu{display:none !important;}
footer{display:none !important;}

/* ─── Space background ─── */
body::before{
    content:'';
    position:fixed;inset:0;z-index:-3;
    background:
        radial-gradient(ellipse 60% 70% at 75% 40%, rgba(0,120,255,.14) 0%,transparent 60%),
        radial-gradient(ellipse 40% 50% at 15% 70%, rgba(185,103,255,.08) 0%,transparent 60%),
        radial-gradient(ellipse at 50% 50%,#04070f 0%,#020509 70%,#010305 100%);
}

/* Earth sphere — brighter, more vivid */
#earth-bg{
    position:fixed;
    right:-160px;top:50%;
    transform:translateY(-50%);
    width:720px;height:720px;
    border-radius:50%;
    z-index:-2;
    background:
        /* bright cloud patches */
        radial-gradient(ellipse 200px 70px at 32% 20%, rgba(255,255,255,.55) 0%,transparent 55%),
        radial-gradient(ellipse 130px 50px at 65% 28%, rgba(255,255,255,.45) 0%,transparent 55%),
        radial-gradient(ellipse 100px 40px at 18% 58%, rgba(255,255,255,.35) 0%,transparent 52%),
        radial-gradient(ellipse 160px 55px at 78% 62%, rgba(255,255,255,.4) 0%,transparent 52%),
        radial-gradient(ellipse 110px 35px at 48% 82%, rgba(255,255,255,.3) 0%,transparent 50%),
        /* vivid land — Indian subcontinent greens */
        radial-gradient(ellipse 140px 170px at 55% 42%, #3a7a30 0%,#22550f 55%,transparent 70%),
        radial-gradient(ellipse 90px 130px at 38% 48%, #4a8e28 0%,#2d6012 50%,transparent 68%),
        radial-gradient(ellipse 70px 90px at 72% 28%, #5a9e35 0%,#2d6012 50%,transparent 65%),
        radial-gradient(ellipse 55px 65px at 23% 33%, #3a7a30 0%,transparent 60%),
        radial-gradient(ellipse 45px 60px at 82% 60%, #3a7a30 0%,transparent 60%),
        radial-gradient(ellipse 75px 45px at 12% 72%, #4a8e28 0%,transparent 60%),
        /* vivid ocean — bright blue */
        radial-gradient(circle,#1e88e5 0%,#1565c0 40%,#0d47a1 72%,#072a6e 100%);
    box-shadow:
        inset -70px -35px 110px rgba(0,0,0,.65),
        inset 25px 12px 70px rgba(255,255,255,.07),
        0 0 140px rgba(30,136,229,.45),
        0 0 350px rgba(30,136,229,.15),
        0 0 600px rgba(0,200,255,.06);
    animation:earth-drift 90s linear infinite;
}
@keyframes earth-drift{
    0%  {filter:hue-rotate(0deg) brightness(1.05);}
    33% {filter:hue-rotate(5deg) brightness(1.1);}
    66% {filter:hue-rotate(-3deg) brightness(1.0);}
    100%{filter:hue-rotate(0deg) brightness(1.05);}
}
#earth-bg::after{
    content:'';
    position:absolute;inset:-22px;border-radius:50%;
    background:radial-gradient(circle,transparent 45%,
        rgba(0,200,255,.18) 50%,rgba(0,150,255,.08) 56%,transparent 62%);
    box-shadow:0 0 100px rgba(0,200,255,.18);
}
#earth-bg::before{
    content:'';
    position:fixed;inset:0;
    background-image:
        radial-gradient(1.5px 1.5px at  5% 12%,rgba(255,255,255,1),transparent),
        radial-gradient(1px   1px   at 18%  8%,rgba(255,255,255,.8),transparent),
        radial-gradient(2px   2px   at  9% 35%,rgba(255,255,255,.6),transparent),
        radial-gradient(1px   1px   at 32% 18%,rgba(255,255,255,.9),transparent),
        radial-gradient(1px   1px   at 45%  5%,rgba(255,255,255,.7),transparent),
        radial-gradient(2px   2px   at 55% 22%,rgba(255,255,255,.5),transparent),
        radial-gradient(1.5px 1.5px at 68% 10%,rgba(255,255,255,1),transparent),
        radial-gradient(1px   1px   at 78%  3%,rgba(255,255,255,.8),transparent),
        radial-gradient(2px   2px   at 88% 18%,rgba(255,255,255,.6),transparent),
        radial-gradient(1px   1px   at 95% 30%,rgba(255,255,255,.9),transparent),
        radial-gradient(1px   1px   at  3% 50%,rgba(255,255,255,.7),transparent),
        radial-gradient(1.5px 1.5px at 15% 65%,rgba(255,255,255,1),transparent),
        radial-gradient(2px   2px   at 28% 75%,rgba(255,255,255,.6),transparent),
        radial-gradient(1px   1px   at 42% 88%,rgba(255,255,255,.8),transparent),
        radial-gradient(1px   1px   at 58% 92%,rgba(255,255,255,.7),transparent),
        radial-gradient(1px   1px   at 72% 80%,rgba(255,255,255,.9),transparent),
        radial-gradient(2px   2px   at 85% 70%,rgba(255,255,255,.5),transparent),
        radial-gradient(1px   1px   at 92% 60%,rgba(255,255,255,.8),transparent),
        radial-gradient(1.5px 1.5px at 10% 90%,rgba(255,255,255,1),transparent),
        radial-gradient(1px   1px   at 97% 85%,rgba(255,255,255,.7),transparent),
        radial-gradient(1px   1px   at 38% 45%,rgba(255,255,255,.4),transparent),
        radial-gradient(1px   1px   at  7% 78%,rgba(255,255,255,.6),transparent),
        radial-gradient(1px   1px   at 62% 55%,rgba(255,255,255,.5),transparent),
        radial-gradient(1.5px 1.5px at 22% 42%,rgba(255,255,255,.9),transparent),
        radial-gradient(1px   1px   at 50% 60%,rgba(255,255,255,.3),transparent);
    border-radius:50%;z-index:-1;
}
body::after{
    content:'';
    position:fixed;inset:0;z-index:-1;pointer-events:none;
    background:repeating-linear-gradient(
        0deg,transparent,transparent 3px,
        rgba(0,245,255,.005) 3px,rgba(0,245,255,.005) 4px);
}

/* ─── SINGLE NAV ─── */
.nav-bar-row {
    position:sticky;top:0;z-index:200;
    background:rgba(6,6,16,.96);
    border-bottom:2px solid var(--red);
    backdrop-filter:blur(22px);
    -webkit-backdrop-filter:blur(22px);
    display:flex;align-items:stretch;
    padding:0 1rem;
    box-shadow:0 2px 30px rgba(0,0,0,.8), 0 2px 0 rgba(255,23,68,.3);
}
.nav-brand-wrap{
    display:flex;align-items:center;gap:.7rem;
    padding:.6rem 1rem .6rem 0;
    border-right:1px solid rgba(255,255,255,.12);
    margin-right:.5rem;flex-shrink:0;
}
.nav-brand-icon{font-size:1.5rem;}
.nav-brand-name{
    font-family:'Barlow Condensed',sans-serif;
    font-size:1.1rem;font-weight:700;
    line-height:1.1;letter-spacing:.5px;
    background:linear-gradient(90deg,#ffffff,var(--yellow));
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
    background-clip:text;
}
.nav-brand-sub{font-size:.58rem;color:var(--green);letter-spacing:1.8px;text-transform:uppercase;
    -webkit-text-fill-color:var(--green);font-weight:700;}
.nav-pills-wrap{display:flex;align-items:center;gap:.35rem;margin-left:auto;padding-right:.5rem;}
.nav-pill{
    font-size:.6rem;font-weight:700;letter-spacing:1px;text-transform:uppercase;
    padding:3px 10px;border-radius:20px;
    border:1px solid rgba(255,214,0,.4);
    color:var(--yellow);background:rgba(255,214,0,.1);
}
.nav-pill.orange{border-color:rgba(0,230,118,.4);color:var(--green);background:rgba(0,230,118,.08);}

/* Style the nav Streamlit buttons */
div[data-testid="stHorizontalBlock"]:has(.nav-btn-col) .stButton>button {
    background:transparent !important;
    color:rgba(255,255,255,.35) !important;
    border:none !important;
    border-bottom:3px solid transparent !important;
    border-radius:0 !important;
    font-size:.83rem !important;
    font-weight:600 !important;
    padding:.85rem 1.1rem !important;
    letter-spacing:.3px !important;
    box-shadow:none !important;
    transition:all .18s !important;
    height:58px !important;
    width:100% !important;
}
div[data-testid="stHorizontalBlock"]:has(.nav-btn-col) .stButton>button:hover {
    color:#fff !important;
    background:rgba(255,255,255,.06) !important;
    transform:none !important;
    box-shadow:none !important;
}
.nav-btn-active .stButton>button {
    color:var(--yellow) !important;
    border-bottom-color:var(--red) !important;
    background:rgba(255,23,68,.08) !important;
    text-shadow:0 0 14px rgba(255,214,0,.5) !important;
}

/* ─── Content wrapper ─── */
.page-wrap{position:relative;z-index:10;padding:2rem 2.5rem;}

.glass-panel{
    background:rgba(6,8,20,.88);
    border:1px solid rgba(255,255,255,.1);
    border-radius:14px;
    backdrop-filter:blur(20px);
    -webkit-backdrop-filter:blur(20px);
    box-shadow:0 8px 40px rgba(0,0,0,.6),
               inset 0 1px 0 rgba(255,255,255,.06);
    transition:border-color .3s, box-shadow .3s;
}
.glass-panel:hover{
    border-color:rgba(255,255,255,.25);
    box-shadow:0 8px 50px rgba(0,0,0,.7), 0 0 30px rgba(255,23,68,.06);
}

/* Hero */
.hero-eyebrow{
    display:inline-flex;align-items:center;gap:.5rem;
    background:rgba(255,23,68,.12);border:1px solid rgba(255,23,68,.5);
    color:#fff;border-radius:20px;padding:4px 18px;
    font-size:.7rem;font-weight:700;letter-spacing:2px;text-transform:uppercase;
    margin-bottom:1.2rem;animation:fadeup .7s ease both;
    box-shadow:0 0 20px rgba(255,23,68,.2);
}
.hero-title{
    font-family:'Barlow Condensed',sans-serif;
    font-size:clamp(2.4rem,5vw,4.5rem);font-weight:700;color:#fff;
    line-height:1.08;margin-bottom:1rem;
    text-shadow:0 2px 40px rgba(0,0,0,.9), 0 0 60px rgba(255,255,255,.05);
    animation:fadeup .85s .1s both;
}
.hero-accent{color:var(--yellow);text-shadow:0 0 30px rgba(255,214,0,.6);}
.hero-green{
    color:var(--green);
    text-shadow:0 0 25px rgba(0,230,118,.55);
    -webkit-text-fill-color:var(--green);
}
.hero-sub{
    font-size:.97rem;color:rgba(255,255,255,.5);line-height:1.75;
    max-width:500px;margin-bottom:1.8rem;animation:fadeup .85s .2s both;
}
@keyframes fadeup{from{opacity:0;transform:translateY(16px);}to{opacity:1;transform:none;}}
.hero-badges{display:flex;gap:.6rem;flex-wrap:wrap;margin-bottom:1.6rem;animation:fadeup .85s .3s both;}
.hbadge{font-size:.71rem;font-weight:700;padding:5px 14px;border-radius:4px;border:1px solid;letter-spacing:.4px;}
.hb-blue{background:rgba(0,229,255,.1);border-color:rgba(0,229,255,.4);color:var(--cyan);}
.hb-green{background:rgba(0,230,118,.1);border-color:rgba(0,230,118,.4);color:var(--green);}
.hb-gold{background:rgba(255,214,0,.1);border-color:rgba(255,214,0,.4);color:var(--yellow);}
.hb-violet{background:rgba(255,23,68,.1);border-color:rgba(255,23,68,.4);color:var(--red);}

/* Stats */
.stats-strip{
    display:flex;flex-wrap:wrap;
    background:rgba(6,8,16,.95);backdrop-filter:blur(16px);
    border-top:2px solid rgba(255,255,255,.06);
    border-bottom:2px solid rgba(255,255,255,.06);
}
.stat-item{flex:1;min-width:110px;text-align:center;padding:1.2rem .8rem;
    border-right:1px solid rgba(255,255,255,.05);transition:background .3s;position:relative;}
.stat-item:last-child{border-right:none;}
.stat-item:hover{background:rgba(255,255,255,.03);}
.stat-item:nth-child(1) .stat-num{color:#fff;text-shadow:0 0 22px rgba(255,255,255,.6);}
.stat-item:nth-child(2) .stat-num{color:var(--green);text-shadow:0 0 22px rgba(0,230,118,.7);}
.stat-item:nth-child(3) .stat-num{color:var(--red);text-shadow:0 0 22px rgba(255,23,68,.6);}
.stat-item:nth-child(4) .stat-num{color:var(--yellow);text-shadow:0 0 22px rgba(255,214,0,.7);}
.stat-item:nth-child(5) .stat-num{color:var(--cyan);text-shadow:0 0 22px rgba(0,229,255,.6);}
.stat-item:nth-child(6) .stat-num{color:var(--green);text-shadow:0 0 22px rgba(0,230,118,.6);}
.stat-num{font-family:'Space Mono',monospace;font-size:1.9rem;font-weight:700;}
.stat-label{font-size:.67rem;color:rgba(255,255,255,.3);letter-spacing:1px;text-transform:uppercase;margin-top:4px;}

/* Section */
.sec-title{font-family:'Barlow Condensed',sans-serif;
    font-size:1.55rem;font-weight:700;color:#fff;margin-bottom:.3rem;
    letter-spacing:.3px;text-shadow:0 0 30px rgba(255,255,255,.15);}
.sec-sub{font-size:.82rem;color:rgba(255,255,255,.3);margin-bottom:1.5rem;}
.sec-ac{
    color:var(--yellow);
    text-shadow:0 0 20px rgba(255,214,0,.5);
    -webkit-text-fill-color:var(--yellow);
}
.sec-ag{color:var(--green);text-shadow:0 0 18px rgba(0,230,118,.5);}

/* Panel title */
.panel-title{
    font-family:'Barlow Condensed',sans-serif;
    font-size:.92rem;font-weight:700;color:#fff;
    letter-spacing:1.5px;text-transform:uppercase;
    border-bottom:1px solid rgba(255,255,255,.1);
    padding-bottom:.6rem;margin-bottom:1rem;
    display:flex;align-items:center;gap:.5rem;
}
.panel-title::before{content:'';display:inline-block;
    width:3px;height:14px;border-radius:2px;
    background:linear-gradient(180deg,var(--red),var(--yellow));}

/* Cards */
.geo-card{
    background:rgba(6,8,20,.7);border:1px solid rgba(255,255,255,.08);
    border-radius:10px;padding:1rem 1.1rem;margin-bottom:.65rem;
    position:relative;overflow:hidden;transition:all .25s;
    backdrop-filter:blur(10px);
}
.geo-card::before{content:'';position:absolute;left:0;top:0;bottom:0;width:3px;
    background:linear-gradient(180deg,var(--red),var(--yellow));
    transform:scaleY(0);transition:transform .3s;transform-origin:top;}
.geo-card:hover{border-color:rgba(255,214,0,.3);transform:translateX(4px);
    box-shadow:0 4px 20px rgba(255,214,0,.05);}
.geo-card:hover::before{transform:scaleY(1);}
.gc-name{font-weight:700;color:#fff;font-size:.88rem;}
.gc-desc{font-size:.75rem;color:rgba(255,255,255,.35);margin-top:3px;line-height:1.5;}

/* Model cards */
.mc{background:rgba(6,8,20,.7);border:1px solid rgba(255,255,255,.08);
    border-left:3px solid transparent;border-radius:8px;
    padding:.85rem 1rem;margin-bottom:.6rem;
    transition:all .22s;backdrop-filter:blur(10px);}
.mc:hover{border-left-color:var(--yellow);border-color:rgba(255,214,0,.25);}
.mc.sel{
    border-left-color:var(--red);border-color:rgba(255,23,68,.3);
    background:rgba(255,23,68,.06);
    box-shadow:0 0 20px rgba(255,23,68,.06);
}
.mc-name{font-weight:700;color:#fff;font-size:.87rem;}
.mc-desc{font-size:.75rem;color:rgba(255,255,255,.35);margin-top:3px;line-height:1.5;}
.mc-meta{font-size:.69rem;color:rgba(255,255,255,.2);margin-top:4px;}
.tag{display:inline-block;font-size:.62rem;font-weight:700;padding:1px 8px;border-radius:10px;margin-left:6px;}
.tag-b{background:rgba(255,23,68,.15);color:var(--red);border:1px solid rgba(255,23,68,.4);}
.tag-p{background:rgba(0,230,118,.1);color:var(--green);border:1px solid rgba(0,230,118,.35);}

/* Metrics */
.mrow{display:flex;gap:.6rem;margin-bottom:1rem;flex-wrap:wrap;}
.mbox{flex:1;min-width:90px;border-radius:8px;padding:.7rem;animation:popin .5s ease both;
    border:1px solid;}
.mbox:nth-child(1){background:rgba(255,255,255,.05);border-color:rgba(255,255,255,.2);}
.mbox:nth-child(2){background:rgba(0,230,118,.07);border-color:rgba(0,230,118,.3);animation-delay:.07s;}
.mbox:nth-child(3){background:rgba(255,214,0,.06);border-color:rgba(255,214,0,.25);animation-delay:.14s;}
.mbox:nth-child(4){background:rgba(255,23,68,.06);border-color:rgba(255,23,68,.25);animation-delay:.21s;}
@keyframes popin{from{opacity:0;transform:scale(.8);}to{opacity:1;transform:none;}}
.mbox:nth-child(1) .mval{color:#fff;text-shadow:0 0 14px rgba(255,255,255,.5);}
.mbox:nth-child(2) .mval{color:var(--green);text-shadow:0 0 14px rgba(0,230,118,.6);}
.mbox:nth-child(3) .mval{color:var(--yellow);text-shadow:0 0 14px rgba(255,214,0,.6);}
.mbox:nth-child(4) .mval{color:var(--red);text-shadow:0 0 14px rgba(255,23,68,.6);}
.mval{font-family:'Space Mono',monospace;font-size:1.2rem;font-weight:700;}
.mlbl{font-size:.65rem;color:rgba(255,255,255,.35);margin-top:2px;letter-spacing:.5px;}

.img-frame{border:1px solid rgba(255,255,255,.12);border-radius:8px;overflow:hidden;position:relative;}
.img-label{position:absolute;top:7px;left:7px;z-index:5;
    background:rgba(6,6,16,.92);color:var(--yellow);
    font-size:.67rem;font-weight:700;letter-spacing:1px;text-transform:uppercase;
    padding:2px 9px;border-radius:4px;border:1px solid rgba(255,214,0,.4);
    box-shadow:0 0 10px rgba(255,214,0,.2);}
.img-label.sr{color:var(--green);border-color:rgba(0,230,118,.4);box-shadow:0 0 10px rgba(0,230,118,.2);}

/* Info boxes */
.ibox{background:rgba(0,229,255,.05);border:1px solid rgba(0,229,255,.2);border-left:3px solid var(--cyan);
    border-radius:6px;padding:.65rem .9rem;font-size:.8rem;color:rgba(255,255,255,.55);margin-bottom:.6rem;}
.wbox{background:rgba(255,214,0,.05);border:1px solid rgba(255,214,0,.25);border-left:3px solid var(--yellow);
    border-radius:6px;padding:.65rem .9rem;font-size:.8rem;color:rgba(255,214,0,.8);margin-bottom:.6rem;}
.okbox{background:rgba(0,230,118,.05);border:1px solid rgba(0,230,118,.25);border-left:3px solid var(--green);
    border-radius:6px;padding:.65rem .9rem;font-size:.8rem;color:var(--green);margin-bottom:.6rem;}

/* Upload */
.upload-zone{border:2px dashed rgba(255,255,255,.15);border-radius:10px;
    padding:1.2rem;text-align:center;background:rgba(255,255,255,.02);margin-bottom:.7rem;
    animation:zone-glow 3s ease-in-out infinite;}
@keyframes zone-glow{0%,100%{box-shadow:0 0 0 rgba(255,214,0,0);}50%{box-shadow:0 0 20px rgba(255,214,0,.08);}}

/* Empty */
.empty{display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:340px;gap:1rem;}
.empty-icon{font-size:3.5rem;opacity:.2;animation:float 4s ease-in-out infinite;}
@keyframes float{0%,100%{transform:translateY(0);}50%{transform:translateY(-10px);}}
.empty-text{font-size:.87rem;color:rgba(255,255,255,.25);text-align:center;}

/* ── Action buttons ── */
.stButton>button{
    background:linear-gradient(135deg,#cc0000,#ff1744) !important;
    color:#fff !important;border:none !important;border-radius:6px !important;
    font-weight:700 !important;font-size:.88rem !important;letter-spacing:.5px !important;
    box-shadow:0 0 20px rgba(255,23,68,.3) !important;transition:all .2s !important;
    text-transform:uppercase !important;
}
.stButton>button:hover{
    background:linear-gradient(135deg,#ff1744,#ff6090) !important;
    box-shadow:0 0 35px rgba(255,23,68,.55) !important;transform:translateY(-1px) !important;
}
.stButton>button:disabled{background:rgba(255,255,255,.05) !important;box-shadow:none !important;color:rgba(255,255,255,.2) !important;}

div.dl-wrap .stDownloadButton>button{
    background:linear-gradient(135deg,#005522,#00e676) !important;
    color:#fff !important;border:none !important;border-radius:6px !important;
    font-weight:700 !important;box-shadow:0 0 20px rgba(0,230,118,.3) !important;
    transition:all .2s !important;text-transform:uppercase !important;
}
div.dl-wrap .stDownloadButton>button:hover{
    background:linear-gradient(135deg,#00cc66,#80ffb8) !important;
    box-shadow:0 0 35px rgba(0,230,118,.5) !important;transform:translateY(-1px) !important;
}

div[data-testid="stSelectbox"]>div{
    background:rgba(6,8,20,.95) !important;border:1px solid rgba(255,255,255,.15) !important;
    border-radius:6px !important;color:#fff !important;
}
div[data-testid="stFileUploader"]{
    background:rgba(255,255,255,.02) !important;border:2px dashed rgba(255,255,255,.15) !important;
    border-radius:10px !important;transition:all .2s !important;
}
div[data-testid="stFileUploader"]:hover{
    border-color:rgba(255,214,0,.5) !important;background:rgba(255,214,0,.03) !important;
}
.stCheckbox label{color:rgba(255,255,255,.55) !important;font-size:.87rem !important;}
.stTabs [data-baseweb="tab"]{
    background:rgba(6,8,20,.8) !important;color:rgba(255,255,255,.3) !important;
    border-radius:6px 6px 0 0 !important;border:1px solid rgba(255,255,255,.08) !important;
    font-weight:600 !important;font-size:.8rem !important;
}
.stTabs [aria-selected="true"]{
    background:rgba(255,23,68,.1) !important;color:var(--yellow) !important;
    border-top:2px solid var(--red) !important;border-bottom-color:transparent !important;
    text-shadow:0 0 10px rgba(255,214,0,.4) !important;
}
.bdone{background:rgba(0,230,118,.12);color:var(--green);padding:2px 10px;border-radius:12px;font-size:.7rem;font-weight:700;border:1px solid rgba(0,230,118,.35);}
.brunning{background:rgba(255,214,0,.1);color:var(--yellow);padding:2px 10px;border-radius:12px;font-size:.7rem;font-weight:700;border:1px solid rgba(255,214,0,.3);}
.bfailed{background:rgba(255,23,68,.12);color:var(--red);padding:2px 10px;border-radius:12px;font-size:.7rem;font-weight:700;border:1px solid rgba(255,23,68,.35);}
.bqueued{background:rgba(255,255,255,.07);color:#fff;padding:2px 10px;border-radius:12px;font-size:.7rem;font-weight:700;border:1px solid rgba(255,255,255,.2);}

.site-footer{position:relative;z-index:10;
    background:rgba(4,4,12,.98);border-top:2px solid rgba(255,23,68,.3);
    padding:1.2rem 2.5rem;font-size:.72rem;color:rgba(255,255,255,.25);
    display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:.5rem;}
.footer-brand{
    color:var(--yellow);
    text-shadow:0 0 20px rgba(255,214,0,.4);
    font-weight:700;
}

/* ── Prevent History Bug on Image Fullscreen ── */
button[title="View fullscreen"], 
[data-testid="StyledFullScreenButton"] { 
    display: none !important; 
}
</style>
""", unsafe_allow_html=True)

# =========================================================================
#  EARTH BACKGROUND ELEMENT  (rendered via HTML injection)
# =========================================================================
st.markdown('<div id="earth-bg"></div>', unsafe_allow_html=True)

# =========================================================================
#  NAV BAR
# =========================================================================
_pages = [
    ("home",     "\U0001f30d Home"),
    ("process",  "\U0001f4e1 Process Imagery"),
    ("history",  "\U0001f4cb Job History"),
    ("analytics","\U0001f4ca Analytics"),
]

# ── Single nav bar: brand + buttons ──
st.markdown(
    '<div class="nav-bar-row">'
    '<div class="nav-brand-wrap">'
    '<span class="nav-brand-icon">\U0001f6f0</span>'
    '<div><div class="nav-brand-name">NTRO &mdash; SIH26142</div>'
    '<div class="nav-brand-sub">Satellite SR System</div></div>'
    '</div>',
    unsafe_allow_html=True,
)

# Nav buttons — the ONLY functional nav, styled via CSS
_ncols = st.columns([1,1,1,1,2])
for i,(k,lbl) in enumerate(_pages):
    _active_cls = "nav-btn-active" if st.session_state.page==k else "nav-btn-col"
    with _ncols[i]:
        st.markdown(f'<div class="{_active_cls}">', unsafe_allow_html=True)
        if st.button(lbl, key=f"nb_{k}", use_container_width=True):
            st.session_state.page = k
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

with _ncols[4]:
    st.markdown(
        '<div class="nav-pills-wrap">'
        '<span class="nav-pill">SIH 2026</span>'
        '<span class="nav-pill orange">SENTINEL-2</span>'
        '</div>',
        unsafe_allow_html=True,
    )

st.markdown('</div>', unsafe_allow_html=True)  # close nav-bar-row

# =========================================================================
#  ANIMATED HERO  (using components.html for proper rendering)
# =========================================================================
if st.session_state.page == "home":

    HERO_HTML = """<!DOCTYPE html>
<html>
<head>
<style>
*{margin:0;padding:0;box-sizing:border-box;}
body{background:transparent;font-family:'Space Grotesk','Segoe UI',sans-serif;overflow:hidden;}
.container{display:flex;align-items:center;justify-content:space-between;
    padding:2.5rem 3rem;min-height:75vh;gap:2rem;}

/* ── Text ── */
.txt{flex:1;min-width:280px;}
.eyebrow{display:inline-flex;align-items:center;gap:.5rem;
    background:rgba(0,212,255,.1);border:1px solid rgba(0,212,255,.3);
    color:#00d4ff;border-radius:20px;padding:4px 16px;
    font-size:.7rem;font-weight:600;letter-spacing:2px;text-transform:uppercase;
    margin-bottom:1.1rem;animation:fu .7s ease both;}
.title{font-family:'Barlow Condensed','Arial Narrow',sans-serif;
    font-size:clamp(2.2rem,5vw,4.2rem);font-weight:700;color:#fff;
    line-height:1.08;margin-bottom:.9rem;
    text-shadow:0 2px 40px rgba(0,0,0,.9),0 0 60px rgba(0,210,255,.12);
    animation:fu .85s .1s both;}
.ac{color:#00d4ff;} .ag{color:#52b788;}
.sub{font-size:.93rem;color:#3a5a7a;line-height:1.72;
    max-width:460px;margin-bottom:1.5rem;animation:fu .85s .2s both;}
.badges{display:flex;gap:.5rem;flex-wrap:wrap;animation:fu .85s .3s both;}
.badge{font-size:.69rem;font-weight:600;padding:4px 11px;border-radius:4px;border:1px solid;}
.b1{background:rgba(13,79,124,.3);border-color:rgba(13,79,124,.6);color:#5ab0e0;}
.b2{background:rgba(45,90,39,.35);border-color:rgba(82,183,136,.5);color:#52b788;}
.b3{background:rgba(244,162,97,.1);border-color:rgba(244,162,97,.45);color:#f4a261;}
@keyframes fu{from{opacity:0;transform:translateY(16px);}to{opacity:1;transform:none;}}

/* ── Earth scene ── */
.scene{position:relative;width:340px;height:340px;flex-shrink:0;}

.earth-glow{position:absolute;inset:-60px;border-radius:50%;
    background:radial-gradient(circle,rgba(20,90,180,.25) 0%,transparent 65%);
    animation:ep 5s ease-in-out infinite;}
@keyframes ep{0%,100%{transform:scale(1);opacity:.6;}50%{transform:scale(1.12);opacity:1;}}

.earth{
    position:absolute;top:50%;left:50%;
    transform:translate(-50%,-50%);
    width:240px;height:240px;border-radius:50%;
    background:
        radial-gradient(ellipse 80px 35px at 30% 22%, rgba(220,240,255,.5) 0%,transparent 55%),
        radial-gradient(ellipse 55px 22px at 62% 30%, rgba(220,240,255,.4) 0%,transparent 55%),
        radial-gradient(ellipse 45px 18px at 20% 60%, rgba(220,240,255,.3) 0%,transparent 52%),
        radial-gradient(ellipse 60px 22px at 75% 65%, rgba(220,240,255,.35) 0%,transparent 52%),
        radial-gradient(ellipse 90px 110px at 52% 45%, #2d5a27 0%,#1a3d15 55%,transparent 70%),
        radial-gradient(ellipse 55px 80px at 37% 48%, #3a6e22 0%,#2d5a27 50%,transparent 68%),
        radial-gradient(ellipse 40px 50px at 70% 28%, #4a7c30 0%,transparent 65%),
        radial-gradient(ellipse 35px 40px at 22% 35%, #2d5a27 0%,transparent 60%),
        radial-gradient(ellipse 30px 38px at 78% 58%, #2d5a27 0%,transparent 60%),
        radial-gradient(circle,#1565a0 0%,#0d4f7c 42%,#083060 78%,#041e36 100%);
    box-shadow:
        inset -28px -14px 55px rgba(0,0,0,.65),
        inset 8px 4px 22px rgba(255,255,255,.05),
        0 0 50px rgba(13,79,124,.4),
        0 0 100px rgba(13,79,124,.12);
    animation:earth-rot 60s linear infinite;
}
@keyframes earth-rot{
    0%  {background-position:0% 50%;}
    100%{background-position:200% 50%;}
}

/* atmosphere */
.atmo{position:absolute;top:50%;left:50%;
    transform:translate(-50%,-50%);
    width:260px;height:260px;border-radius:50%;
    background:radial-gradient(circle,transparent 46%,
        rgba(80,180,255,.14) 50%,rgba(50,130,220,.06) 55%,transparent 60%);
    box-shadow:0 0 60px rgba(80,180,255,.1);pointer-events:none;}

/* orbit ring */
.orbit-ring{position:absolute;top:50%;left:50%;
    transform:translate(-50%,-50%);
    width:308px;height:308px;border-radius:50%;
    border:1px dashed rgba(0,212,255,.22);pointer-events:none;}

/* satellite */
.sat-orbit{
    position:absolute;top:50%;left:50%;
    width:308px;height:308px;
    transform:translate(-50%,-50%);
    animation:orbit 8s linear infinite;
}
@keyframes orbit{to{transform:translate(-50%,-50%) rotate(360deg);}}

.sat{
    position:absolute;top:-14px;left:50%;
    transform:translateX(-50%) rotate(-90deg);
    width:30px;height:14px;
    animation:counter-orbit 8s linear infinite;
}
@keyframes counter-orbit{to{transform:translateX(-50%) rotate(270deg);}}

.sat-body{
    position:absolute;top:3px;left:8px;
    width:14px;height:8px;border-radius:2px;
    background:linear-gradient(135deg,#b0cce0,#80aac8);
    box-shadow:0 0 8px rgba(0,212,255,.6);
}
.sat-wing{
    position:absolute;top:4px;
    width:8px;height:6px;border-radius:1px;
    background:linear-gradient(180deg,#0d4f7c,#1565a0);
    border:1px solid rgba(0,212,255,.5);
}
.sat-wing.l{left:-8px;} .sat-wing.r{right:-8px;}
.sat-dot{
    position:absolute;top:2px;right:1px;
    width:3px;height:3px;border-radius:50%;
    background:#f4a261;box-shadow:0 0 5px #f4a261;
    animation:blink 1.4s step-end infinite;
}
@keyframes blink{0%,100%{opacity:1;}50%{opacity:.1;}}

/* scan beam */
.beam-orbit{
    position:absolute;top:50%;left:50%;
    width:308px;height:308px;
    transform:translate(-50%,-50%);
    animation:orbit 8s linear infinite;
    pointer-events:none;
}
.beam{
    position:absolute;top:0;left:50%;
    transform:translateX(-50%);
    width:2px;height:52%;
    background:linear-gradient(180deg,rgba(0,212,255,.9),rgba(0,212,255,0));
    box-shadow:0 0 8px rgba(0,212,255,.7);
}

/* scan swath on earth */
.swath-orbit{
    position:absolute;top:50%;left:50%;
    width:240px;height:240px;
    transform:translate(-50%,-50%);
    border-radius:50%;overflow:hidden;
    animation:orbit 8s linear infinite;
    pointer-events:none;
}
.swath{
    position:absolute;top:0;left:50%;
    transform:translateX(-50%);
    width:22px;height:50%;
    background:linear-gradient(180deg,rgba(0,212,255,.5),rgba(0,212,255,.05));
    border-radius:0 0 11px 11px;
}

/* coverage grid on earth */
.grid-overlay{
    position:absolute;top:50%;left:50%;
    transform:translate(-50%,-50%);
    width:240px;height:240px;border-radius:50%;
    overflow:hidden;pointer-events:none;
    background-image:
        linear-gradient(rgba(0,212,255,.07) 1px,transparent 1px),
        linear-gradient(90deg,rgba(0,212,255,.07) 1px,transparent 1px);
    background-size:30px 30px;
    animation:grid-fade 4s ease-in-out infinite;
}
@keyframes grid-fade{0%,100%{opacity:.4;}50%{opacity:.8;}}

/* data label */
.data-label{
    position:absolute;bottom:-38px;left:50%;transform:translateX(-50%);
    font-family:'Space Mono',monospace;font-size:.62rem;color:#00d4ff;
    white-space:nowrap;letter-spacing:1px;
    animation:data-flicker .2s step-end infinite;
}
@keyframes data-flicker{0%{opacity:1;}50%{opacity:.85;}100%{opacity:1;}}

/* ── Pixel SR demo ── */
.px-demo{
    display:flex;align-items:center;gap:1rem;margin-top:1.8rem;
}
.px-panel{text-align:center;}
.px-label{font-family:'Space Mono',monospace;font-size:.62rem;letter-spacing:1.5px;
    text-transform:uppercase;margin-bottom:.4rem;}
.px-label.low{color:#f4a261;} .px-label.hi{color:#52b788;}
.px-grid{display:grid;gap:2px;border-radius:5px;overflow:hidden;
    border:1px solid rgba(0,180,255,.2);}
.px-grid.low{grid-template-columns:repeat(6,1fr);width:84px;height:84px;}
.px-grid.hi {grid-template-columns:repeat(16,1fr);width:84px;height:84px;}
.px{border-radius:1px;animation:pf 3s ease-in-out infinite;}
@keyframes pf{0%,100%{opacity:.7;}50%{opacity:1;}}
.sr-arr{font-size:1.6rem;color:#00d4ff;animation:ap 2s ease-in-out infinite;}
@keyframes ap{0%,100%{color:#00d4ff;transform:scale(1);}50%{color:#52b788;transform:scale(1.2);}}
.sr-lbl{font-family:'Space Mono',monospace;font-size:.55rem;color:#00d4ff;margin-top:3px;}
</style>
</head>
<body>
<div class="container">

  <!-- LEFT: Text -->
  <div class="txt">
    <div class="eyebrow">&#128225;&nbsp; Sentinel-2 Imagery Enhancement &nbsp;&middot;&nbsp; SIH26142</div>
    <div class="title">
      From <span class="ac">10&nbsp;metre</span><br>
      to <span class="ag">sub&nbsp;4&nbsp;metre</span><br>
      Resolution
    </div>
    <div class="sub">
      NTRO&rsquo;s deep-learning super-resolution engine enhances
      Sentinel-2 multispectral satellite imagery using models trained
      exclusively on real earth-observation data &mdash; zero hallucination,
      quantified per-pixel uncertainty.
    </div>
    <div class="badges">
      <span class="badge b1">&#127758; Sentinel-2 Native</span>
      <span class="badge b2">&times;4 Spatial Enhancement</span>
      <span class="badge b3">&#128752; Orbital AI Models</span>
      <span class="badge b1">&#128205; 2.5m Output GSD</span>
    </div>

    <!-- Pixel demo -->
    <div class="px-demo">
      <div class="px-panel">
        <div class="px-label low">10m Input</div>
        <div class="px-grid low">
          <div class="px" style="background:hsl(210,35%,22%);animation-delay:0s"></div>
          <div class="px" style="background:hsl(120,30%,18%);animation-delay:.1s"></div>
          <div class="px" style="background:hsl(180,25%,20%);animation-delay:.2s"></div>
          <div class="px" style="background:hsl(210,38%,25%);animation-delay:.15s"></div>
          <div class="px" style="background:hsl(130,32%,15%);animation-delay:.05s"></div>
          <div class="px" style="background:hsl(200,30%,22%);animation-delay:.25s"></div>
          <div class="px" style="background:hsl(120,35%,20%);animation-delay:.3s"></div>
          <div class="px" style="background:hsl(215,28%,18%);animation-delay:.1s"></div>
          <div class="px" style="background:hsl(140,32%,22%);animation-delay:.2s"></div>
          <div class="px" style="background:hsl(205,36%,24%);animation-delay:0s"></div>
          <div class="px" style="background:hsl(125,30%,16%);animation-delay:.15s"></div>
          <div class="px" style="background:hsl(210,33%,20%);animation-delay:.25s"></div>
          <div class="px" style="background:hsl(200,28%,18%);animation-delay:.35s"></div>
          <div class="px" style="background:hsl(130,35%,21%);animation-delay:.05s"></div>
          <div class="px" style="background:hsl(215,30%,23%);animation-delay:.18s"></div>
          <div class="px" style="background:hsl(120,32%,17%);animation-delay:.28s"></div>
          <div class="px" style="background:hsl(210,36%,21%);animation-delay:.08s"></div>
          <div class="px" style="background:hsl(195,30%,19%);animation-delay:.22s"></div>
          <div class="px" style="background:hsl(135,34%,23%);animation-delay:.12s"></div>
          <div class="px" style="background:hsl(210,29%,18%);animation-delay:.32s"></div>
          <div class="px" style="background:hsl(125,33%,20%);animation-delay:.02s"></div>
          <div class="px" style="background:hsl(205,37%,25%);animation-delay:.17s"></div>
          <div class="px" style="background:hsl(130,31%,16%);animation-delay:.27s"></div>
          <div class="px" style="background:hsl(215,35%,22%);animation-delay:.07s"></div>
          <div class="px" style="background:hsl(200,33%,20%);animation-delay:.37s"></div>
          <div class="px" style="background:hsl(120,36%,18%);animation-delay:.13s"></div>
          <div class="px" style="background:hsl(210,30%,21%);animation-delay:.23s"></div>
          <div class="px" style="background:hsl(195,28%,17%);animation-delay:.03s"></div>
          <div class="px" style="background:hsl(135,32%,22%);animation-delay:.33s"></div>
          <div class="px" style="background:hsl(210,37%,24%);animation-delay:.11s"></div>
          <div class="px" style="background:hsl(125,30%,19%);animation-delay:.21s"></div>
          <div class="px" style="background:hsl(205,34%,21%);animation-delay:.31s"></div>
          <div class="px" style="background:hsl(130,33%,17%);animation-delay:.09s"></div>
          <div class="px" style="background:hsl(215,31%,23%);animation-delay:.19s"></div>
          <div class="px" style="background:hsl(120,34%,20%);animation-delay:.29s"></div>
          <div class="px" style="background:hsl(210,28%,18%);animation-delay:.39s"></div>
        </div>
      </div>
      <div style="text-align:center;">
        <div class="sr-arr">&rsaquo;&rsaquo;</div>
        <div class="sr-lbl">&times;4 SR</div>
      </div>
      <div class="px-panel">
        <div class="px-label hi">2.5m Output</div>
        <div class="px-grid hi">
          <div class="px" style="background:hsl(210,45%,32%);animation-delay:.04s"></div>
          <div class="px" style="background:hsl(120,42%,28%);animation-delay:.09s"></div>
          <div class="px" style="background:hsl(195,40%,30%);animation-delay:.14s"></div>
          <div class="px" style="background:hsl(210,48%,35%);animation-delay:.19s"></div>
          <div class="px" style="background:hsl(130,44%,25%);animation-delay:.24s"></div>
          <div class="px" style="background:hsl(200,42%,32%);animation-delay:.29s"></div>
          <div class="px" style="background:hsl(120,46%,30%);animation-delay:.34s"></div>
          <div class="px" style="background:hsl(215,40%,28%);animation-delay:.39s"></div>
          <div class="px" style="background:hsl(140,44%,32%);animation-delay:.05s"></div>
          <div class="px" style="background:hsl(205,47%,34%);animation-delay:.10s"></div>
          <div class="px" style="background:hsl(125,42%,26%);animation-delay:.15s"></div>
          <div class="px" style="background:hsl(210,45%,30%);animation-delay:.20s"></div>
          <div class="px" style="background:hsl(200,40%,28%);animation-delay:.25s"></div>
          <div class="px" style="background:hsl(130,46%,31%);animation-delay:.30s"></div>
          <div class="px" style="background:hsl(215,42%,33%);animation-delay:.35s"></div>
          <div class="px" style="background:hsl(120,44%,27%);animation-delay:.40s"></div>
          <div class="px" style="background:hsl(210,47%,31%);animation-delay:.03s"></div>
          <div class="px" style="background:hsl(195,42%,29%);animation-delay:.08s"></div>
          <div class="px" style="background:hsl(135,45%,33%);animation-delay:.13s"></div>
          <div class="px" style="background:hsl(210,41%,28%);animation-delay:.18s"></div>
          <div class="px" style="background:hsl(125,44%,30%);animation-delay:.23s"></div>
          <div class="px" style="background:hsl(205,48%,35%);animation-delay:.28s"></div>
          <div class="px" style="background:hsl(130,43%,26%);animation-delay:.33s"></div>
          <div class="px" style="background:hsl(215,46%,32%);animation-delay:.38s"></div>
          <div class="px" style="background:hsl(200,44%,30%);animation-delay:.02s"></div>
          <div class="px" style="background:hsl(120,47%,28%);animation-delay:.07s"></div>
          <div class="px" style="background:hsl(210,42%,31%);animation-delay:.12s"></div>
          <div class="px" style="background:hsl(195,40%,27%);animation-delay:.17s"></div>
          <div class="px" style="background:hsl(135,44%,32%);animation-delay:.22s"></div>
          <div class="px" style="background:hsl(210,48%,34%);animation-delay:.27s"></div>
          <div class="px" style="background:hsl(125,42%,29%);animation-delay:.32s"></div>
          <div class="px" style="background:hsl(205,45%,31%);animation-delay:.37s"></div>
          <div class="px" style="background:hsl(130,44%,27%);animation-delay:.01s"></div>
          <div class="px" style="background:hsl(215,42%,33%);animation-delay:.06s"></div>
          <div class="px" style="background:hsl(120,46%,30%);animation-delay:.11s"></div>
          <div class="px" style="background:hsl(210,40%,28%);animation-delay:.16s"></div>
          <div class="px" style="background:hsl(200,44%,32%);animation-delay:.21s"></div>
          <div class="px" style="background:hsl(120,43%,26%);animation-delay:.26s"></div>
          <div class="px" style="background:hsl(210,47%,33%);animation-delay:.31s"></div>
          <div class="px" style="background:hsl(195,41%,29%);animation-delay:.36s"></div>
          <div class="px" style="background:hsl(135,45%,31%);animation-delay:.41s"></div>
          <div class="px" style="background:hsl(210,42%,30%);animation-delay:.04s"></div>
          <div class="px" style="background:hsl(125,44%,28%);animation-delay:.09s"></div>
          <div class="px" style="background:hsl(205,47%,34%);animation-delay:.14s"></div>
          <div class="px" style="background:hsl(130,43%,26%);animation-delay:.19s"></div>
          <div class="px" style="background:hsl(215,46%,32%);animation-delay:.24s"></div>
          <div class="px" style="background:hsl(200,44%,30%);animation-delay:.29s"></div>
          <div class="px" style="background:hsl(120,47%,28%);animation-delay:.34s"></div>
          <div class="px" style="background:hsl(210,41%,31%);animation-delay:.39s"></div>
          <div class="px" style="background:hsl(195,40%,27%);animation-delay:.44s"></div>
          <div class="px" style="background:hsl(135,44%,33%);animation-delay:.06s"></div>
          <div class="px" style="background:hsl(210,48%,34%);animation-delay:.11s"></div>
          <div class="px" style="background:hsl(125,42%,29%);animation-delay:.16s"></div>
          <div class="px" style="background:hsl(205,45%,31%);animation-delay:.21s"></div>
          <div class="px" style="background:hsl(130,44%,27%);animation-delay:.26s"></div>
          <div class="px" style="background:hsl(215,42%,33%);animation-delay:.31s"></div>
          <div class="px" style="background:hsl(120,46%,30%);animation-delay:.36s"></div>
          <div class="px" style="background:hsl(210,40%,28%);animation-delay:.41s"></div>
          <div class="px" style="background:hsl(200,44%,32%);animation-delay:.46s"></div>
          <div class="px" style="background:hsl(120,43%,26%);animation-delay:.08s"></div>
          <div class="px" style="background:hsl(210,47%,33%);animation-delay:.13s"></div>
          <div class="px" style="background:hsl(195,41%,29%);animation-delay:.18s"></div>
          <div class="px" style="background:hsl(135,45%,31%);animation-delay:.23s"></div>
        </div>
      </div>
    </div>
  </div>

  <!-- RIGHT: Earth satellite scene -->
  <div class="scene">
    <div class="earth-glow"></div>
    <div class="earth"></div>
    <div class="atmo"></div>
    <div class="grid-overlay"></div>
    <div class="orbit-ring"></div>
    <!-- swath -->
    <div class="swath-orbit"><div class="swath"></div></div>
    <!-- beam -->
    <div class="beam-orbit"><div class="beam"></div></div>
    <!-- satellite -->
    <div class="sat-orbit">
      <div class="sat">
        <div class="sat-wing l"></div>
        <div class="sat-body"><div class="sat-dot"></div></div>
        <div class="sat-wing r"></div>
      </div>
    </div>
    <div class="data-label">&#9608; 10m/px &nbsp; 290km SWATH &nbsp; INDIA-PASS</div>
  </div>

</div>
</body>
</html>"""

    st.html(HERO_HTML)

    # Stats strip
    st.markdown("""
    <div class="stats-strip">
      <div class="stat-item"><div class="stat-num">&times;4</div><div class="stat-label">Upscale Factor</div></div>
      <div class="stat-item"><div class="stat-num">2.5m</div><div class="stat-label">Output GSD</div></div>
      <div class="stat-item"><div class="stat-num">290km</div><div class="stat-label">S-2 Swath Width</div></div>
      <div class="stat-item"><div class="stat-num">13</div><div class="stat-label">Spectral Bands</div></div>
      <div class="stat-item"><div class="stat-num">5d</div><div class="stat-label">Revisit Time</div></div>
      <div class="stat-item"><div class="stat-num">CPU</div><div class="stat-label">No GPU Needed</div></div>
    </div>
    """, unsafe_allow_html=True)

    # Body
    st.markdown('<div class="page-wrap">', unsafe_allow_html=True)
    lc,rc = st.columns([3,2], gap="large")

    with lc:
        st.markdown('<div class="sec-title">Geo-Imagery <span class="sec-ac">Applications</span></div>'
                    '<div class="sec-sub">Where sub-4m earth observation changes everything</div>',
                    unsafe_allow_html=True)
        _apps = [
            ("\U0001f33e","Precision Agriculture",
             "Sub-field crop stress mapping, irrigation canal detection, field boundary delineation"),
            ("\U0001f3d9","Urban Cartography",
             "Building footprint extraction, road detection, settlement boundary mapping"),
            ("\U0001f30a","Hydrological Mapping",
             "Flood extent, river width, coastal wetland and reservoir monitoring"),
            ("\U0001f525","Disaster Intelligence",
             "Pre/post event change detection, damage assessment, landslide mapping"),
            ("\U0001f332","Forest & Carbon",
             "Deforestation alerts, canopy proxy, REDD+ monitoring at field scale"),
            ("\U0001f6e1","NTRO Defence",
             "Intelligence imagery with LDSR-S2 uncertainty maps for critical pixel analysis"),
        ]
        for icon,name,desc in _apps:
            st.markdown(
                f'<div class="geo-card">'
                f'<div style="display:flex;align-items:flex-start;gap:.6rem;">'
                f'<span style="font-size:1.4rem;flex-shrink:0;">{icon}</span>'
                f'<div><div class="gc-name">{name}</div><div class="gc-desc">{desc}</div></div>'
                '</div></div>',
                unsafe_allow_html=True,
            )

    with rc:
        st.markdown('<div class="sec-title">SR <span class="sec-ac">Model Stack</span></div>'
                    '<div class="sec-sub">Sentinel-2 specific — no generic natural-image SR</div>',
                    unsafe_allow_html=True)
        for mname,minfo in MODEL_REGISTRY.items():
            tc = "tag-b" if minfo["physical_bias"]=="Balanced" else "tag-p"
            st.markdown(
                f'<div class="mc"><div class="mc-name">{mname}'
                f'<span class="tag {tc}">{minfo["physical_bias"]}</span></div>'
                f'<div class="mc-desc">{minfo["description"]}</div>'
                f'<div class="mc-meta">\U0001f4c4 {minfo["paper"]} '
                f'\u00b7 \u00d7{minfo["scale"]} \u2192 {minfo["output_res_m"]}m GSD</div>'
                '</div>',
                unsafe_allow_html=True,
            )
        st.markdown(
            '<div class="ibox" style="margin-top:.8rem;">'
            '\u2696\ufe0f <b>Physical\u2013Logical Trade-off:</b> '
            'DSen2 &amp; Bicubic are radiometrically faithful (zero hallucination). '
            'LDSR-S2 uses back-projection + per-pixel uncertainty maps '
            'critical for NTRO intelligence analysis.'
            '</div>',
            unsafe_allow_html=True,
        )
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("\U0001f4e1  Launch Processing Engine", key="sec_cta", use_container_width=True):
            st.session_state.page = "process"
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="site-footer">'
        '<div><span class="footer-brand">NTRO</span> \u00b7 National Technical Research Organisation \u00b7 Government of India</div>'
        '<div>Smart India Hackathon 2026 \u00b7 Problem SIH26142</div>'
        '</div>',
        unsafe_allow_html=True,
    )

# =========================================================================
#  PROCESS IMAGERY
# =========================================================================
elif st.session_state.page == "process":
    st.markdown('<div class="page-wrap">', unsafe_allow_html=True)
    st.markdown(
        '<div class="sec-title" style="padding-top:1.5rem;">\U0001f4e1 Satellite Image <span class="sec-ac">Processing Engine</span></div>'
        '<div class="sec-sub">Upload a Sentinel-2 GeoTIFF or use the bundled sample tile</div>',
        unsafe_allow_html=True,
    )
    left_col,right_col = st.columns([1,1], gap="large")

    with left_col:
        st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
        st.markdown('<div class="panel-title">\U0001f4e5 Input Satellite Image</div>', unsafe_allow_html=True)
        use_sample = st.checkbox("Use bundled sample Sentinel-2 tile (recommended)", value=True)
        input_path_str = None
        sample_path = Path("static/sample_data/sample_sentinel2.tif")
        if use_sample:
            if not sample_path.exists():
                with st.spinner("Generating sample tile\u2026"):
                    try:
                        import subprocess, sys
                        subprocess.run([sys.executable,"generate_sample_tile.py"],check=True,timeout=30)
                    except Exception as e:
                        st.error(f"Could not generate sample: {e}")
            if sample_path.exists():
                st.markdown(
                    f'<div class="okbox">\u2705 <b>Sample tile ready</b><br>'
                    f'<span style="font-size:.73rem;">{sample_path.name} \u00b7 512\u00d7512 px '
                    f'\u00b7 4-band Sentinel-2 \u00b7 10m GSD</span></div>',
                    unsafe_allow_html=True,
                )
                input_path_str = str(sample_path)

        st.markdown(
            '<div class="panel-title" style="margin-top:1.2rem;">\U0001f4c2 Upload GeoTIFF</div>'
            '<div class="upload-zone">'
            '<div style="font-size:2rem;margin-bottom:.4rem;">\U0001f30d</div>'
            '<div style="font-size:.8rem;color:#1a3a50;">Drag &amp; drop Sentinel-2 GeoTIFF (.tif / .tiff)</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        uploaded = st.file_uploader("Choose file",type=["tif","tiff"],
                                    label_visibility="collapsed",key="uploader")
        if uploaded is not None:
            os.makedirs("uploads",exist_ok=True)
            sp = f"uploads/{uploaded.name}"
            with open(sp,"wb") as fh: fh.write(uploaded.getbuffer())
            input_path_str = sp
            st.markdown(
                f'<div class="okbox">\u2705 <b>Uploaded:</b> {uploaded.name}<br>'
                f'<span style="font-size:.73rem;">{uploaded.size/1024:.1f} KB</span></div>',
                unsafe_allow_html=True,
            )
        st.markdown('<div class="panel-title" style="margin-top:1.2rem;">\U0001f9e0 SR Model</div>',
                    unsafe_allow_html=True)
        model_name = st.selectbox("Model",list(MODEL_REGISTRY.keys()),
                                  label_visibility="collapsed",key="mdl")
        minfo = MODEL_REGISTRY[model_name]
        tc    = "tag-b" if minfo["physical_bias"]=="Balanced" else "tag-p"
        st.markdown(
            f'<div class="mc sel"><div class="mc-name">{model_name}'
            f'<span class="tag {tc}">{minfo["physical_bias"]}</span></div>'
            f'<div class="mc-desc">{minfo["description"]}</div>'
            f'<div class="mc-meta">\U0001f4c4 {minfo["paper"]} \u00b7 '
            f'\u00d7{minfo["scale"]} \u00b7 {minfo["output_res_m"]}m GSD</div></div>',
            unsafe_allow_html=True,
        )
        if model_name == "LDSR-S2 (ESA)":
            st.markdown('<div class="wbox">\u23f1 LDSR-S2 may take 2\u20135 min on CPU.</div>',
                        unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        disabled = (input_path_str is None)
        run_btn = st.button("\U0001f4e1  Run Super-Resolution",
                            use_container_width=True,disabled=disabled,key="run_btn")
        if disabled:
            st.markdown('<div class="wbox">\u26a0\ufe0f Enable sample tile or upload a file above.</div>',
                        unsafe_allow_html=True)

    with right_col:
        st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
        st.markdown('<div class="panel-title">\U0001f4ca SR Results &amp; Output</div>',
                    unsafe_allow_html=True)

        if run_btn and input_path_str:
            os.makedirs("outputs",exist_ok=True)
            safe_m = (model_name.replace(" ","_")
                               .replace("(","").replace(")","").replace("/",""))
            out_sr  = f"outputs/sr_{Path(input_path_str).stem}_{safe_m}.tif"
            out_bic = f"outputs/bicubic_{Path(input_path_str).stem}.tif"
            db       = SessionLocal()
            job_repo = JobRepository(db)
            job      = job_repo.create(filename=Path(input_path_str).name,
                sr_model=model_name,scale_factor=float(minfo["scale"]),input_path=input_path_str)
            job_id = job.id
            job_repo.update_status(job_id,"running")
            db.close()
            with st.spinner(f"\U0001f6f0 Processing via {model_name}\u2026"):
                t0 = time.time()
                result  = run_super_resolution(input_path_str,out_sr,model_name=model_name)
                run_bicubic(input_path_str,out_bic,scale_factor=minfo["scale"])
                metrics = compute_metrics(out_sr,out_bic)
                elapsed = time.time() - t0
            db       = SessionLocal()
            job_repo = JobRepository(db)
            met_repo = MetricsRepository(db)
            job_repo.update_status(job_id,"done",output_path=out_sr)
            met_repo.save(job_id=job_id,psnr=metrics["psnr"],ssim=metrics["ssim"],
                          inference_time=elapsed,output_res_m=minfo["output_res_m"])
            db.close()
            st.session_state["last_result"] = {
                "input":input_path_str,"sr":out_sr,"bicubic":out_bic,
                "model":model_name,"metrics":metrics,"elapsed":elapsed,"result_meta":result}
            st.rerun()

        if "last_result" in st.session_state:
            res     = st.session_state["last_result"]
            psnr    = res["metrics"]["psnr"]
            ssim    = res["metrics"]["ssim"]
            scale   = res["result_meta"].get("scale",MODEL_REGISTRY[res["model"]]["scale"])
            out_res = MODEL_REGISTRY[res["model"]]["output_res_m"]
            if res.get("result_meta",{}).get("fallback"):
                st.markdown(f'<div class="wbox">\u26a0\ufe0f Fell back to Bicubic: '
                            f'{res["result_meta"].get("fallback_reason","")}</div>',
                            unsafe_allow_html=True)
            st.markdown(
                f'<div class="mrow">'
                f'<div class="mbox"><div class="mval">{psnr if psnr is not None else "N/A"}</div><div class="mlbl">PSNR (dB)</div></div>'
                f'<div class="mbox"><div class="mval">{ssim if ssim is not None else "N/A"}</div><div class="mlbl">SSIM</div></div>'
                f'<div class="mbox"><div class="mval">{res["elapsed"]:.1f}s</div><div class="mlbl">Inference Time</div></div>'
                f'<div class="mbox"><div class="mval">\u00d7{scale}</div><div class="mlbl">Upscale</div></div>'
                '</div>', unsafe_allow_html=True)
            os.makedirs("outputs/thumbs",exist_ok=True)
            png_in = f"outputs/thumbs/in_{Path(res['input']).stem}.png"
            png_sr = f"outputs/thumbs/sr_{Path(res['sr']).stem}.png"
            geotiff_to_png(res["input"],png_in)
            geotiff_to_png(res["sr"],   png_sr)
            tab1,tab2 = st.tabs(["\U0001f4f7 Side-by-Side","\u2728 SR Output"])
            with tab1:
                i1,i2 = st.columns(2)
                with i1:
                    st.markdown('<div class="img-frame"><span class="img-label">INPUT 10m</span>', unsafe_allow_html=True)
                    if Path(png_in).exists(): st.image(png_in,use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                with i2:
                    st.markdown(f'<div class="img-frame"><span class="img-label sr">SR {out_res}m</span>', unsafe_allow_html=True)
                    if Path(png_sr).exists(): st.image(png_sr,use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)
            with tab2:
                if Path(png_sr).exists(): st.image(png_sr,use_container_width=True)
            st.markdown("<br>", unsafe_allow_html=True)
            if Path(res["sr"]).exists():
                st.markdown('<div class="dl-wrap">', unsafe_allow_html=True)
                with open(res["sr"],"rb") as fh:
                    st.download_button("\u2b07\ufe0f  Download Enhanced GeoTIFF",fh,
                        file_name=Path(res["sr"]).name,mime="image/tiff",
                        use_container_width=True,key="dl_sr")
                st.markdown('</div>', unsafe_allow_html=True)
                st.markdown(
                    f'<div class="ibox" style="margin-top:.5rem;">'
                    f'\U0001f4be <code style="color:#00d4ff;">{Path(res["sr"]).name}</code><br>'
                    f'{res["model"]} \u00b7 {out_res}m GSD \u00b7 {res["elapsed"]:.1f}s'
                    '</div>', unsafe_allow_html=True)
        else:
            st.markdown(
                '<div class="empty">'
                '<div class="empty-icon">\U0001f6f0</div>'
                '<div class="empty-text">Configure input &amp; model on the left,<br>'
                'then click <b>Run Super-Resolution</b></div>'
                '</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================================
#  JOB HISTORY
# =========================================================================
elif st.session_state.page == "history":
    st.markdown('<div class="page-wrap">', unsafe_allow_html=True)
    st.markdown(
        '<div class="sec-title" style="padding-top:1.5rem;">\U0001f4cb Processing <span class="sec-ac">Job History</span></div>'
        '<div class="sec-sub">All SR jobs persisted in SQLite (swap via DATABASE_URL env var)</div>',
        unsafe_allow_html=True)
    db       = SessionLocal()
    job_repo = JobRepository(db)
    met_repo = MetricsRepository(db)
    jobs     = job_repo.list_all(limit=50)
    if not jobs:
        st.markdown('<div class="empty" style="min-height:260px;"><div class="empty-icon">\U0001f4ed</div>'
                    '<div class="empty-text">No jobs yet. Go to <b>Process Imagery</b>.</div></div>',
                    unsafe_allow_html=True)
    else:
        for job in jobs:
            bc  = {"done":"bdone","running":"brunning","failed":"bfailed"}.get(job.status,"bqueued")
            m   = met_repo.get_by_job(job.id)
            ps  = f"{m.psnr_vs_bicubic:.2f} dB" if m and m.psnr_vs_bicubic else "\u2014"
            ss  = f"{m.ssim_vs_bicubic:.4f}"     if m and m.ssim_vs_bicubic else "\u2014"
            ts  = f"{m.inference_time_sec:.1f}s" if m and m.inference_time_sec else "\u2014"
            rs  = f"{m.output_resolution_m}m"    if m and m.output_resolution_m else "\u2014"
            cre = job.created_at.strftime("%Y-%m-%d %H:%M") if job.created_at else "\u2014"
            with st.expander(f"#{job.id} \u00b7 {job.filename} \u00b7 {job.sr_model}",expanded=False):
                c1,c2 = st.columns([2,1])
                with c1:
                    st.markdown(f'<div style="font-size:.82rem;color:#3a5a7a;line-height:2.1;">'
                        f'<b>Status:</b> <span class="{bc}">{job.status}</span><br>'
                        f'<b>Model:</b> {job.sr_model}<br><b>Scale:</b> \u00d7{job.scale_factor}<br>'
                        f'<b>Created:</b> {cre}</div>', unsafe_allow_html=True)
                with c2:
                    st.markdown(f'<div style="font-size:.82rem;color:#3a5a7a;line-height:2.1;">'
                        f'<b>PSNR:</b> {ps}<br><b>SSIM:</b> {ss}<br>'
                        f'<b>Time:</b> {ts}<br><b>GSD:</b> {rs}</div>', unsafe_allow_html=True)
                if job.output_path and Path(job.output_path).exists():
                    st.markdown('<div class="dl-wrap">', unsafe_allow_html=True)
                    with open(job.output_path,"rb") as fh:
                        st.download_button("\u2b07\ufe0f Download GeoTIFF",fh,
                            file_name=Path(job.output_path).name,
                            mime="image/tiff",key=f"dl_{job.id}")
                    st.markdown('</div>', unsafe_allow_html=True)
    db.close()
    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================================
#  ANALYTICS
# =========================================================================
elif st.session_state.page == "analytics":
    st.markdown('<div class="page-wrap">', unsafe_allow_html=True)
    st.markdown(
        '<div class="sec-title" style="padding-top:1.5rem;">\U0001f4ca Model Analytics <span class="sec-ac">&amp; Validation</span></div>'
        '<div class="sec-sub">SR quality metrics and physical\u2013logical trade-off guide</div>',
        unsafe_allow_html=True)
    db          = SessionLocal()
    all_jobs    = JobRepository(db).list_all(limit=200)
    all_metrics = MetricsRepository(db).list_all()
    db.close()
    if not all_metrics:
        st.markdown('<div class="ibox">\u2139\ufe0f No metrics yet. Run jobs on <b>Process Imagery</b> first.</div>',
                    unsafe_allow_html=True)
    else:
        import pandas as pd
        jm   = {j.id:j for j in all_jobs}
        rows = [{"Job #":j.id,"Model":j.sr_model,"PSNR (dB)":m.psnr_vs_bicubic,
                 "SSIM":m.ssim_vs_bicubic,"Time (s)":m.inference_time_sec,"GSD (m)":m.output_resolution_m}
                for m in all_metrics if (j:=jm.get(m.job_id))]
        df = pd.DataFrame(rows)
        ts,tc,tg = st.tabs(["\U0001f4cb Summary","\U0001f4c8 Charts","\U0001f4d6 Model Guide"])
        with ts:
            st.dataframe(df.style.format({"PSNR (dB)":"{:.2f}","SSIM":"{:.4f}","Time (s)":"{:.1f}"}),
                         use_container_width=True)
        with tc:
            try:
                import plotly.express as px
                cols = ["#00d4ff","#52b788","#c084fc"]
                tmpl = dict(paper_bgcolor="rgba(2,8,20,0)",plot_bgcolor="rgba(2,10,22,.7)",
                            font=dict(family="Space Grotesk",color="#3a5a7a"))
                c1,c2 = st.columns(2)
                with c1:
                    fp=px.bar(df.dropna(subset=["PSNR (dB)"]),x="Job #",y="PSNR (dB)",color="Model",
                        title="PSNR vs Bicubic (dB)",color_discrete_sequence=cols,template="plotly_dark")
                    fp.update_layout(**tmpl);st.plotly_chart(fp,use_container_width=True)
                with c2:
                    fs=px.bar(df.dropna(subset=["SSIM"]),x="Job #",y="SSIM",color="Model",
                        title="SSIM vs Bicubic",color_discrete_sequence=cols,template="plotly_dark")
                    fs.update_layout(**tmpl);st.plotly_chart(fs,use_container_width=True)
            except ImportError:
                st.bar_chart(df.set_index("Job #")[["PSNR (dB)","SSIM"]])
        with tg:
            for mname,minfo in MODEL_REGISTRY.items():
                tc2 = "tag-b" if minfo["physical_bias"]=="Balanced" else "tag-p"
                st.markdown(
                    f'<div class="mc"><div class="mc-name">{mname}'
                    f'<span class="tag {tc2}">{minfo["physical_bias"]}</span></div>'
                    f'<div class="mc-desc">{minfo["description"]}</div>'
                    f'<div class="mc-meta">{minfo["paper"]} \u00b7 \u00d7{minfo["scale"]} \u2192 {minfo["output_res_m"]}m GSD</div>'
                    '</div>', unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            st.table({"Metric":["PSNR","SSIM","Back-projection Error"],
                "Measures":["Pixel fidelity","Structural similarity","Physical consistency"],
                "Good Value":[">30 dB",">0.85","<0.01 RMSE"],
                "Notes":["Higher=better","Closer to 1.0=better","Lower=less hallucination"]})
    st.markdown('</div>', unsafe_allow_html=True)
