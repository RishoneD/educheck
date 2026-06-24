import re
import io
import pandas as pd


FIXED_COLS_COUNT = 10

# שמות עמודות קבועות צפויות (לאימות מבני)
EXPECTED_FIXED = ['מס\'', 'ת.ז', 'שם התלמיד', 'מין', 'שכבה', 'כיתה', 'עמודה',
                  'ממוצע', 'ממוצע לתעודה', 'מס שליליים']


def parse_excel(file_bytes: bytes) -> tuple[pd.DataFrame, str]:
    """קורא קובץ Excel ומחזיר (DataFrame, שם כיתה).

    שורות 0–1 הן כותרת ושורה ריקה — נדלגות.
    שם הכיתה נקרא מהתא הראשון של שורה 0.
    """
    raw = pd.read_excel(io.BytesIO(file_bytes), header=None, dtype=str)

    # שם הכיתה — שורה 0, תא 0
    class_name = str(raw.iloc[0, 0]).strip() if len(raw) > 0 else ''
    if class_name in ('nan', 'None', ''):
        class_name = 'לא ידוע'

    # headers בשורה 2
    df = pd.read_excel(io.BytesIO(file_bytes), skiprows=2, dtype=str)

    # ממירים עמודות מספריות
    numeric_subject_cols = df.columns[FIXED_COLS_COUNT:]
    for col in numeric_subject_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # מנקים שורות ריקות לחלוטין
    df = df.dropna(how='all').reset_index(drop=True)

    return df, class_name


def parse_col_header(col: str) -> tuple[str, str, str]:
    """מפרסר כותרת עמודת מקצוע לפי רווחים כפולים.

    Returns (subject, teacher, code_str)
    """
    parts = re.split(r'\s{2,}', str(col).strip())
    subject = parts[0] if parts else str(col)
    teacher = parts[1] if len(parts) > 1 else 'לא ידוע'
    code    = parts[2].strip('[]') if len(parts) > 2 else ''
    return subject, teacher, code


def extract_bank_code(text) -> int | None:
    """מחלץ קוד מספרי מהערת בנק כגון: 'בקיא [קוד: 63]'."""
    m = re.search(r'\[קוד:\s*(\d+)\]', str(text))
    return int(m.group(1)) if m else None
