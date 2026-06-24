import pandas as pd


def load_bank_notes(path='data/bank_notes.xlsx'):
    """טוען את הגדרות הערות הבנק מ-Excel לזיכרון."""
    # קוראים כ-str תחילה כי יש שורות כותרת/הסבר עם טקסט בעמודת מזהה
    df = pd.read_excel(path, sheet_name='הערות_בנק', dtype=str)

    # שומרים רק שורות שה-מזהה שלהן הוא מספר שלם
    df['_id_num'] = pd.to_numeric(df.get('מזהה', pd.Series(dtype=str)), errors='coerce')
    df = df[df['_id_num'].notna()].copy()

    def _num(val):
        """ממיר ערך מחרוזת למספר, מחזיר None אם לא מספר/ריק."""
        if val is None:
            return None
        s = str(val).strip()
        if s in ('', 'nan', 'None'):
            return None
        try:
            return float(s)
        except ValueError:
            return None

    def _str(val):
        s = str(val).strip() if val is not None else ''
        return '' if s in ('nan', 'None') else s

    rules = {}
    for _, row in df.iterrows():
        code = int(row['_id_num'])
        rules[code] = {
            'text':       _str(row.get('ערך', '')),
            'semester':   _str(row.get('מתאים למחצית', '')) == 'V',
            'annual':     _str(row.get('מתאים לשנתי',  '')) == 'V',
            'min_score':  _num(row.get('ציון מינימום')),
            'max_score':  _num(row.get('ציון מקסימום')),
            'check_type': _str(row.get('סוג בדיקה', '')),
            'threshold':  _num(row.get('סף שינוי')),
        }
    return rules
