import pandas as pd
from core.parser import FIXED_COLS_COUNT


def detect_file_type(df: pd.DataFrame) -> str | None:
    """מזהה סוג הקובץ לפי ערכי עמודת 'עמודה'."""
    col_values = df['עמודה'].dropna().unique()
    has_annual = any('שנתי' in str(v) for v in col_values)
    has_sem_b  = any('מחצית ב' in str(v) for v in col_values)
    has_sem_a  = any('מחצית א' in str(v) and 'ציון' in str(v) for v in col_values)

    if has_annual and has_sem_b:
        return 'annual'
    if has_sem_a and not has_sem_b and not has_annual:
        return 'semester'
    return None


def get_active_cols(df: pd.DataFrame) -> list[str]:
    """מחזיר רשימת עמודות מקצוע פעילות (ללא ריקות ופונקציונליות)."""
    subject_cols = list(df.columns[FIXED_COLS_COUNT:])

    score_rows = df[df['עמודה'].str.contains('ציון', na=False)]
    bank_rows  = df[df['עמודה'].str.contains('הערת בנק', na=False)]

    empty_cols      = {c for c in subject_cols if df[c].isna().all()}
    functional_cols = {
        c for c in subject_cols
        if bank_rows[c].notna().any() and score_rows[c].isna().all()
    }

    return [c for c in subject_cols if c not in empty_cols | functional_cols]


def subject_semesters(df: pd.DataFrame, col: str) -> tuple[bool, bool]:
    """מחזיר (has_sem_a, has_sem_b) עבור עמודת מקצוע נתונה."""
    sem_a_rows = df[df['עמודה'].str.contains(r'מחצית א.*ציון', na=False, regex=True)]
    sem_b_rows = df[df['עמודה'].str.contains('ציון מחצית ב', na=False)]
    has_a = sem_a_rows[col].notna().any()
    has_b = sem_b_rows[col].notna().any()
    return bool(has_a), bool(has_b)
