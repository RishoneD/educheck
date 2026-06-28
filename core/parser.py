import re
import io
import pandas as pd


FIXED_COLS_COUNT = 10  # נשמר לתאימות עם subject_detector.py


def parse_col_header(col: str) -> tuple[str, str, str]:
    """מפרסר col_key לפי רווחים כפולים → (subject, teacher, code_str).
    נשמר כי validators.py מייבא אותו."""
    parts = re.split(r'\s{2,}', str(col).strip())
    subject = parts[0] if parts else str(col)
    teacher = parts[1] if len(parts) > 1 else 'לא ידוע'
    code    = parts[2].strip('[]') if len(parts) > 2 else ''
    return subject, teacher, code


def extract_bank_code(text) -> int | None:
    """מחלץ קוד מספרי מהערת בנק כגון: 'בקיא [קוד: 63]'."""
    m = re.search(r'\[קוד:\s*(\d+)\]', str(text))
    return int(m.group(1)) if m else None


# ── TSV (מאשב) ────────────────────────────────────────────────────────────────

def parse_tsv(file_bytes: bytes) -> tuple[pd.DataFrame, str]:
    """קורא קובץ TSV ממאשב ומחזיר (DataFrame, שם כיתה)."""
    df = pd.read_csv(io.BytesIO(file_bytes), sep='\t', encoding='utf-8-sig', dtype=str)
    df = df.dropna(how='all').reset_index(drop=True)

    class_name = 'לא ידוע'
    for col_candidate in ('כיתה', 'שכבה', 'כיתה_שם'):
        if col_candidate in df.columns and df[col_candidate].notna().any():
            val = str(df[col_candidate].dropna().iloc[0]).strip()
            if val and val not in ('nan', ''):
                class_name = val
                break

    return df, class_name


def detect_file_type(df: pd.DataFrame) -> str | None:
    """מזהה סוג הקובץ לפי עמודות TSV ממאשב."""
    has_b      = 'ב_תקופה_שם' in df.columns and df['ב_תקופה_שם'].notna().any()
    has_annual = 'ג_תקופה_שם' in df.columns and df['ג_תקופה_שם'].notna().any()

    if has_b and has_annual:
        return 'annual'
    if not has_b:
        return 'semester'
    return None


def get_active_subjects(df: pd.DataFrame) -> list[dict]:
    """מחזיר רשימת מקצועות פעילים: [{index, name, teacher, col_key}].

    col_key מפורמט כ-'שם  מורה  [i]' כך ש-parse_col_header יחלץ אותו נכון.
    """
    subjects = []
    i = 1
    while True:
        subj_col = f'מקצוע{i}'
        if subj_col not in df.columns:
            break
        if df[subj_col].notna().any():
            name    = str(df[subj_col].dropna().iloc[0]).strip()
            teacher = ''
            tcol    = f'מורה{i}'
            if tcol in df.columns and df[tcol].notna().any():
                teacher = str(df[tcol].dropna().iloc[0]).strip()
            col_key = f'{name}  {teacher}  [{i}]'
            subjects.append({'index': i, 'name': name, 'teacher': teacher, 'col_key': col_key})
        i += 1
    return subjects


def build_students_tsv(df: pd.DataFrame, subjects: list[dict],
                       file_type: str) -> tuple[dict, dict]:
    """בונה students ו-col_semesters מ-DataFrame TSV.

    students[שם_תלמיד][col_key] = {sem_a, sem_b, annual, bank}
    col_semesters[col_key] = (has_a, has_b)
    """
    students: dict     = {}
    col_semesters: dict = {}

    for subj in subjects:
        idx     = subj['index']
        col_key = subj['col_key']
        has_a   = False
        has_b   = False

        for _, row in df.iterrows():
            student = str(row.get('שם_תלמיד', '') or '').strip()
            if not student or student == 'nan':
                continue
            if student not in students:
                students[student] = {}

            data: dict = {}

            # מחצית א'
            for j in range(1, 8):
                nc = f'ציון_שם{idx}_{j}'
                vc = f'ציון{idx}_{j}'
                if nc not in df.columns:
                    break
                shem = str(row.get(nc) or '')
                val  = row.get(vc)
                if '02' in shem and 'ציון' in shem and 'מילולי' not in shem:
                    if pd.notna(val):
                        try:
                            data['sem_a'] = int(float(val))
                            has_a = True
                        except (ValueError, TypeError):
                            pass
                elif '01' in shem and 'בנק' in shem:
                    if pd.notna(val):
                        data['bank_a'] = str(val).strip()

            # מחצית ב' + שנתי (שנתי בלבד)
            if file_type == 'annual':
                for j in range(1, 8):
                    nc = f'ב_ציון_שם{idx}_{j}'
                    vc = f'ב_ציון{idx}_{j}'
                    if nc not in df.columns:
                        break
                    shem = str(row.get(nc) or '')
                    val  = row.get(vc)
                    if '02' in shem and 'ציון' in shem and 'מילולי' not in shem:
                        if pd.notna(val):
                            try:
                                data['sem_b'] = int(float(val))
                                has_b = True
                            except (ValueError, TypeError):
                                pass
                    elif '01' in shem and 'בנק' in shem:
                        if pd.notna(val):
                            data['bank_b'] = str(val).strip()

                ac = f'ג_ציון{idx}_1'
                if ac in df.columns:
                    val = row.get(ac)
                    if pd.notna(val):
                        try:
                            data['annual'] = int(float(val))
                        except (ValueError, TypeError):
                            pass

            # הערת בנק רלוונטית לולידציה
            data['bank'] = data.get('bank_b' if file_type == 'annual' else 'bank_a')

            students[student][col_key] = data

        col_semesters[col_key] = (has_a, has_b)

    return students, col_semesters
