"""
diagnose.py — סקריפט אבחון לנתונים גולמיים מתוך קובץ TSV

שימוש:
    python diagnose.py <קובץ.tsv>

פולט:
    diagnose_<שם_קובץ>.csv  — טבלה עם כל תא תלמיד/מקצוע
    diagnose_<שם_קובץ>_subjects.csv — טבלה עם מקצועות שזוהו
"""

import sys
import csv
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from core.parser import parse_tsv, detect_file_type, get_active_subjects, build_students_tsv
from core.parser import extract_bank_code
from core.bank_notes_loader import load_bank_notes


def main():
    if len(sys.argv) < 2:
        print("שימוש: python diagnose.py <קובץ.tsv>")
        sys.exit(1)

    tsv_path = pathlib.Path(sys.argv[1])
    if not tsv_path.exists():
        print(f"קובץ לא נמצא: {tsv_path}")
        sys.exit(1)

    file_bytes = tsv_path.read_bytes()
    bank_rules = load_bank_notes(str(pathlib.Path(__file__).parent / 'data' / 'bank_notes.xlsx'))

    df, class_name = parse_tsv(file_bytes)
    file_type = detect_file_type(df)
    subjects = get_active_subjects(df)
    students, col_semesters = build_students_tsv(df, subjects, file_type, bank_rules)
    # col_semesters is now student-derived; subjects list is for display only

    print(f"\n=== קובץ: {tsv_path.name} ===")
    print(f"כיתה: {class_name}")
    print(f"סוג תעודה: {file_type}")
    print(f"מקצועות שזוהו: {len(subjects)}")
    print(f"תלמידים שזוהו: {len(students)}")

    # ── טבלת מקצועות ─────────────────────────────────────────────────────────
    subjects_out = tsv_path.parent / f"diagnose_{tsv_path.stem}_subjects.csv"
    with open(subjects_out, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['אינדקס', 'מקצוע', 'מורה', 'יש_א', 'יש_ב', 'col_key'])
        for s in subjects:
            has_a, has_b = col_semesters.get(s['col_key'], (False, False))
            w.writerow([s['index'], s['name'], s['teacher'],
                        'כן' if has_a else 'לא',
                        'כן' if has_b else 'לא',
                        s['col_key']])
    print(f"\nטבלת מקצועות נשמרה: {subjects_out}")

    # ── טבלת תלמידים/מקצועות ─────────────────────────────────────────────────
    rows_out = tsv_path.parent / f"diagnose_{tsv_path.stem}_students.csv"
    with open(rows_out, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        header = ['תלמיד', 'מקצוע', 'מורה', 'יש_א', 'יש_ב',
                  'ציון_א', 'ציון_ב', 'שנתי', 'הערת_בנק_טקסט', 'קוד_בנק']
        w.writerow(header)

        for student, subjs in sorted(students.items()):
            for col_key, data in subjs.items():
                # חלץ שם מקצוע ומורה מ-col_key
                parts = col_key.split('  ')
                subj_name = parts[0] if parts else col_key
                teacher = parts[1] if len(parts) > 1 else ''

                has_a, has_b = col_semesters.get(col_key, (False, False))
                bank_text = data.get('bank') or ''
                bank_code = extract_bank_code(bank_text) if bank_text else ''

                w.writerow([
                    student,
                    subj_name,
                    teacher,
                    'כן' if has_a else 'לא',
                    'כן' if has_b else 'לא',
                    data.get('sem_a', ''),
                    data.get('sem_b', ''),
                    data.get('annual', ''),
                    bank_text,
                    bank_code,
                ])

    print(f"טבלת תלמידים נשמרה:  {rows_out}")
    print("\nפתח את קבצי ה-CSV ב-Excel וסנן לפי מורה/מקצוע לאבחון.")


if __name__ == '__main__':
    main()
