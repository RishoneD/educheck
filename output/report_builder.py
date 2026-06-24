import streamlit as st
from collections import defaultdict


def _severity_color(severity: str) -> str:
    return '#ff4b4b' if severity == '❌' else '#ffa500'


def _count_label(findings: list[dict]) -> str:
    errors   = sum(1 for f in findings if f['severity'] == '❌')
    warnings = sum(1 for f in findings if f['severity'] == '⚠️')
    parts = []
    if errors:
        parts.append(f'{errors} שגיאות')
    if warnings:
        parts.append(f'{warnings} אזהרות')
    return ' | '.join(parts) if parts else 'תקין ✅'


def render_summary(findings: list[dict]) -> None:
    """מציג שורת סיכום עליונה."""
    errors   = sum(1 for f in findings if f['severity'] == '❌')
    warnings = sum(1 for f in findings if f['severity'] == '⚠️')
    teachers = len({f['teacher'] for f in findings})

    col1, col2, col3 = st.columns(3)
    col1.metric('שגיאות ❌', errors)
    col2.metric('אזהרות ⚠️', warnings)
    col3.metric('מורים עם ממצאים', teachers)


def render_by_teacher(findings: list[dict]) -> None:
    """מציג ממצאים מקובצים לפי מורה ← מקצוע ← תלמיד."""
    if not findings:
        st.success('לא נמצאו ממצאים — הכל תקין ✅')
        return

    by_teacher: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for f in findings:
        by_teacher[f['teacher']][f['subject']].append(f)

    for teacher, subjects in sorted(by_teacher.items()):
        teacher_findings = [f for subj_list in subjects.values() for f in subj_list]
        label = f"{teacher} — {_count_label(teacher_findings)}"
        with st.expander(label, expanded=False):
            for subject, items in sorted(subjects.items()):
                st.markdown(f"**📚 {subject}**")
                for f in items:
                    _render_finding_row(f)
                st.markdown('---')


def render_by_student(findings: list[dict]) -> None:
    """מציג ממצאים מקובצים לפי תלמיד ← מקצוע."""
    if not findings:
        st.success('לא נמצאו ממצאים — הכל תקין ✅')
        return

    by_student: dict[str, list] = defaultdict(list)
    for f in findings:
        by_student[f['student']].append(f)

    for student, items in sorted(by_student.items()):
        label = f"{student} — {_count_label(items)}"
        with st.expander(label, expanded=False):
            # קיבוץ לפי מקצוע בתוך התלמיד
            by_subject: dict[str, list] = defaultdict(list)
            for f in items:
                by_subject[f['subject']].append(f)
            for subject, subj_items in sorted(by_subject.items()):
                st.markdown(f"**📚 {subject}** ({subj_items[0]['teacher']})")
                for f in subj_items:
                    _render_finding_row(f)
            st.markdown('---')


def _render_finding_row(f: dict) -> None:
    sev   = f['severity']
    color = _severity_color(sev)
    msg   = f['message']
    det   = f['details']
    line  = f"{sev} **{f['student']}** — {msg}"
    if det:
        line += f"  \n&nbsp;&nbsp;&nbsp;&nbsp;`{det}`"
    st.markdown(
        f'<div style="border-left: 3px solid {color}; '
        f'padding: 4px 8px; margin: 4px 0; direction: rtl;">{line}</div>',
        unsafe_allow_html=True,
    )
