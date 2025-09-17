import pandas as pd
import sqlite3
from utils import normalize_arabic

# Configuration
XLSX_FILE = 'data.xlsx'
DB_FILE = 'data.db'
TABLE_NAME = 'students'
FTS_TABLE_NAME = 'students_fts'
SEATING_NO_COL = 'seating_no'
NAME_COL = 'name'
DEGREE_COL = 'degree'
NORMALIZED_NAME_COL = 'normalized_name'

# --- 1. Load and prepare the data from Excel ---
df = pd.read_excel(XLSX_FILE)
df.rename(columns={
    'seating_no': SEATING_NO_COL,
    'arabic_name': NAME_COL,
    'total_degree': DEGREE_COL
}, inplace=True)
df[NORMALIZED_NAME_COL] = df[NAME_COL].apply(normalize_arabic)

# --- 2. Create the database connection ---
conn = sqlite3.connect(DB_FILE)
cur = conn.cursor()

# --- 3. Create the main students table and its index ---
db_df = df[[SEATING_NO_COL, NAME_COL, DEGREE_COL, NORMALIZED_NAME_COL]].copy()
db_df.to_sql(TABLE_NAME, conn, if_exists='replace', index=False)

print("Creating index for seating numbers...")
conn.execute(f'CREATE INDEX idx_seating_no ON {TABLE_NAME} ({SEATING_NO_COL});')

# --- 4. Create and populate the FTS5 virtual table for fast name searching ---
print("Creating FTS5 virtual table for name search...")
cur.execute(f"DROP TABLE IF EXISTS {FTS_TABLE_NAME};")
# content_rowid links the FTS table back to the main table's seating_no
cur.execute(f"CREATE VIRTUAL TABLE {FTS_TABLE_NAME} USING fts5({NORMALIZED_NAME_COL}, content='{TABLE_NAME}', content_rowid='{SEATING_NO_COL}');")

print("Populating FTS5 table...")
# This populates the FTS index with all the names from the main table
cur.execute(f"INSERT INTO {FTS_TABLE_NAME}(rowid, {NORMALIZED_NAME_COL}) SELECT {SEATING_NO_COL}, {NORMALIZED_NAME_COL} FROM {TABLE_NAME};")

conn.commit()
conn.close()

print("\nDatabase and FTS index created successfully as data.db")