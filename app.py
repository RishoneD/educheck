import streamlit as st
import streamlit.components.v1 as components

from core.bank_notes_loader import load_bank_notes
from core.parser import parse_excel, parse_col_header
from core.subject_detector import detect_file_type, get_active_cols, subject_semesters
from core.student_builder import build_students
from core.validators import run_all_validations
from output.report_builder import render_by_teacher, render_by_student
from output.excel_export import build_excel_report

APP_VERSION = "0.2"
TYPE_LABELS = {'semester': 'תקופתי מחצית', 'annual': 'תקופתי שנתי'}

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title='Gradify', page_icon='📋', layout='wide')

# ── CSS injection via same-origin iframe ─────────────────────────────────────
# Streamlit 1.38+ strips <style> from st.markdown; components.html is same-origin
# so window.parent.document is accessible.
_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Heebo:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"], .stApp {
    direction: rtl !important;
    font-family: 'Heebo', sans-serif !important;
}
.stApp { background: #f4f6f3 !important; }
#MainMenu, footer { visibility: hidden; }

.block-container {
    max-width: 880px !important;
    padding: 24px 28px 80px !important;
    margin: 0 auto !important;
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

components.html(
    "<script>"
    "var s=window.parent.document.createElement('style');"
    "s.id='gradify-css';"
    "if(!window.parent.document.getElementById('gradify-css')){"
    "s.textContent=" + repr(_CSS) + ";"
    "window.parent.document.head.appendChild(s);"
    "}</script>",
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
    # Welcome
    st.markdown(
        '<h1 style="font-size:25px;font-weight:800;margin:0 0 6px;'
        'letter-spacing:-0.4px;color:#243029;">שלום, בואו נבדוק את התעודות 👋</h1>'
        '<p style="margin:0 0 24px;color:#6f7d74;font-size:15px;line-height:1.5;">'
        'העלו את קובץ הציונים של הכיתה ו-Gradify יאתר שגיאות חישוב והערות לא תקינות — לפני ההגשה.</p>',
        unsafe_allow_html=True,
    )

    # Step 1 — report type
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

    # Step 2 — upload
    _step_card(2, 'העלאת קובץ Excel')
    uploaded = st.file_uploader(
        label='קובץ Excel',
        type=['xlsx', 'xls'],
        label_visibility='collapsed',
    )
    st.markdown(
        '<div style="text-align:center;margin-top:10px;">'
        '<span style="color:#2563a8;font-weight:600;font-size:13px;'
        'text-decoration:underline;text-underline-offset:3px;">'
        'לא יודעים איך להפיק את הקובץ מהמערכת? כך עושים זאת ›'
        '</span></div>',
        unsafe_allow_html=True,
    )
    _card_end()

    if uploaded is None:
        return

    # Parse file
    file_bytes = uploaded.read()
    try:
        df, class_name = parse_excel(file_bytes)
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

    active_cols  = get_active_cols(df)
    num_students = df['שם התלמיד'].dropna().nunique()
    teachers     = {parse_col_header(c)[1] for c in active_cols}

    st.session_state.upload_cache = {
        'df': df, 'class_name': class_name, 'active_cols': active_cols,
        'num_students': num_students, 'num_subjects': len(active_cols),
        'num_teachers': len(teachers), 'detected': detected,
    }

    # Step 3 — confirmation
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
        f'<span style="font-weight:800;font-size:16px;color:#243029;">{class_name}</span>'
        f'<span style="width:1px;height:22px;background:#d4e4f1;"></span>'
        f'<span style="font-size:14.5px;color:#3a4742;"><b>{num_students}</b> תלמידים</span>'
        f'<span style="width:1px;height:22px;background:#d4e4f1;"></span>'
        f'<span style="font-size:14.5px;color:#3a4742;"><b>{len(active_cols)}</b> מקצועות</span>'
        f'<span style="width:1px;height:22px;background:#d4e4f1;"></span>'
        f'<span style="font-size:14.5px;color:#3a4742;"><b>{len(teachers)}</b> מורים</span>'
        f'</div>'
        f'<p style="margin:12px 2px 0;font-size:13px;color:#6f7d74;">'
        f'אם הזיהוי שגוי, העלה קובץ אחר בשלב 2.</p></div>',
        unsafe_allow_html=True,
    )

    # Run button
    if st.button('🔍 הרץ בדיקה', type='primary', use_container_width=True):
        cache = st.session_state.upload_cache
        with st.spinner('בודק את הציונים…'):
            students      = build_students(cache['df'], cache['active_cols'])
            col_semesters = {c: subject_semesters(cache['df'], c) for c in cache['active_cols']}
            findings      = run_all_validations(
                students, cache['active_cols'], col_semesters, cache['detected'], bank_rules
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

    # Header row
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
            st.download_button(
                label='⬇ הורד דוח Excel',
                data=st.session_state.excel_bytes,
                file_name=f'דוח_ציונים_{class_name}.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            )

    # 3 summary cards
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

    # Validity bar
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
