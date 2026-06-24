import pandas as pd
from collections import defaultdict


ROW_TYPES = {
    'sem_a':  lambda v: 'מחצית א' in v and 'ציון' in v,
    'sem_b':  lambda v: 'ציון מחצית ב' in v,
    'annual': lambda v: 'שנתי' in v and 'ציון' in v,
    'bank':   lambda v: 'הערת בנק' in v,
}


def build_students(df: pd.DataFrame, active_cols: list[str]) -> dict:
    """בונה מבנה נתונים: students[שם_תלמיד][עמודת_מקצוע][sem_a/sem_b/annual/bank]."""
    students = defaultdict(lambda: defaultdict(dict))

    for _, row in df.iterrows():
        name = str(row.get('שם התלמיד', '') or '').strip()
        if not name or name == 'nan':
            continue

        rt = str(row['עמודה']) if pd.notna(row.get('עמודה')) else ''

        for col in active_cols:
            val = row.get(col)
            if pd.isna(val):
                continue
            for key, matcher in ROW_TYPES.items():
                if matcher(rt):
                    students[name][col][key] = val
                    break

    return dict(students)
