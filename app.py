import io
import streamlit as st

from core.bank_notes_loader import load_bank_notes
from core.parser import parse_excel
from core.subject_detector import detect_file_type, get_active_cols, subject_semesters
from core.student_builder import build_students
from core.validators import run_all_validations
from output.report_builder import render_summary, render_by_teacher, render_by_student
from output.excel_export import build_excel_report

# ─────────────────────────── הגדרות עמוד ───────────────────────────
st.set_page_config(
    page_title='EduCheck',
    page_icon='📋',
    layout='wide',
)

st.markdown("""
<style>
    body, .stApp { direction: rtl; text-align: right; }
    .stTextInput, .stSelectbox, .stRadio { direction: rtl; }
    [data-testid="metric-container"] { direction: rtl; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────── טעינת הערות בנק ───────────────────────────
@st.cache_data(show_spinner='טוען הגדרות הערות בנק...')
def _load_rules():
    return load_bank_notes('data/bank_notes.xlsx')

try:
    bank_rules = _load_rules()
except Exception as e:
    st.error(f'שגיאה בטעינת קובץ הערות בנק: {e}')
    st.stop()

# ─────────────────────────── כותרת ───────────────────────────
st.title('📋 EduCheck — בדיקת תקינות ציונים ותעודות')
st.caption(f'הערות בנק טעונות: {len(bank_rules)} קודים')

st.divider()

# ─────────────────────────── בחירת סוג תעודה ───────────────────────────
col_radio, col_upload = st.columns([1, 2])

with col_radio:
    st.subheader('סוג תעודה')
    file_type_choice = st.radio(
        label='בחר סוג:',
        options=['semester', 'annual'],
        format_func=lambda x: 'תקופתי מחצית' if x == 'semester' else 'תקופתי שנתי',
        horizontal=False,
    )
    TYPE_LABELS = {'semester': 'תקופתי מחצית', 'annual': 'תקופתי שנתי'}

with col_upload:
    st.subheader('העלאת קובץ')
    uploaded = st.file_uploader(
        label='בחר קובץ Excel של ציונים תקופתיים:',
        type=['xlsx', 'xls'],
        accept_multiple_files=False,
    )

st.divider()

if uploaded is None:
    st.info('אנא העלה קובץ Excel להתחלת הבדיקה.')
    st.stop()

# ─────────────────────────── קריאת הקובץ ───────────────────────────
file_bytes = uploaded.read()

try:
    df, class_name = parse_excel(file_bytes)
except Exception as e:
    st.error(f'שגיאה בקריאת הקובץ: {e}')
    st.stop()

# ─────────────────────────── זיהוי סוג הקובץ ───────────────────────────
detected = detect_file_type(df)

if detected is None:
    st.error('הקובץ אינו מוכר — לא ניתן לזהות סוג תעודה. אנא בדוק שהקובץ תקין.')
    st.stop()

if detected != file_type_choice:
    st.error(
        f'**אי-התאמה בסוג התעודה**  \n'
        f'בחרת: **{TYPE_LABELS[file_type_choice]}**  \n'
        f'הקובץ מזוהה כ: **{TYPE_LABELS[detected]}**  \n'
        f'אנא בחר את הסוג הנכון או העלה קובץ מתאים.'
    )
    st.stop()

# ─────────────────────────── זיהוי עמודות ───────────────────────────
active_cols = get_active_cols(df)
num_students = df['שם התלמיד'].dropna().nunique()

st.success(
    f'✅ זוהה: **{class_name}** — '
    f'{num_students} תלמידים | '
    f'{len(active_cols)} מקצועות פעילים | '
    f'סוג: {TYPE_LABELS[detected]}'
)

# ─────────────────────────── הרץ בדיקה ───────────────────────────
if st.button('▶ הרץ בדיקה', type='primary', use_container_width=False):

    with st.spinner('מנתח ציונים...'):
        # מבנה תלמידים
        students = build_students(df, active_cols)

        # מחציות פעילות לכל עמודה
        col_semesters = {col: subject_semesters(df, col) for col in active_cols}

        # בדיקות
        findings = run_all_validations(
            students, active_cols, col_semesters, file_type_choice, bank_rules
        )

    st.session_state['findings']   = findings
    st.session_state['class_name'] = class_name

# ─────────────────────────── הצגת תוצאות ───────────────────────────
if 'findings' in st.session_state:
    findings   = st.session_state['findings']
    class_name = st.session_state['class_name']

    st.divider()
    st.subheader(f'תוצאות הבדיקה — {class_name}')

    render_summary(findings)
    st.divider()

    tab_teacher, tab_student = st.tabs(['👩‍🏫 לפי מורה', '🎓 לפי תלמיד'])

    with tab_teacher:
        render_by_teacher(findings)

    with tab_student:
        render_by_student(findings)

    # ─── הורדת Excel ───
    st.divider()
    if findings:
        excel_bytes = build_excel_report(findings, class_name)
        st.download_button(
            label='📥 הורד דוח Excel',
            data=excel_bytes,
            file_name=f'דוח_ציונים_{class_name}.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            type='primary',
        )
    else:
        st.success('🎉 לא נמצאו שגיאות או אזהרות — הקובץ תקין לחלוטין!')
