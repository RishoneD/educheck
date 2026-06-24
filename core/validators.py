import math
from core.parser import parse_col_header, extract_bank_code


def _safe_num(val):
    """ממיר ערך למספר, מחזיר None אם לא מספר."""
    try:
        f = float(val)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


def valid_annual_set(sem_a: float, sem_b: float) -> set[int]:
    """מחשב קבוצת ציונות שנתיות תקינות (עיגול ל-5 הקרוב מטה/מעלה)."""
    avg    = (sem_a + sem_b) / 2
    floor5 = int(math.floor(avg / 5)) * 5
    ceil5  = int(math.ceil(avg / 5)) * 5
    return {floor5, ceil5}


def run_all_validations(students: dict, active_cols: list[str],
                        col_semesters: dict, file_type: str,
                        bank_rules: dict) -> list[dict]:
    """מריץ את כל הבדיקות ומחזיר רשימת ממצאים.

    כל ממצא הוא dict עם המפתחות:
        severity  — '❌' / '⚠️'
        student   — שם תלמיד
        col       — עמודת מקצוע (raw)
        subject   — שם מקצוע
        teacher   — שם מורה
        message   — תיאור הבעיה
        details   — פרטים נוספים (מחרוזת)
    """
    findings = []

    def add(severity, student, col, subject, teacher, message, details=''):
        findings.append({
            'severity': severity,
            'student':  student,
            'col':      col,
            'subject':  subject,
            'teacher':  teacher,
            'message':  message,
            'details':  details,
        })

    for student, subjects in students.items():
        for col, data in subjects.items():
            subject, teacher, _ = parse_col_header(col)
            has_a, has_b = col_semesters.get(col, (False, False))

            sem_a  = _safe_num(data.get('sem_a'))
            sem_b  = _safe_num(data.get('sem_b'))
            annual = _safe_num(data.get('annual'))
            bank   = data.get('bank')

            # --- ציונות חסרות ---
            if file_type == 'semester':
                if sem_a is None:
                    add('⚠️', student, col, subject, teacher,
                        'ציון מחצית א\' חסר — יש לבדוק אם מוצדק')

            elif file_type == 'annual':
                if has_a and sem_a is None:
                    add('⚠️', student, col, subject, teacher,
                        'ציון מחצית א\' חסר — יש לבדוק אם מוצדק')
                if has_b and sem_b is None:
                    add('⚠️', student, col, subject, teacher,
                        'ציון מחצית ב\' חסר — יש לבדוק אם מוצדק')
                if annual is None:
                    add('⚠️', student, col, subject, teacher,
                        'ציון שנתי חסר — יש לבדוק אם מוצדק')

            # --- ציון חריג (0–10) ---
            for label, score in [('מחצית א\'', sem_a), ('מחצית ב\'', sem_b), ('שנתי', annual)]:
                if score is not None and score <= 10:
                    add('⚠️', student, col, subject, teacher,
                        f'ציון חריג — ייתכן שגיאת הקלדה',
                        f'ציון {label} = {int(score)}')

            # --- ציון שנתי (רק בקובץ שנתי) ---
            if file_type == 'annual' and annual is not None:
                if has_a and has_b and sem_a is not None and sem_b is not None:
                    valid = valid_annual_set(sem_a, sem_b)
                    if int(annual) not in valid:
                        add('❌', student, col, subject, teacher,
                            'ציון שנתי שגוי',
                            f'א={int(sem_a)} | ב={int(sem_b)} | '
                            f'ממוצע={(sem_a+sem_b)/2:.1f} | '
                            f'שנתי={int(annual)} | '
                            f'צפוי={sorted(valid)}')
                elif has_a and not has_b and sem_a is not None:
                    if int(annual) != int(sem_a):
                        add('❌', student, col, subject, teacher,
                            'ציון שנתי שגוי (מקצוע חד-סמסטרלי)',
                            f'א={int(sem_a)} | שנתי={int(annual)} | צפוי={int(sem_a)}')
                elif has_b and not has_a and sem_b is not None:
                    if int(annual) != int(sem_b):
                        add('❌', student, col, subject, teacher,
                            'ציון שנתי שגוי (מקצוע חד-סמסטרלי)',
                            f'ב={int(sem_b)} | שנתי={int(annual)} | צפוי={int(sem_b)}')

            # --- הערת בנק ---
            _validate_bank_note(
                bank, data, sem_a, sem_b, has_a, has_b,
                file_type, bank_rules,
                lambda sev, msg, det='': add(sev, student, col, subject, teacher, msg, det)
            )

    return findings


def _validate_bank_note(bank_val, data, sem_a, sem_b, has_a, has_b,
                        file_type, rules, add_fn):
    """בודק הערת בנק עבור תלמיד ומקצוע נתונים."""
    if bank_val is None or str(bank_val).strip() in ('', 'nan', 'None'):
        add_fn('⚠️', 'הערת בנק חסרה — יש להוסיף הערה')
        return

    code = extract_bank_code(bank_val)

    if code is None:
        add_fn('⚠️', 'לא ניתן לזהות קוד בהערת הבנק', str(bank_val)[:80])
        return

    # קוד 0–41 — הליכות מחנך
    if code <= 41:
        add_fn('❌', 'הערת מחנך — לא רלוונטית לתעודה', f'קוד {code}')
        return

    # קוד 111+ — תכניות בית ספר
    if code >= 111:
        add_fn('⚠️', f'הערה #{code} — בדוק התאמה לסוג תעודה (תכנית בית ספר)')
        return

    rule = rules.get(code)
    if not rule:
        add_fn('⚠️', f'קוד {code} לא מוגדר בקובץ הערות בנק')
        return

    # התאמה לסוג תעודה
    if file_type == 'semester' and not rule['semester']:
        add_fn('❌', 'הערה לא מתאימה לתעודת מחצית', f'קוד {code}')
        return
    if file_type == 'annual' and not rule['annual']:
        add_fn('❌', 'הערה לא מתאימה לתעודת שנה', f'קוד {code}')
        return

    check = rule['check_type']
    score = sem_b if sem_b is not None else sem_a

    if check == 'ציון':
        mn = rule['min_score']
        mx = rule['max_score']
        if mn is not None and mx is not None:
            if score is None or not (mn <= score <= mx):
                add_fn('❌',
                       f'ציון מחוץ לטווח הנדרש להערה זו ({int(mn)}–{int(mx)})',
                       f'ציון={int(score) if score is not None else "חסר"} | קוד {code}')
        elif mn is not None:
            if score is None or score < mn:
                add_fn('❌',
                       f'ציון נמוך מהמינימום הנדרש ({int(mn)})',
                       f'ציון={int(score) if score is not None else "חסר"} | קוד {code}')
        elif mx is not None:
            if score is None or score > mx:
                add_fn('❌',
                       f'ציון גבוה מהמקסימום המותר ({int(mx)})',
                       f'ציון={int(score) if score is not None else "חסר"} | קוד {code}')

    elif check == 'ירידה':
        if not has_a or not has_b:
            add_fn('⚠️',
                   'הערת ירידה לא ניתנת לאימות — המקצוע נלמד רק מחצית אחת',
                   f'קוד {code}')
        elif sem_a is not None and sem_b is not None:
            thr = rule['threshold'] or 5
            if (sem_a - sem_b) < thr:
                add_fn('❌',
                       f'הערת ירידה — אין ירידה של {int(thr)}+ נק\'',
                       f'א={int(sem_a)} | ב={int(sem_b)} | הפרש={int(sem_a - sem_b)} | קוד {code}')

    elif check == 'עלייה':
        if not has_a or not has_b:
            add_fn('⚠️',
                   'הערת עלייה לא ניתנת לאימות — המקצוע נלמד רק מחצית אחת',
                   f'קוד {code}')
        elif sem_a is not None and sem_b is not None:
            thr = rule['threshold'] or 5
            if (sem_b - sem_a) < thr:
                add_fn('❌',
                       f'הערת עלייה — אין עלייה של {int(thr)}+ נק\'',
                       f'א={int(sem_a)} | ב={int(sem_b)} | הפרש={int(sem_b - sem_a)} | קוד {code}')
