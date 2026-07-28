# Thanawya 2026 Results

A simple web application to search for student results by name or seating number.
The 2026 modern-system total is 320 marks.

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
This creates `data.db`, including the seating-number index and the FTS5 name
search index used by the API.

### 3. Run the Application
Once the databases are created, you can start the Flask application:
```bash
python app.py
```
The application will be available at `http://127.0.0.1:5000`.
