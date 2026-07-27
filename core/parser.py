import re
import io
import difflib
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


def find_bank_code_by_text(bank_text: str, bank_rules: dict) -> int | None:
    """מאתר קוד הערת בנק לפי התאמת טקסט.

    מטפל ב:
    - הערות מורחבות: ה-TSV מכיל טקסט נוסף אחרי הנוסח הבסיסי (בודק prefix)
    - שינויי מגדר: מגיע/מגיעה וכו'
    - הערות קטועות: ה-TSV קצר מהנוסח בבנק
    """
    if not bank_text or not bank_rules:
        return None
    text = bank_text.strip()
    best_code, best_ratio, best_len = None, 0.0, 0
    for code, rule in bank_rules.items():
        rule_text = str(rule.get('text', '')).strip()
        if not rule_text or rule_text.startswith('*'):
            continue

        # השוואת rule_text מול תחילת ה-text (prefix) — מטפל בהערות מורחבות
        prefix = text[:len(rule_text)] if len(text) >= len(rule_text) else text
        prefix_ratio = difflib.SequenceMatcher(None, rule_text, prefix).ratio()

        # השוואה מלאה — מטפל בהערות קצרות/קטועות
        full_ratio = difflib.SequenceMatcher(None, text, rule_text).ratio()

        ratio = max(prefix_ratio, full_ratio)
        # בציון שווה — מעדיפים את הכלל הארוך יותר (ספציפי יותר, כמו קוד 69 על פני 30)
        if ratio > best_ratio or (ratio == best_ratio and len(rule_text) > best_len):
            best_ratio = ratio
            best_code = code
            best_len = len(rule_text)
    return best_code if best_ratio >= 0.75 else None


def inject_bank_code(bank_text: str, bank_rules: dict) -> str:
    """מחדיר קוד להערת בנק אם לא קיים. מחזיר את הטקסט המועשר."""
    if not bank_text or '[קוד:' in bank_text:
        return bank_text
    code = find_bank_code_by_text(bank_text, bank_rules)
    if code is not None:
        return f'{bank_text} [קוד: {code}]'
    return bank_text


# ── TSV (מאשב) ────────────────────────────────────────────────────────────────

_GRADE_HEBREW = {
    '10': "י'", '11': 'י"א', '12': 'י"ב',
    "י'": "י'", 'י"א': 'י"א', 'י"ב': 'י"ב',
}


def _col_val(df: pd.DataFrame, col: str) -> str:
    """מחזיר את הערך הראשון הלא-ריק של עמודה, או ''."""
    if col in df.columns and df[col].notna().any():
        v = str(df[col].dropna().iloc[0]).strip()
        return v if v not in ('', 'nan') else ''
    return ''


def parse_tsv(file_bytes: bytes) -> tuple[pd.DataFrame, str]:
    """קורא קובץ TSV ממאשב ומחזיר (DataFrame, שם כיתה מלא).

    מנסה לשלב שכבה (י'/י"א/י"ב) עם מספר הכיתה לתצוגה נוחה כגון 'י" א 4'.
    """
    df = pd.read_csv(io.BytesIO(file_bytes), sep='\t', encoding='utf-8-sig', dtype=str)
    df = df.dropna(how='all').reset_index(drop=True)

    grade   = _GRADE_HEBREW.get(_col_val(df, 'שכבה'), '')
    kita    = _col_val(df, 'כיתה') or _col_val(df, 'כיתה_שם')

    if grade and kita:
        class_name = f'{grade} {kita}'
    elif grade:
        class_name = grade
    elif kita:
        class_name = kita
    else:
        class_name = 'לא ידוע'

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
    """מחזיר רשימת מקצועות ייחודיים ע"י סריקת כל שורות הקובץ.

    בניגוד לגישה הקודמת שלקחה רק את השורה הראשונה — כאן סורקים את כל התלמידים
    כי יכולים להיות מקצועות ומורים שונים לתלמידים שונים באותה עמודת אינדקס.
    col_key = 'שם  מורה' (ללא אינדקס — המפתח הלוגי הוא שם+מורה).
    """
    seen: dict = {}
    i = 1
    while f'מקצוע{i}' in df.columns:
        for _, row in df.iterrows():
            name = str(row.get(f'מקצוע{i}') or '').strip()
            if not name or name == 'nan':
                continue
            teacher = ''
            tcol = f'מורה{i}'
            if tcol in df.columns:
                t = str(row.get(tcol) or '').strip()
                if t and t != 'nan':
                    teacher = t
            key = (name, teacher)
            if key not in seen:
                seen[key] = {'name': name, 'teacher': teacher,
                             'col_key': f'{name}  {teacher}'}
        i += 1
    return list(seen.values())


def build_students_tsv(df: pd.DataFrame, subjects: list[dict],
                       file_type: str, bank_rules: dict | None = None) -> tuple[dict, dict]:
    """בונה students ו-col_semesters מ-DataFrame TSV.

    גישה תלמיד-מרכזית: לכל תלמיד קוראים את המקצוע/המורה שלו עצמו בכל עמודה.
    כך מטופלים: מקצועות שונים לתלמידים שונים באותו אינדקס, וכמה מורים לאותו מקצוע.

    col_key = 'שם_מקצוע  מורה'  (ללא אינדקס)
    col_semesters[col_key] = (has_a, has_b)  — מצטבר מכל התלמידים
    """
    students: dict      = {}
    col_semesters: dict = {}

    max_i = 0
    while f'מקצוע{max_i + 1}' in df.columns:
        max_i += 1

    for _, row in df.iterrows():
        student = str(row.get('שם_תלמיד', '') or '').strip()
        if not student or student == 'nan':
            continue
        if student not in students:
            students[student] = {}

        for i in range(1, max_i + 1):
            subj_name = str(row.get(f'מקצוע{i}') or '').strip()
            if not subj_name or subj_name == 'nan':
                continue

            teacher = ''
            tcol = f'מורה{i}'
            if tcol in df.columns:
                t = str(row.get(tcol) or '').strip()
                if t and t != 'nan':
                    teacher = t

            col_key = f'{subj_name}  {teacher}'
            data: dict = {}
            has_a = False
            has_b = False

            # מחצית א'
            for j in range(1, 8):
                nc = f'ציון_שם{i}_{j}'
                vc = f'ציון{i}_{j}'
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
                        data['bank_a'] = inject_bank_code(str(val).strip(), bank_rules or {})

            # מחצית ב' + שנתי
            if file_type == 'annual':
                for j in range(1, 8):
                    nc = f'ב_ציון_שם{i}_{j}'
                    vc = f'ב_ציון{i}_{j}'
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
                            data['bank_b'] = inject_bank_code(str(val).strip(), bank_rules or {})

                ac = f'ג_ציון{i}_1'
                if ac in df.columns:
                    val = row.get(ac)
                    if pd.notna(val):
                        try:
                            data['annual'] = int(float(val))
                        except (ValueError, TypeError):
                            pass

            data['bank'] = data.get('bank_b' if file_type == 'annual' else 'bank_a')
            students[student][col_key] = data

            # עדכון has_a/has_b מצטבר לכל תלמידי המקצוע
            prev_a, prev_b = col_semesters.get(col_key, (False, False))
            col_semesters[col_key] = (prev_a or has_a, prev_b or has_b)

    return students, col_semesters
