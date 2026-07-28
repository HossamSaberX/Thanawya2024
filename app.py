from flask import Flask, request, jsonify, render_template, g
import sqlite3
from flask_caching import Cache
import hashlib
from utils import (
    RESULTS_YEAR,
    TOTAL_DEGREE,
    format_student_result,
    normalize_arabic,
)
import os

app = Flask(__name__)
redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
cache = Cache(app, config={
    'CACHE_TYPE': 'redis',
    'CACHE_REDIS_URL': redis_url
})
DB_PATH = 'data.db'

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

@app.route('/')
def index():
    return render_template(
        'index.html',
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

if __name__ == '__main__':
    app.run(debug=False)
