# Grade Validator — מסמך דרישות מלא
# לשימוש ב-Claude Code

---

## סקירה כללית

כלי Streamlit לבדיקת תקינות ציונים והערות בתעודות.
מורה/רכז מעלה קובץ Excel, התוכנה מנתחת ומחזירה דוח אי-התאמות.

**Tech Stack:** Python · Streamlit · pandas · openpyxl
**פריסה:** Streamlit Cloud (מחובר ל-GitHub)
**עיקרון מרכזי:** אפס שמירת נתונים — כל קובץ מעובד בזיכרון בלבד (io.BytesIO)

---

## מבנה הפרויקט

```
grade_validator/
├── app.py                    ← Streamlit UI
├── CLAUDE.md                 ← קובץ זה
├── requirements.txt          ← streamlit, pandas, openpyxl
├── data/
│   └── bank_notes.xlsx       ← קובץ הגדרות הערות בנק (מקור האמת)
├── core/
│   ├── __init__.py
│   ├── parser.py             ← קריאת Excel, בניית DataFrame
│   ├── subject_detector.py   ← זיהוי מחציות פעילות, עמודות לדילוג
│   ├── student_builder.py    ← dict: תלמיד → מקצוע → נתונים
│   ├── bank_notes_loader.py  ← קריאת bank_notes.xlsx לזיכרון
│   └── validators.py         ← כל לוגיקת הבדיקות
└── output/
    ├── __init__.py
    ├── report_builder.py     ← בניית תצוגה ב-Streamlit
    └── excel_export.py       ← ייצוא Excel צבעוני
```

---

## שלושה סוגי קבצי קלט

| סוג | שורות לתלמיד | מה נבדק |
|---|---|---|
| תקופתי מחצית | 2 (ציון + בנק) | הערות בנק בלבד |
| תקופתי שנתי | 4 (א' + ב' + שנתי + בנק) | ציון שנתי + הערות בנק |
| (תעודות — שלב עתידי) | — | — |

---

## מבנה קובץ Excel

### שורות הקובץ
```
שורה 0:  כותרת (שם הכיתה) — skiprows=2
שורה 1:  ריקה              — skiprows=2
שורה 2:  headers
שורות+:  נתוני תלמידים
```

### 10 עמודות קבועות
```
מס' | ת.ז | שם התלמיד | מין | שכבה | כיתה | עמודה | ממוצע | ממוצע לתעודה | מס שליליים
```

### פרסור כותרת עמודת מקצוע
הפורמט בפועל הוא תא אחד עם רווחים מרובים (לא newlines):
```
אלקטרוניקה יב4   זאזובסקי ליאור   [2482]
```
פרסור לפי רווחים כפולים:
```python
import re
def parse_col_header(col):
    parts = re.split(r'\s{2,}', str(col).strip())
    subject = parts[0] if parts else col
    teacher = parts[1] if len(parts) > 1 else 'לא ידוע'
    code    = parts[2].strip('[]') if len(parts) > 2 else ''
    return subject, teacher, code
```

### ערכי עמודת "עמודה" לפי סוג קובץ

**תקופתי מחצית (2 שורות לתלמיד):**
```
מחצית א' - 02.ציון
מחצית א' - 01.הערת בנק
```

**תקופתי שנתי (4 שורות לתלמיד):**
```
מחצית א' - 02.ציון
מחצית ב' - 02. ציון מחצית ב
שנתי - ציון שנתי מחושב
מחצית ב' - 01. הערת בנק
```

### הערות בנק — פורמט בקובץ
הערות מכילות קוד מספרי בסוגריים:
```
בקיאה בחומר הנלמד [קוד: 63]
שולטת חלקית בחומר הנלמד [קוד: 65]
```
חילוץ קוד:
```python
import re
def extract_bank_code(text):
    m = re.search(r'\[קוד:\s*(\d+)\]', str(text))
    return int(m.group(1)) if m else None
```

---

## קובץ הגדרות הערות בנק (data/bank_notes.xlsx)

### עמודות
| עמודה | תיאור |
|---|---|
| מזהה | קוד מספרי |
| ערך | טקסט ההערה |
| מתאים למחצית | V / ריק |
| מתאים לשנתי | V / ריק |
| ציון מינימום | מספר (ציון חייב להיות מעליו) |
| ציון מקסימום | מספר (ציון חייב להיות מתחתיו) |
| סוג בדיקה | ציון / ירידה / עלייה / ידני |
| סף שינוי | מספר (לירידה/עלייה) |
| הערות | הסברים למפעיל |

### טווחי קודים וסטטוסם
| טווח | משמעות | התנהגות |
|---|---|---|
| 0–41 | הליכות מחנך | ❌ שגיאה — לא רלוונטי לתעודה |
| 42–110 | הערות מקצועיות | נבדק לפי עמודות הקובץ |
| 111+ | תכניות בית ספר | ⚠️ אזהרה — לבדיקת המשתמש |

### קודי ולידציה ידועים
| קוד | טקסט | בדיקה |
|---|---|---|
| 63 | בקיא | ציון ≥ 80 |
| 64 | מתקשה | ציון ≤ 65 |
| 65 | שולט חלקית | ציון בין 55 ל-75 |
| 66 | מגלה יחס חיובי | ציון ≥ 75 |
| 68, 135, 137 | ניכרת התקדמות | עלייה ≥ 5 נק' |
| 69, 134, 151 | חלה ירידה | ירידה ≥ 5 נק' |

### טעינת הקובץ
```python
import pandas as pd

def load_bank_notes(path='data/bank_notes.xlsx'):
    df = pd.read_excel(path, sheet_name='הערות_בנק', dtype={'מזהה': 'Int64'})
    df = df[df['מזהה'].notna()].copy()
    rules = {}
    for _, row in df.iterrows():
        code = int(row['מזהה'])
        rules[code] = {
            'text':       row.get('ערך', ''),
            'semester':   str(row.get('מתאים למחצית', '')).strip() == 'V',
            'annual':     str(row.get('מתאים לשנתי',  '')).strip() == 'V',
            'min_score':  row.get('ציון מינימום') if pd.notna(row.get('ציון מינימום')) else None,
            'max_score':  row.get('ציון מקסימום') if pd.notna(row.get('ציון מקסימום')) else None,
            'check_type': str(row.get('סוג בדיקה', '')).strip(),
            'threshold':  row.get('סף שינוי')    if pd.notna(row.get('סף שינוי'))    else None,
        }
    return rules
```

---

## זיהוי סוג הקובץ

המשתמש בוחר ידנית, התוכנה מאמתת:

```python
def detect_file_type(df):
    col_values = df['עמודה'].dropna().unique()
    has_annual = any('שנתי' in str(v) for v in col_values)
    has_sem_b  = any('מחצית ב' in str(v) for v in col_values)
    has_sem_a  = any('מחצית א' in str(v) and 'ציון' in str(v) for v in col_values)

    if has_annual and has_sem_b:
        return 'annual'      # תקופתי שנתי — 4 שורות
    elif has_sem_a and not has_sem_b and not has_annual:
        return 'semester'    # תקופתי מחצית — 2 שורות
    else:
        return None          # לא מזוהה

# אם file_type != user_selection → הצג שגיאה ובקש העלאה מחדש
```

---

## זיהוי עמודות פעילות

```python
subject_cols = df.columns[10:]   # אחרי 10 עמודות קבועות

score_rows = df[df['עמודה'].str.contains('ציון', na=False)]
bank_rows  = df[df['עמודה'].str.contains('הערת בנק', na=False)]

# לדלג:
empty_cols      = {c for c in subject_cols if df[c].isna().all()}
functional_cols = {c for c in subject_cols
                   if bank_rows[c].notna().any() and score_rows[c].isna().all()}

active_cols = [c for c in subject_cols if c not in empty_cols | functional_cols]
```

---

## זיהוי מחציות פעילות

```python
def subject_semesters(df, col):
    sem_a = df[df['עמודה'].str.contains("מחצית א.*ציון", na=False, regex=True)]
    sem_b = df[df['עמודה'].str.contains("ציון מחצית ב", na=False)]
    has_a = sem_a[col].notna().any()
    has_b = sem_b[col].notna().any()
    return has_a, has_b
```

---

## בניית מבנה נתונים

```python
from collections import defaultdict

students = defaultdict(lambda: defaultdict(dict))

ROW_TYPES = {
    'sem_a':  lambda v: 'מחצית א' in v and 'ציון' in v,
    'sem_b':  lambda v: 'ציון מחצית ב' in v,
    'annual': lambda v: 'שנתי' in v,
    'bank':   lambda v: 'הערת בנק' in v,
}

for _, row in df.iterrows():
    name = row['שם התלמיד']
    rt   = str(row['עמודה']) if pd.notna(row['עמודה']) else ''
    for col in active_cols:
        val = row[col]
        if pd.isna(val):
            continue
        for key, matcher in ROW_TYPES.items():
            if matcher(rt):
                students[name][col][key] = val
                break
```

---

## לוגיקת הבדיקות

### ציון שנתי
```python
import math

def valid_annual_set(sem_a, sem_b):
    avg    = (sem_a + sem_b) / 2
    floor5 = int(math.floor(avg / 5)) * 5
    ceil5  = int(math.ceil(avg / 5)) * 5
    return {floor5, ceil5}

# מחצית א' בלבד:  annual == sem_a
# שתי מחציות:     annual in valid_annual_set(sem_a, sem_b)
```

### אזהרות ציון חריג
```python
if isinstance(val, (int, float)) and val <= 10:
    add('⚠️', 'ציון חריג — ייתכן שגיאת הקלדה', ...)
```

### בדיקת הערת בנק לפי קוד
```python
def validate_bank_note(code, data, rules, file_type, add_fn):
    if code is None:
        return

    # קוד 0–41 — לא רלוונטי לתעודה
    if code <= 41:
        add_fn('❌', 'הערת מחנך — לא רלוונטית לתעודה', ...)
        return

    # קוד 111+ — אזהרה ידנית
    if code >= 111:
        add_fn('⚠️', f'הערה #{code} — בדוק התאמה לסוג תעודה', ...)
        return

    rule = rules.get(code)
    if not rule:
        add_fn('⚠️', f'קוד {code} לא מוגדר בקובץ הערות', ...)
        return

    # התאמה לסוג תעודה
    if file_type == 'semester' and not rule['semester']:
        add_fn('❌', 'הערה לא מתאימה לתעודת מחצית', ...)
        return
    if file_type == 'annual' and not rule['annual']:
        add_fn('❌', 'הערה לא מתאימה לתעודת שנה', ...)
        return

    # בדיקת ציון
    score = data.get('sem_b') or data.get('sem_a')
    check = rule['check_type']

    if check == 'ציון':
        if rule['min_score'] and score is not None and score < rule['min_score']:
            add_fn('❌', f'ציון {score} נמוך מהמינימום הנדרש ({rule["min_score"]})', ...)
        if rule['max_score'] and score is not None and score > rule['max_score']:
            add_fn('❌', f'ציון {score} גבוה מהמקסימום המותר ({rule["max_score"]})', ...)
        if rule['min_score'] and rule['max_score']:
            if score is not None and not (rule['min_score'] <= score <= rule['max_score']):
                add_fn('❌', f'ציון {score} מחוץ לטווח {rule["min_score"]}–{rule["max_score"]}', ...)

    elif check == 'ירידה':
        sem_a = data.get('sem_a')
        sem_b = data.get('sem_b')
        thr   = rule['threshold'] or 5
        if sem_a and sem_b and (sem_a - sem_b) < thr:
            add_fn('❌', f'הערת ירידה — אין ירידה של {thr}+ נק\' (א={sem_a}, ב={sem_b})', ...)

    elif check == 'עלייה':
        sem_a = data.get('sem_a')
        sem_b = data.get('sem_b')
        thr   = rule['threshold'] or 5
        if sem_a and sem_b and (sem_b - sem_a) < thr:
            add_fn('❌', f'הערת עלייה — אין עלייה של {thr}+ נק\' (א={sem_a}, ב={sem_b})', ...)
```

---

## זרימת המשתמש ב-Streamlit

```
1. בחירת סוג תעודה  ← radio button: "תקופתי מחצית" / "תקופתי שנתי"
        ↓
2. העלאת קובץ Excel ← st.file_uploader, io.BytesIO — לא נשמר לדיסק
        ↓
3. ולידציה מבנית    ← אוטומטי
   ✅ "זוהתה כיתה יב4 — 12 תלמידים, 8 מקצועות פעילים"
   ❌ "הקובץ לא מתאים לסוג שנבחר — אנא העלה מחדש"
        ↓
4. [הרץ בדיקה]      ← כפתור
        ↓
5. תוצאות במסך:
   סיכום: N שגיאות | N אזהרות | N מורים
   טאב "לפי מורה" → לפי מקצוע → לפי תלמיד
   טאב "ממוצעי כיתה" → לפני/אחרי תיקון
        ↓
6. [📥 הורד דוח Excel] ← כפתור
```

---

## פורמט הפלט

### מסך — לפי מורה
```
▼ זאזובסקי ליאור (3 שגיאות, 1 אזהרה)
  ▼ אלקטרוניקה יב4
    ❌ כהן מרים — ציון שנתי שגוי
       א=80 | ב=90 | ממוצע=85.0 | שנתי=90 | צפוי=[85]
    ⚠️ לוי דוד — ציון חריג (ציון=10) — ייתכן שגיאת הקלדה
```

### מסך — ממוצעי כיתה
| תלמיד | ממוצע נוכחי | ממוצע מתוקן | הפרש |
|---|---|---|---|
| כהן מרים | 84.2 | 85.0 | +0.8 |

### Excel להורדה
- גיליון לכל מורה
- צבעים: ❌ רקע אדום בהיר, ⚠️ רקע צהוב, ✅ רקע ירוק בהיר
- עמודות: תלמיד | מקצוע | סוג בעיה | פרטים | ציון נוכחי | ציון מוצע

---

## עדכון קובץ הערות בנק

כשמוסיפים הערות חדשות או משנים כללים:
1. פותחים `data/bank_notes.xlsx`
2. מוסיפים/עורכים שורה בגיליון "הערות_בנק"
3. שומרים — התוכנה תקרא בהרצה הבאה
4. **אין צורך לשנות קוד Python**

---

## דגשים טכניים

- `encoding='utf-8-sig'` בכל קריאת/כתיבת Excel
- כל הממשק בעברית, `st.set_page_config(layout="wide")`
- CSS לכיוון RTL במידת הצורך
- הפרד קפדני: `core/` = לוגיקה, `app.py` = UI בלבד
- `app.py` לא מכיל שום לוגיקת בדיקה

