# Thanawya 2026 Results and Admission Indicator

A web application for searching the 2026 Thanawya Amma result by name or
seating number, plus an evidence-based college admission indicator. The 2026
modern-system total is 320 marks.

The indicator does not reuse last year's score as if the two cohorts were
identical. It converts every official 2025 minimum into its equivalent
whole-cohort rank, then finds the score occupying that rank in the 2026 result
distribution. Results are presented as strong, close, and stretch choices.

The output is guidance, not an official nomination. Final placement also
depends on the preference form, capacity, geographic distribution, aptitude
tests, and any final coordination rules.

Students can use the indicator with either their 2026 seating number or by
entering a score directly from 160 to 320, then selecting the academic track.

## Setup

### 1. Install Dependencies
First, install the required Python packages:
```bash
pip install -r requirements.txt
```

### 2. Prepare the Data
Before running the application, process `data.xlsx` to generate the search
database.

Place your `data.xlsx` file in the main project directory. The Excel file should
have the following columns in the first row: `seating_no`, `arabic_name`,
`total_degree`, and `student_case_desc`.

Then, run the processing script:
```bash
python process_data.py
```
This creates `data.db`, including:

- the seating-number index;
- the FTS5 name-search index used by the existing API;
- `degree_stats`, an aggregated 641-row score/rank table used by the admission
  indicator instead of scanning all 919,396 students per request.

### 3. Run the Application
Once the databases are created, you can start the Flask application:
```bash
python app.py
```
The application will be available at `http://127.0.0.1:5000`.

- Search: `http://127.0.0.1:5000/`
- Admission indicator: `http://127.0.0.1:5000/predict`

For local development without Redis:

```bash
CACHE_TYPE=SimpleCache python app.py
```

## Admission reference data

The committed `data/admission_reference_2025.json` contains the official 2025
scientific and literary minimums and the rank equivalents used by the model.
To rebuild it, save the two official coordination tables as HTML and provide a
2025 result workbook:

```bash
python scripts/prepare_admission_reference.py \
  --science-html /path/to/LimitE2025.html \
  --literary-html /path/to/LimitA2025.html \
  --results-2025 /path/to/results-2025.xlsx \
  --output data/admission_reference_2025.json
```

The preparation script stores source URLs and generation metadata in the JSON
so the reference is auditable and repeatable.
