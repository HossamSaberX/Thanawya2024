RESULTS_YEAR = 2026
TOTAL_DEGREE = 320
PASSING_DEGREE = TOTAL_DEGREE / 2


def normalize_arabic(text):
    if text is None:
        return ""
    text = str(text)
    text = text.replace('ى', 'ي')
    text = text.replace('أ', 'ا')
    text = text.replace('إ', 'ا')
    text = text.replace('آ', 'ا')
    text = text.replace('ة', 'ه')
    text = text.replace('ؤ', 'و')
    text = text.replace('ئ', 'ي')
    return text


def format_student_result(row):
    if not row:
        return None

    row_dict = dict(row)
    total_degree = row_dict.get('degree', 0)
    student_case_desc = str(row_dict.get('student_case_desc') or '').strip()
    if not student_case_desc:
        student_case_desc = 'ناجح' if total_degree >= PASSING_DEGREE else 'راسب'

    return {
        'رقم الجلوس': row_dict.get('seating_no', 'N/A'),
        'الاسم': row_dict.get('name', 'N/A'),
        'الدرجة': total_degree,
        'student_case_desc': student_case_desc
    }
