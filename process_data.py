import pandas as pd
import sqlite3
from pathlib import Path
from utils import RESULTS_YEAR, TOTAL_DEGREE, normalize_arabic

# Configuration
XLSX_FILE = 'data.xlsx'
DB_FILE = 'data.db'
TABLE_NAME = 'students'
FTS_TABLE_NAME = 'students_fts'
DEGREE_STATS_TABLE_NAME = 'degree_stats'
SEATING_NO_COL = 'seating_no'
NAME_COL = 'name'
DEGREE_COL = 'degree'
STATUS_COL = 'student_case_desc'
NORMALIZED_NAME_COL = 'normalized_name'
SOURCE_COLUMNS = {
    'seating_no',
    'arabic_name',
    'total_degree',
    STATUS_COL,
}


def load_students(xlsx_file):
    df = pd.read_excel(xlsx_file)
    missing_columns = SOURCE_COLUMNS.difference(df.columns)
    if missing_columns:
        missing = ', '.join(sorted(missing_columns))
        raise ValueError(f"Missing required Excel columns: {missing}")

    df.rename(columns={
        'seating_no': SEATING_NO_COL,
        'arabic_name': NAME_COL,
        'total_degree': DEGREE_COL,
    }, inplace=True)

    required_values = [SEATING_NO_COL, NAME_COL, DEGREE_COL, STATUS_COL]
    if df[required_values].isna().any().any():
        raise ValueError("The Excel file contains missing student values")
    if df[SEATING_NO_COL].duplicated().any():
        raise ValueError("The Excel file contains duplicate seating numbers")
    if not df[DEGREE_COL].between(0, TOTAL_DEGREE).all():
        raise ValueError(
            f"Student degrees must be between 0 and {TOTAL_DEGREE}"
        )

    df[NAME_COL] = df[NAME_COL].astype(str).str.strip()
    df[STATUS_COL] = df[STATUS_COL].astype(str).str.strip()
    df[NORMALIZED_NAME_COL] = df[NAME_COL].apply(normalize_arabic)
    return df[
        [
            SEATING_NO_COL,
            NAME_COL,
            DEGREE_COL,
            STATUS_COL,
            NORMALIZED_NAME_COL,
        ]
    ].copy()


def create_database(dataframe, db_file):
    db_path = Path(db_file)
    temporary_db_path = db_path.with_suffix(f"{db_path.suffix}.tmp")

    with sqlite3.connect(temporary_db_path) as conn:
        dataframe.to_sql(TABLE_NAME, conn, if_exists='replace', index=False)

        print("Creating index for seating numbers...")
        conn.execute(
            f'CREATE UNIQUE INDEX idx_seating_no '
            f'ON {TABLE_NAME} ({SEATING_NO_COL});'
        )

        print("Creating FTS5 virtual table for name search...")
        conn.execute(f"DROP TABLE IF EXISTS {FTS_TABLE_NAME};")
        # Keep the existing FTS search mechanism and link it by seating number.
        conn.execute(
            f"CREATE VIRTUAL TABLE {FTS_TABLE_NAME} USING fts5("
            f"{NORMALIZED_NAME_COL}, content='{TABLE_NAME}', "
            f"content_rowid='{SEATING_NO_COL}');"
        )

        print("Populating FTS5 table...")
        conn.execute(
            f"INSERT INTO {FTS_TABLE_NAME}(rowid, {NORMALIZED_NAME_COL}) "
            f"SELECT {SEATING_NO_COL}, {NORMALIZED_NAME_COL} "
            f"FROM {TABLE_NAME};"
        )

        print("Creating degree distribution for admission predictions...")
        conn.execute(f"DROP TABLE IF EXISTS {DEGREE_STATS_TABLE_NAME};")
        conn.execute(
            f"CREATE TABLE {DEGREE_STATS_TABLE_NAME} AS "
            f"WITH score_counts AS ("
            f"SELECT {DEGREE_COL} AS degree, COUNT(*) AS student_count "
            f"FROM {TABLE_NAME} GROUP BY {DEGREE_COL}"
            f") "
            f"SELECT degree, student_count, "
            f"SUM(student_count) OVER (ORDER BY degree DESC) "
            f"- student_count + 1 AS rank_start, "
            f"SUM(student_count) OVER (ORDER BY degree DESC) AS rank_end "
            f"FROM score_counts;"
        )
        conn.execute(
            f"CREATE UNIQUE INDEX idx_degree_stats_degree "
            f"ON {DEGREE_STATS_TABLE_NAME} (degree);"
        )
        conn.execute("ANALYZE;")

    temporary_db_path.replace(db_path)


def main():
    dataframe = load_students(XLSX_FILE)
    create_database(dataframe, DB_FILE)
    print(
        f"\nDatabase and FTS index created successfully as {DB_FILE}: "
        f"{len(dataframe):,} students, {RESULTS_YEAR} results, "
        f"{TOTAL_DEGREE} total degree"
    )


if __name__ == '__main__':
    main()
