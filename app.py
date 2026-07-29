import base64
import pathlib
import streamlit as st
import streamlit.components.v1 as components

from core.bank_notes_loader import load_bank_notes
from core.parser import (parse_tsv, detect_file_type,
                         get_active_subjects, build_students_tsv)
from core.validators import run_all_validations
from output.report_builder import render_by_teacher, render_by_student
from output.excel_export import build_excel_report

try:
    with open(pathlib.Path(__file__).parent / "version.txt") as _f:
        APP_VERSION = _f.read().strip()
except Exception:
    APP_VERSION = "1.0.0"
TYPE_LABELS = {'semester': 'תקופתי מחצית', 'annual': 'תקופתי שנתי'}

GUIDE_STEPS = [
    {
        'title': 'שלב 1: כנסו לעמוד של "הפקת תעודות/ימי הורים"',
        'image': 'data/guide/step1.png',
    },
    {
        'title': 'שלב 2: בחרו את הכיתה שלכם',
        'image': 'data/guide/step2.png',
    },
    {
        'title': "שלב 3: בחרו את התעודה הרצויה (מחצית א' או מחצית ב')",
        'image': 'data/guide/step3.png',
    },
    {
        'title': 'שלב 4: בסוג הקובץ, בחרו "מקור נתונים"',
        'image': 'data/guide/step4.png',
    },
    {
        'title': 'שלב 5: הפיקו דוח לכל הכיתה',
        'image': 'data/guide/step5.png',
    },
]

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title='Gradify', page_icon='📋', layout='wide')

_CSS = """
header[data-testid="stHeader"] { display: none !important; }
@import url('https://fonts.googleapis.com/css2?family=Heebo:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"], .stApp {
    direction: rtl !important;
    font-family: 'Heebo', sans-serif !important;
}
.stApp { background: #f4f6f3 !important; }
#MainMenu, footer { visibility: hidden; }

.block-container {
    max-width: 880px !important;
    padding: 56px 28px 80px !important;
    margin: 0 auto !important;
}

[data-testid="stMarkdownContainer"] * {
    text-align: right !important;
}

div[data-testid="stRadio"],
div[data-testid="stElementContainer"]:has(div[data-testid="stRadio"]) {
    width: 100% !important;
    max-width: 100% !important;
    flex-grow: 1 !important;
}
div[data-testid="stRadio"] > div:first-child {
    width: 100% !important;
}
div[data-testid="stRadio"] > div {
    display: grid !important;
    grid-template-columns: 1fr 1fr !important;
    gap: 12px !important;
}
div[data-testid="stRadio"] label {
    border: 2px solid #e3e8e2 !important;
    border-radius: 13px !important;
    padding: 15px 16px !important;
    background: #fff !important;
    cursor: pointer !important;
    margin: 0 !important;
    transition: border .15s, background .15s !important;
}
div[data-testid="stRadio"] label:has(input:checked) {
    border-color: #15876a !important;
    background: #f1f8f4 !important;
}

.stButton > button {
    width: 100% !important;
    font-family: 'Heebo', sans-serif !important;
    font-weight: 800 !important;
    font-size: 17px !important;
    background: #15876a !important;
    color: #fff !important;
    border: none !important;
    border-radius: 14px !important;
    padding: 17px !important;
    box-shadow: 0 4px 16px rgba(21,135,106,.32) !important;
}
.stButton > button:hover { background: #0f6b54 !important; }

.stDownloadButton > button {
    font-family: 'Heebo', sans-serif !important;
    font-weight: 700 !important;
    font-size: 14.5px !important;
    background: #15876a !important;
    color: #fff !important;
    border: none !important;
    border-radius: 11px !important;
    padding: 12px 18px !important;
    box-shadow: 0 2px 10px rgba(21,135,106,.3) !important;
    width: auto !important;
}
.stDownloadButton > button:hover { background: #0f6b54 !important; }

.stTabs [data-baseweb="tab-list"] {
    background: #eef1ee !important;
    padding: 5px !important;
    border-radius: 12px !important;
    gap: 6px !important;
    width: fit-content !important;
}
.stTabs [data-baseweb="tab"] {
    font-family: 'Heebo', sans-serif !important;
    font-weight: 700 !important;
    font-size: 14px !important;
    border-radius: 9px !important;
    background: transparent !important;
    color: #6f7d74 !important;
    padding: 9px 20px !important;
}
.stTabs [aria-selected="true"] {
    background: #fff !important;
    color: #15876a !important;
    box-shadow: 0 1px 4px rgba(0,0,0,.08) !important;
}
.stTabs [data-baseweb="tab-highlight"],
.stTabs [data-baseweb="tab-border"] { display: none !important; }

[data-testid="stFileUploaderDropzone"] {
    border: 2px dashed #cdd8d0 !important;
    background: #f8faf8 !important;
    border-radius: 13px !important;
}
[data-testid="stFileUploaderDropzone"]:hover {
    border-color: #15876a !important;
    background: #f1f8f4 !important;
}

.btn-secondary > button {
    background: #fff !important;
    color: #6f7d74 !important;
    border: 1px solid #e3e8e2 !important;
    font-weight: 600 !important;
    font-size: 13.5px !important;
    padding: 8px 14px !important;
    border-radius: 9px !important;
    box-shadow: none !important;
    width: auto !important;
}
.btn-secondary > button:hover {
    background: #f4f6f3 !important;
    color: #243029 !important;
}

"""

def _build_guide_overlay() -> str:
    """בונה HTML מלא של overlay מדריך עם תמונות base64 ו-JS ניווט."""
    steps_html = ''
    for idx, step in enumerate(GUIDE_STEPS):
        img_path = pathlib.Path(step['image'])
        b64 = base64.b64encode(img_path.read_bytes()).decode() if img_path.exists() else ''
        img_tag = (
            f'<img src="data:image/png;base64,{b64}" style="max-width:100%;max-height:100%;object-fit:contain;" />'
            if b64 else '<span style="color:#9aa69e;">תמונה לא נמצאה</span>'
        )
        display = 'flex' if idx == 0 else 'none'
        steps_html += (
            f'<div class="gd-step" id="gd-step-{idx}" '
            f'style="display:{display};flex-direction:column;gap:14px;">'
            f'<div style="font-size:16px;font-weight:800;color:#243029;direction:rtl;'
            f'padding:10px 14px;background:#f0f6fb;border-right:4px solid #15876a;'
            f'border-radius:0 8px 8px 0;">{step["title"]}</div>'
            f'<div style="width:100%;height:340px;display:flex;align-items:center;'
            f'justify-content:center;background:#f8faf8;border:1px solid #e3e8e2;'
            f'border-radius:10px;overflow:hidden;">{img_tag}</div>'
            f'</div>'
        )

    total = len(GUIDE_STEPS)
    nav_btn = (
        'background:#fff;border:1px solid #e3e8e2;border-radius:9px;'
        'padding:8px 22px;font-size:20px;cursor:pointer;font-family:Heebo,sans-serif;'
        'color:#243029;line-height:1;'
    )
    overlay_html = (
        f'<div id="gradify-guide-overlay" style="display:none;position:fixed;top:0;left:0;'
        f'width:100%;height:100%;background:rgba(0,0,0,0.55);z-index:99999;'
        f'align-items:center;justify-content:center;">'
        f'  <div style="background:#fff;width:92vw;max-height:92vh;border-radius:14px;'
        f'display:flex;flex-direction:column;overflow:hidden;box-shadow:0 8px 40px rgba(0,0,0,.2);">'
        f'    <div style="padding:16px 20px;border-bottom:1px solid #e3e8e2;display:flex;'
        f'align-items:center;justify-content:space-between;direction:rtl;flex-shrink:0;">'
        f'      <span style="font-weight:800;font-size:17px;font-family:Heebo,sans-serif;color:#243029;">'
        f'📖 מדריך — כיצד להפיק קובץ ממאשב</span>'
        f'      <button onclick="gradifyGuideClose()" style="background:none;border:none;'
        f'cursor:pointer;font-size:22px;color:#6f7d74;line-height:1;padding:2px 6px;">✕</button>'
        f'    </div>'
        f'    <div style="flex:1;overflow-y:auto;padding:20px 24px;">{steps_html}</div>'
        f'    <div style="padding:14px 20px;border-top:1px solid #e3e8e2;display:flex;'
        f'align-items:center;justify-content:center;gap:24px;flex-shrink:0;">'
        f'      <button id="gd-btn-prev" onclick="gradifyGuideNav(-1)" style="{nav_btn}">→</button>'
        f'      <span id="gd-indicator" style="font-size:13px;color:#6f7d74;font-weight:600;'
        f'font-family:Heebo,sans-serif;">{total} / 1</span>'
        f'      <button id="gd-btn-next" onclick="gradifyGuideNav(1)" style="{nav_btn}">←</button>'
        f'    </div>'
        f'  </div>'
        f'</div>'
    )
    return overlay_html


_GUIDE_OVERLAY_HTML = _build_guide_overlay()
_TOTAL_STEPS = len(GUIDE_STEPS)

components.html(
    "<script>"
    # ── CSS ──
    "var s=window.parent.document.getElementById('gradify-css')"
    "||window.parent.document.createElement('style');"
    "s.id='gradify-css';"
    "s.textContent=" + repr(_CSS) + ";"
    "if(!s.parentElement)window.parent.document.head.appendChild(s);"
    # ── Guide link button styling ──
    "if(!window.parent.document.getElementById('gradify-guide-link-css')){"
    "  var ls=window.parent.document.createElement('style');"
    "  ls.id='gradify-guide-link-css';"
    "  ls.textContent='button.gradify-guide-link{background:none!important;border:none!important;"
    "box-shadow:none!important;padding:0!important;width:auto!important;color:#2563a8!important;"
    "font-weight:600!important;font-size:13px!important;text-decoration:underline!important;"
    "text-underline-offset:3px!important;cursor:pointer!important;}"
    "button.gradify-guide-link:hover{background:none!important;color:#1a4a8a!important;}"
    "[data-testid=\"stButton\"]:has(button.gradify-guide-link){text-align:center!important;}';"
    "  window.parent.document.head.appendChild(ls);"
    "}"
    # ── Guide overlay HTML (inject once) ──
    "if(!window.parent.document.getElementById('gradify-guide-overlay')){"
    "  var tmp=window.parent.document.createElement('div');"
    "  tmp.innerHTML=" + repr(_GUIDE_OVERLAY_HTML) + ";"
    "  window.parent.document.body.appendChild(tmp.firstElementChild);"
    "}"
    # ── Guide JS functions on parent ──
    "if(!window.parent.gradifyGuideOpen){"
    "  window.parent.gradifyGuideStep=0;"
    "  window.parent.gradifyGuideTotal=" + str(_TOTAL_STEPS) + ";"
    "  window.parent.gradifyGuideOpen=function(){"
    "    var t=window.parent.gradifyGuideTotal;"
    "    window.parent.gradifyGuideStep=0;"
    "    window.parent.document.querySelectorAll('.gd-step').forEach(function(el,i){"
    "      el.style.display=i===0?'flex':'none';"
    "    });"
    "    window.parent.document.getElementById('gd-indicator').textContent=t+' / 1';"
    "    window.parent.document.getElementById('gd-btn-prev').style.visibility='hidden';"
    "    window.parent.document.getElementById('gd-btn-next').style.visibility=t>1?'visible':'hidden';"
    "    window.parent.document.getElementById('gradify-guide-overlay').style.display='flex';"
    "  };"
    "  window.parent.gradifyGuideClose=function(){"
    "    window.parent.document.getElementById('gradify-guide-overlay').style.display='none';"
    "  };"
    "  window.parent.gradifyGuideNav=function(dir){"
    "    var step=window.parent.gradifyGuideStep;"
    "    var t=window.parent.gradifyGuideTotal;"
    "    var next=Math.max(0,Math.min(t-1,step+dir));"
    "    if(next===step)return;"
    "    window.parent.document.getElementById('gd-step-'+step).style.display='none';"
    "    window.parent.document.getElementById('gd-step-'+next).style.display='flex';"
    "    window.parent.gradifyGuideStep=next;"
    "    window.parent.document.getElementById('gd-indicator').textContent=t+' / '+(next+1);"
    "    window.parent.document.getElementById('gd-btn-prev').style.visibility=next>0?'visible':'hidden';"
    "    window.parent.document.getElementById('gd-btn-next').style.visibility=next<t-1?'visible':'hidden';"
    "  };"
    # expose to iframe scope too (onclick handlers use window scope)
    "  window.gradifyGuideClose=window.parent.gradifyGuideClose;"
    "  window.gradifyGuideNav=window.parent.gradifyGuideNav;"
    "}"
    # ── Wire guide link button ──
    "function wireGuideBtn(){"
    "  window.parent.document.querySelectorAll('button').forEach(function(b){"
    "    if(b.textContent.trim().startsWith('לא יודעים')){"
    "      b.classList.add('gradify-guide-link');"
    "      if(!b.dataset.guideWired){"
    "        b.dataset.guideWired='1';"
    "        b.addEventListener('click',function(e){"
    "          e.preventDefault();e.stopPropagation();"
    "          window.parent.gradifyGuideOpen();"
    "        },true);"  # capture phase — fires before Streamlit handler
    "      }"
    "    }"
    "  });"
    "}"
    "var obs=new MutationObserver(wireGuideBtn);"
    "obs.observe(window.parent.document.body,{childList:true,subtree:true});"
    "wireGuideBtn();"
    "</script>",
    height=0,
    scrolling=False,
)

# ── Bank rules ────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def _load_rules():
    return load_bank_notes('data/bank_notes.xlsx')

try:
    bank_rules = _load_rules()
except Exception as e:
    st.error(f'שגיאה בטעינת קובץ הערות בנק: {e}')
    st.stop()

# ── Session state ─────────────────────────────────────────────────────────────
for _k, _v in {
    'screen': 'setup',
    'report_type': 'semester',
    'findings': None,
    'class_name': '',
    'num_teachers': 0,
    'excel_bytes': None,
    'upload_cache': None,
}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v




# ── Header ────────────────────────────────────────────────────────────────────
def _header():
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:12px;padding:14px 0 18px;">'
        f'<div style="width:38px;height:38px;border-radius:11px;background:#15876a;'
        f'display:flex;align-items:center;justify-content:center;color:#fff;font-weight:800;'
        f'font-size:20px;box-shadow:0 2px 8px rgba(21,135,106,.28);flex-shrink:0;">G</div>'
        f'<div style="line-height:1.15;">'
        f'<div style="display:flex;align-items:center;gap:7px;">'
        f'<span style="font-weight:800;font-size:19px;letter-spacing:-0.2px;color:#243029;">Gradify</span>'
        f'<span dir="ltr" style="font-size:10.5px;font-weight:600;color:#6f7d74;background:#f0f2ef;'
        f'border:1px solid #e3e8e2;padding:1px 6px;border-radius:6px;">v{APP_VERSION}</span>'
        f'</div>'
        f'<div style="font-size:12.5px;color:#6f7d74;font-weight:500;">בדיקת תקינות ציונים תקופתיים</div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )
    st.divider()


# ── HTML helpers ──────────────────────────────────────────────────────────────
def _step_card(step: int, title: str):
    st.markdown(
        f'<div style="background:#fff;border:1px solid #e3e8e2;border-radius:16px;'
        f'padding:22px 24px;margin-bottom:16px;">'
        f'<div style="display:flex;align-items:center;gap:11px;margin-bottom:16px;">'
        f'<span style="width:27px;height:27px;border-radius:50%;background:#15876a;color:#fff;'
        f'font-weight:700;font-size:14px;display:inline-flex;align-items:center;'
        f'justify-content:center;flex-shrink:0;">{step}</span>'
        f'<span style="font-size:16.5px;font-weight:700;color:#243029;">{title}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _card_end():
    st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SETUP SCREEN
# ─────────────────────────────────────────────────────────────────────────────
def _screen_setup():
    st.markdown(
        '<h1 style="font-size:25px;font-weight:800;margin:0 0 6px;'
        'letter-spacing:-0.4px;color:#243029;">שלום, בואו נבדוק את התעודות 👋</h1>'
        '<p style="margin:0 0 24px;color:#6f7d74;font-size:15px;line-height:1.5;">'
        'העלו את קובץ הציונים של הכיתה ו-Gradify יאתר שגיאות חישוב והערות לא תקינות.</p>',
        unsafe_allow_html=True,
    )

    _step_card(1, 'איזה סוג דוח אתם בודקים?')
    st.radio(
        label='סוג',
        options=['semester', 'annual'],
        format_func=lambda x: 'תקופתי מחצית\n\nתעודת מחצית א׳' if x == 'semester'
                              else 'תקופתי שנתי\n\nתעודה שנתית מסכמת',
        label_visibility='collapsed',
        horizontal=True,
        key='report_type',
    )
    _card_end()

    _step_card(2, 'העלאת קובץ מקור נתונים')
    uploaded = st.file_uploader(
        label='קובץ TSV',
        type=['txt', 'tsv', 'csv'],
        label_visibility='collapsed',
    )
    st.button('לא יודעים איך להפיק את הקובץ מהמערכת? כך עושים זאת ›', key='guide_link_btn')
    _card_end()

    if uploaded is None:
        return

    file_bytes = uploaded.read()
    try:
        df, class_name = parse_tsv(file_bytes)
    except Exception as e:
        st.error(f'שגיאה בקריאת הקובץ: {e}')
        return

    detected = detect_file_type(df)
    if detected is None:
        st.error('הקובץ אינו מוכר — לא ניתן לזהות סוג תעודה.')
        return

    if detected != st.session_state.report_type:
        st.error(
            f'אי-התאמה בסוג התעודה — בחרת **{TYPE_LABELS[st.session_state.report_type]}** '
            f'אך הקובץ מזוהה כ-**{TYPE_LABELS[detected]}**.'
        )
        return

    subjects     = get_active_subjects(df)
    num_students = df['שם_תלמיד'].dropna().nunique() if 'שם_תלמיד' in df.columns else 0
    teachers     = {s['teacher'] for s in subjects}

    st.session_state.upload_cache = {
        'df': df, 'class_name': class_name, 'subjects': subjects,
        'num_students': num_students, 'num_subjects': len(subjects),
        'num_teachers': len(teachers), 'detected': detected,
    }

    st.markdown(
        f'<div style="background:#fff;border:1px solid #e3e8e2;border-radius:16px;'
        f'padding:22px 24px;margin-bottom:22px;">'
        f'<div style="display:flex;align-items:center;gap:11px;margin-bottom:16px;">'
        f'<span style="width:27px;height:27px;border-radius:50%;background:#15876a;color:#fff;'
        f'font-weight:700;font-size:14px;display:inline-flex;align-items:center;'
        f'justify-content:center;">3</span>'
        f'<span style="font-size:16.5px;font-weight:700;color:#243029;">זיהינו את הקובץ — נכון?</span>'
        f'</div>'
        f'<div style="background:#f0f6fb;border:1px solid #d4e4f1;border-radius:12px;'
        f'padding:16px 18px;display:flex;align-items:center;gap:16px;flex-wrap:wrap;">'
        f'<span style="font-size:18px;">🏫</span>'
        f'<span style="font-weight:800;font-size:16px;color:#243029;">כיתה {class_name}</span>'
        f'<span style="width:1px;height:22px;background:#d4e4f1;"></span>'
        f'<span style="font-size:14.5px;color:#3a4742;"><b>{num_students}</b> תלמידים</span>'
        f'</div>'
        f'<p style="margin:12px 2px 0;font-size:13px;color:#6f7d74;">'
        f'אם הזיהוי שגוי, העלה קובץ אחר בשלב 2.</p></div>',
        unsafe_allow_html=True,
    )

    if st.button('🔍 הרץ בדיקה', type='primary', use_container_width=True):
        cache = st.session_state.upload_cache
        with st.spinner('בודק את הציונים…'):
            students, col_semesters = build_students_tsv(
                cache['df'], cache['subjects'], cache['detected'], bank_rules
            )
            findings = run_all_validations(
                students, [], col_semesters, cache['detected'], bank_rules
            )
            excel_bytes = build_excel_report(findings, cache['class_name'])

        st.session_state.findings     = findings
        st.session_state.class_name   = cache['class_name']
        st.session_state.num_teachers = cache['num_teachers']
        st.session_state.excel_bytes  = excel_bytes
        st.session_state.upload_cache = {**cache}
        st.session_state.screen       = 'results'
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# RESULTS SCREEN
# ─────────────────────────────────────────────────────────────────────────────
def _screen_results():
    findings       = st.session_state.findings or []
    class_name     = st.session_state.class_name
    total_teachers = st.session_state.num_teachers

    errors            = sum(1 for f in findings if f['severity'] == '❌')
    warnings          = sum(1 for f in findings if f['severity'] == '⚠️')
    teachers_involved = len({f['teacher'] for f in findings})

    cache       = st.session_state.get('upload_cache') or {}
    total_cells = (cache.get('num_students', 1) or 1) * (cache.get('num_subjects', 1) or 1)
    pct         = max(0, min(100, int((1 - (errors + warnings) / max(errors + warnings, total_cells)) * 100)))

    col_title, col_dl = st.columns([3, 1])
    with col_title:
        subtitle = 'נמצאו נושאים שדורשים את תשומת לבכם' if findings else 'הכל תקין ✅'
        st.markdown(
            f'<div style="margin-bottom:20px;">'
            f'<div style="font-size:13px;color:#6f7d74;font-weight:600;margin-bottom:5px;">'
            f'תוצאות בדיקה · {class_name}</div>'
            f'<h1 style="font-size:24px;font-weight:800;margin:0;letter-spacing:-0.4px;'
            f'color:#243029;">{subtitle}</h1></div>',
            unsafe_allow_html=True,
        )
    with col_dl:
        if findings and st.session_state.excel_bytes:
            if st.button('⬇ שמור דוח Excel'):
                import tkinter as tk
                from tkinter import filedialog
                root = tk.Tk()
                root.withdraw()
                root.attributes('-topmost', True)
                safe_name = class_name.replace('"', '').replace("'", '')
                path = filedialog.asksaveasfilename(
                    title='שמור דוח Excel',
                    initialfile=f'דוח_ציונים_{safe_name}.xlsx',
                    defaultextension='.xlsx',
                    filetypes=[('Excel', '*.xlsx')],
                )
                root.destroy()
                if path:
                    pathlib.Path(path).write_bytes(st.session_state.excel_bytes)
                    st.success(f'נשמר: {path}')

    st.markdown(
        f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:13px;margin-bottom:14px;">'
        f'<div style="background:#fcebeb;border:1px solid #f3c9c9;border-radius:14px;padding:18px 20px;">'
        f'<div style="color:#b53535;font-weight:600;font-size:13.5px;">❌ שגיאות</div>'
        f'<div style="font-size:34px;font-weight:800;color:#c0392b;margin-top:4px;line-height:1;">{errors}</div>'
        f'<div style="font-size:12.5px;color:#9a5b5b;margin-top:6px;">חובה לתקן לפני הגשה</div></div>'
        f'<div style="background:#fdf4e0;border:1px solid #f0dcae;border-radius:14px;padding:18px 20px;">'
        f'<div style="color:#9a7212;font-weight:600;font-size:13.5px;">⚠️ אזהרות</div>'
        f'<div style="font-size:34px;font-weight:800;color:#b9831a;margin-top:4px;line-height:1;">{warnings}</div>'
        f'<div style="font-size:12.5px;color:#8a7236;margin-top:6px;">מומלץ לבדוק ידנית</div></div>'
        f'<div style="background:#e9f6ed;border:1px solid #c4e6cf;border-radius:14px;padding:18px 20px;">'
        f'<div style="color:#1f7a44;font-weight:600;font-size:13.5px;">👥 מורים מעורבים</div>'
        f'<div style="font-size:34px;font-weight:800;color:#2f9e57;margin-top:4px;line-height:1;">{teachers_involved}</div>'
        f'<div style="font-size:12.5px;color:#4d7d61;margin-top:6px;">מתוך {total_teachers} מורים בכיתה</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div style="background:#fff;border:1px solid #e3e8e2;border-radius:14px;'
        f'padding:15px 20px;margin-bottom:22px;display:flex;align-items:center;gap:16px;">'
        f'<div style="font-weight:700;font-size:14px;white-space:nowrap;color:#243029;">תקינות כללית</div>'
        f'<div style="flex:1;height:11px;background:#eef1ee;border-radius:99px;overflow:hidden;">'
        f'<div style="width:{pct}%;height:100%;background:#2f9e57;border-radius:99px;"></div></div>'
        f'<div style="font-weight:800;font-size:15px;color:#2f9e57;white-space:nowrap;" dir="ltr">'
        f'{pct}% תקין</div></div>',
        unsafe_allow_html=True,
    )

    if not findings:
        return

    tab_teacher, tab_student = st.tabs(['👩‍🏫 לפי מורה', '🎓 לפי תלמיד'])
    with tab_teacher:
        render_by_teacher(findings)
    with tab_student:
        render_by_student(findings)

    st.markdown(
        '<div style="margin-top:24px;display:flex;align-items:center;gap:12px;'
        'background:#f0f6fb;border:1px solid #d4e4f1;border-radius:14px;padding:18px 22px;">'
        '<span style="font-size:22px;">💡</span>'
        '<div style="font-size:14px;line-height:1.5;color:#3a4742;">'
        'הדוח כולל את כל השגיאות מסודרות לפי מורה ותלמיד — נוח להעברה לצוות.</div></div>',
        unsafe_allow_html=True,
    )


# ── Footer ────────────────────────────────────────────────────────────────────
def _footer():
    st.markdown(
        f'<div style="margin-top:40px;text-align:center;color:#9aa69e;font-size:12.5px;padding-bottom:24px;">'
        f'Gradify · בדיקת תקינות ציונים'
        f'<span style="margin:0 6px;">·</span>'
        f'<span dir="ltr">גרסה {APP_VERSION}</span></div>',
        unsafe_allow_html=True,
    )


# ── Main ──────────────────────────────────────────────────────────────────────
_header()

if st.session_state.screen == 'results':
    st.markdown('<div class="btn-secondary">', unsafe_allow_html=True)
    if st.button('← בדיקה חדשה', key='new_check'):
        st.session_state.screen = 'setup'
        st.session_state.findings = None
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    _screen_results()
else:
    _screen_setup()

_footer()
