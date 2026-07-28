from flask import Flask, request, jsonify, render_template, g
import sqlite3
from flask_caching import Cache
import hashlib
from decimal import Decimal, InvalidOperation
from prediction import PredictionEngine, TRACK_LABELS
from utils import (
    PASSING_DEGREE,
    RESULTS_YEAR,
    TOTAL_DEGREE,
    format_student_result,
    normalize_arabic,
)
import os

app = Flask(__name__)
redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
cache_type = os.environ.get('CACHE_TYPE', 'redis')
cache_config = {'CACHE_TYPE': cache_type}
if cache_type == 'redis':
    cache_config['CACHE_REDIS_URL'] = redis_url
cache = Cache(app, config=cache_config)
DB_PATH = os.environ.get('DB_PATH', 'data.db')
prediction_engine = PredictionEngine()

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode = WAL;")
        g.db.execute("PRAGMA synchronous = 1;")
        g.db.execute("PRAGMA cache_size = -8000;")
        g.db.execute("PRAGMA temp_store = memory;")
    return g.db

@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'db'):
        g.db.close()

def query_db(query, args=(), one=False):
    try:
        cur = get_db().execute(query, args)
        rv = cur.fetchall()
        return (rv[0] if rv else None) if one else rv
    except sqlite3.OperationalError:
        return None if one else []

def make_cache_key():
    query = request.args.get('query')
    page = request.args.get('page', 1)
    key_str = f"query={query}&page={page}"
    key_str = f"year={RESULTS_YEAR}&{key_str}"
    return hashlib.md5(key_str.encode()).hexdigest()


def make_prediction_cache_key():
    seating_no = request.args.get('seating_no')
    score = request.args.get('score')
    input_mode = request.args.get('input_mode')
    track = request.args.get('track')
    institution_filter = request.args.get(
        'institution_filter',
        'universities',
    )
    model_version = prediction_engine.reference.get('version', 1)
    key_str = (
        f"year={RESULTS_YEAR}&model={model_version}"
        f"&mode={input_mode}&prediction={seating_no}&score={score}&track={track}"
        f"&filter={institution_filter}"
    )
    return hashlib.md5(key_str.encode()).hexdigest()


@app.route('/')
def index():
    return render_template(
        'index.html',
        results_year=RESULTS_YEAR,
        total_degree=TOTAL_DEGREE,
    )


@app.route('/predict')
def predict_page():
    return render_template(
        'predict.html',
        results_year=RESULTS_YEAR,
        total_degree=TOTAL_DEGREE,
    )


@app.route('/search', methods=['GET'])
@cache.cached(timeout=86400, key_prefix=make_cache_key)
def search():
    query = request.args.get('query')
    page = int(request.args.get('page', 1))
    per_page = 10
    if not query:
        return jsonify({"error": "No query provided"}), 400
    results_list = []
    total_results = 0
    if query.isdigit():
        sql_query = "SELECT * FROM students WHERE seating_no = ?"
        result_row = query_db(sql_query, [query], one=True)
        if result_row:
            total_results = 1
            results_list.append(format_student_result(result_row))
    else:
        offset = (page - 1) * per_page
        normalized_query = normalize_arabic(query)
        fts_query = f"SELECT rowid FROM students_fts WHERE normalized_name MATCH ?;"
        matching_ids_rows = query_db(fts_query, [normalized_query])
        if matching_ids_rows:
            matching_ids = [row[0] for row in matching_ids_rows]
            total_results = len(matching_ids)
            paginated_ids = matching_ids[offset : offset + per_page]
            if paginated_ids:
                placeholders = ','.join('?' for _ in paginated_ids)
                results_query = f"SELECT * FROM students WHERE seating_no IN ({placeholders}) ORDER BY degree DESC"
                paginated_results = query_db(results_query, paginated_ids)
                for row in paginated_results:
                    results_list.append(format_student_result(row))
    return jsonify({
        "results": results_list,
        "total_results": total_results,
        "results_year": RESULTS_YEAR,
        "total_degree": TOTAL_DEGREE,
    })


@app.route('/api/predict', methods=['GET'])
@cache.cached(timeout=86400, key_prefix=make_prediction_cache_key)
def predict():
    seating_no = request.args.get('seating_no', '').strip()
    score_raw = request.args.get('score', '').strip()
    input_mode = request.args.get('input_mode', '').strip()
    track = request.args.get('track', '').strip()
    institution_filter = request.args.get(
        'institution_filter',
        'universities',
    ).strip()

    if not input_mode:
        input_mode = 'score' if score_raw and not seating_no else 'seating'
    if input_mode not in {'seating', 'score'}:
        return jsonify({
            'error': 'اختر رقم الجلوس أو إدخال المجموع.',
            'code': 'invalid_input_mode',
        }), 400
    if track not in TRACK_LABELS:
        return jsonify({
            'error': 'اختر الشعبة قبل حساب التوقع.',
            'code': 'invalid_track',
        }), 400
    if institution_filter not in {'universities', 'all'}:
        return jsonify({
            'error': 'اختيار نوع المؤسسة غير صحيح.',
            'code': 'invalid_institution_filter',
        }), 400

    degree_stats = query_db(
        "SELECT degree, student_count, rank_start, rank_end "
        "FROM degree_stats ORDER BY degree DESC"
    )
    if not degree_stats:
        return jsonify({
            'error': (
                'بيانات مؤشر التنسيق غير جاهزة الآن. '
                'أعد بناء قاعدة البيانات ثم حاول مرة أخرى.'
            ),
            'code': 'prediction_data_unavailable',
        }), 503

    if input_mode == 'seating':
        if not seating_no.isdigit():
            return jsonify({
                'error': 'اكتب رقم جلوس صحيح بالأرقام فقط.',
                'code': 'invalid_seating_no',
            }), 400
        student = query_db(
            "SELECT * FROM students WHERE seating_no = ?",
            [seating_no],
            one=True,
        )
        if not student:
            return jsonify({
                'error': 'رقم الجلوس غير موجود في نتيجة 2026.',
                'code': 'student_not_found',
            }), 404

        student_result = format_student_result(student)
        if 'ناجح' not in student_result['student_case_desc']:
            return jsonify({
                'error': (
                    'التوقع متاح بعد النتيجة النهائية للطالب الناجح. '
                    f"الحالة الحالية: {student_result['student_case_desc']}."
                ),
                'code': 'result_not_final',
                'student': student_result,
            }), 422
        student_rank = query_db(
            "SELECT student_count, rank_start, rank_end "
            "FROM degree_stats WHERE degree = ?",
            [student_result['الدرجة']],
            one=True,
        )
    else:
        try:
            score_decimal = Decimal(score_raw)
        except InvalidOperation:
            score_decimal = None
        if (
            score_decimal is None
            or not score_decimal.is_finite()
            or score_decimal.as_tuple().exponent < -2
            or score_decimal < Decimal(str(PASSING_DEGREE))
            or score_decimal > Decimal(str(TOTAL_DEGREE))
        ):
            return jsonify({
                'error': (
                    f'اكتب مجموعًا من {PASSING_DEGREE:g} إلى '
                    f'{TOTAL_DEGREE}، بحد أقصى رقمين بعد العلامة.'
                ),
                'code': 'invalid_score',
            }), 400

        score = float(score_decimal)
        student_result = {
            'رقم الجلوس': None,
            'الاسم': None,
            'الدرجة': score,
            'student_case_desc': 'إدخال مباشر',
        }
        student_rank = query_db(
            "SELECT student_count, rank_start, rank_end "
            "FROM degree_stats WHERE ABS(degree - ?) < 0.000001",
            [score],
            one=True,
        )
        if not student_rank:
            students_above = query_db(
                "SELECT COALESCE(MAX(rank_end), 0) AS total "
                "FROM degree_stats WHERE degree > ?",
                [score],
                one=True,
            )['total']
            estimated_rank = students_above + 1
            student_rank = {
                'student_count': 0,
                'rank_start': estimated_rank,
                'rank_end': estimated_rank,
            }

    if not student_rank:
        return jsonify({
            'error': (
                'بيانات مؤشر التنسيق غير جاهزة الآن. '
                'أعد بناء قاعدة البيانات ثم حاول مرة أخرى.'
            ),
            'code': 'prediction_data_unavailable',
        }), 503

    total_students = degree_stats[-1]['rank_end']
    current_distribution = [dict(row) for row in degree_stats]
    prediction = prediction_engine.predict(
        student_result['الدرجة'],
        track,
        current_distribution,
        institution_filter,
    )

    return jsonify({
        'student': student_result,
        'ranking': {
            'rank_start': student_rank['rank_start'],
            'rank_end': student_rank['rank_end'],
            'tied_students': student_rank['student_count'],
            'total_students': total_students,
            'scope': 'all_students',
            'note': (
                'موقع تقريبي داخل كل نتائج 2026، وليس ترتيب الشعبة الرسمي.'
            ),
        },
        'prediction': prediction,
        'input_mode': input_mode,
        'results_year': RESULTS_YEAR,
        'total_degree': TOTAL_DEGREE,
        'disclaimer': (
            'مؤشر استرشادي وليس ترشيحًا رسميًا. الرغبات والطاقة '
            'الاستيعابية واختبارات القدرات والتوزيع الجغرافي قد تغير النتيجة.'
        ),
    })


if __name__ == '__main__':
    app.run(debug=False)
