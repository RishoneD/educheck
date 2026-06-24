import streamlit as st
from collections import defaultdict


def _count_label(findings: list[dict]) -> str:
    errors   = sum(1 for f in findings if f['severity'] == '❌')
    warnings = sum(1 for f in findings if f['severity'] == '⚠️')
    parts = []
    if errors:
        parts.append(f'❌ {errors} שגיאות')
    if warnings:
        parts.append(f'⚠️ {warnings} אזהרות')
    return ' · '.join(parts) if parts else '✅ תקין'


def _finding_row(f: dict) -> str:
    sev = f['severity']
    if sev == '❌':
        bg, border, text_color = '#fcebeb', '#f3c9c9', '#9a5b5b'
    else:
        bg, border, text_color = '#fdf4e0', '#f0dcae', '#8a7236'

    det = f.get('details', '')
    det_html = (
        f'<br><span style="font-size:12px; color:#9aa69e; font-family:monospace; direction:ltr; display:inline-block;">{det}</span>'
        if det else ''
    )
    return f"""
    <div style="display:flex; align-items:flex-start; gap:11px; background:{bg}; border:1px solid {border};
                border-radius:10px; padding:11px 14px; margin:5px 0; direction:rtl;">
      <span style="font-size:15px; line-height:1.4; flex-shrink:0;">{sev}</span>
      <div style="line-height:1.5;">
        <span style="font-weight:700; font-size:14px; color:#243029;">{f['student']}</span>
        <span style="font-size:14px; color:{text_color};"> — {f['message']}</span>
        {det_html}
      </div>
    </div>"""


def render_by_teacher(findings: list[dict]) -> None:
    if not findings:
        st.success('לא נמצאו ממצאים — הכל תקין ✅')
        return

    by_teacher: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for f in findings:
        by_teacher[f['teacher']][f['subject']].append(f)

    for teacher, subjects in sorted(by_teacher.items()):
        teacher_findings = [f for items in subjects.values() for f in items]
        label = f"{teacher}  —  {_count_label(teacher_findings)}"
        with st.expander(label, expanded=False):
            for subject, items in sorted(subjects.items()):
                st.markdown(f"""
                <div style="font-weight:700; font-size:13.5px; color:#3a4742; margin:12px 0 8px 2px;
                            display:flex; align-items:center; gap:7px;">
                  <span style="width:5px; height:5px; border-radius:50%; background:#15876a; display:inline-block; flex-shrink:0;"></span>
                  {subject}
                </div>
                {''.join(_finding_row(f) for f in items)}
                """, unsafe_allow_html=True)


def render_by_student(findings: list[dict]) -> None:
    if not findings:
        st.success('לא נמצאו ממצאים — הכל תקין ✅')
        return

    by_student: dict[str, list] = defaultdict(list)
    for f in findings:
        by_student[f['student']].append(f)

    for student, items in sorted(by_student.items()):
        label = f"{student}  —  {_count_label(items)}"
        with st.expander(label, expanded=False):
            by_subject: dict[str, list] = defaultdict(list)
            for f in items:
                by_subject[f['subject']].append(f)
            for subject, subj_items in sorted(by_subject.items()):
                teacher = subj_items[0]['teacher']
                st.markdown(f"""
                <div style="font-weight:700; font-size:13.5px; color:#3a4742; margin:12px 0 8px 2px;
                            display:flex; align-items:center; gap:7px;">
                  <span style="width:5px; height:5px; border-radius:50%; background:#15876a; display:inline-block; flex-shrink:0;"></span>
                  {subject}
                  <span style="font-weight:400; color:#9aa69e; font-size:12.5px;">({teacher})</span>
                </div>
                {''.join(_finding_row(f) for f in subj_items)}
                """, unsafe_allow_html=True)
