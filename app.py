from flask import Flask, request, render_template, send_file
import pandas as pd
import logging
import os
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Paths to CSV files
CSV_FILE_PATH = 'student_data.csv'
REPORT_CSV_PATH = 'studentcgpa_data.csv'

# Expected columns for report CSV
required_report_columns = [
    'Roll No', 'Name', 'Hostel status', 'cgpa', 'Total Registerd credits',
    'Result Declared Credits', 'Result Awaiting Credits', 'Obtained Credits',
    'Cumulative Grade Points', 'Missing Courses', 'Not Declared Courses',
    'Error', 'Credit Requirements', 'Attained', 'Not Attained',
    'Requirements Error', 'Backlog Count', 'Backlog Details'
]

# Load memo data
def load_memo_data():
    try:
        if not os.path.exists(CSV_FILE_PATH):
            raise FileNotFoundError(f"CSV file not found at {CSV_FILE_PATH}")
        df = pd.read_csv(CSV_FILE_PATH, delimiter=',', encoding='utf-8')
        app.logger.debug(f"Loaded {len(df)} records from CSV")
        app.logger.debug(f"Unique University IDs: {df['University ID'].astype(str).str.strip().unique()}")
        return df
    except Exception as e:
        app.logger.error(f"Error loading CSV: {e}")
        return None

# Load report data
def load_report_data():
    try:
        df = pd.read_csv(REPORT_CSV_PATH, dtype={'Roll No': str})
        df.columns = [col.strip() for col in df.columns]
        missing_columns = [col for col in required_report_columns if col not in df.columns]
        if missing_columns:
            app.logger.error(f"Missing columns in report CSV: {missing_columns}")
            return None
        app.logger.debug(f"Loaded {len(df)} report records from CSV")
        app.logger.debug(f"CSV columns: {df.columns.tolist()}")
        return df
    except FileNotFoundError:
        app.logger.error(f"Error: {REPORT_CSV_PATH} not found")
        return None
    except pd.errors.EmptyDataError:
        app.logger.error(f"Error: {REPORT_CSV_PATH} is empty")
        return None
    except Exception as e:
        app.logger.error(f"Error loading report CSV: {e}")
        return None

# Generate course memo
def generate_memo(student_id):
    df = load_memo_data()
    if df is None:
        return None, None, None, "Error loading data from CSV file. Please ensure 'student_data.csv' exists and is correctly formatted."

    # Convert input and dataframe IDs to strings and strip whitespace for comparison
    student_id = str(student_id).strip()
    df['University ID'] = df['University ID'].astype(str).str.strip()

    # Case-insensitive matching
    student_data = df[df['University ID'].str.lower() == student_id.lower()]
    app.logger.debug(f"Found {len(student_data)} records for University ID: {student_id}")
    if student_data.empty:
        return None, None, None, f"No data found for University ID '{student_id}'. Please verify the ID and try again."

    student_name = student_data['Name'].iloc[0]

    # Group by AcademicYear, Semester, and Bucket Group for detailed memo
    grouped = student_data.groupby(['AcademicYear', 'Semester', 'Bucket Group'])

    # Prepare memo data
    memo_data = []
    for (year, sem, bucket), group in grouped:
        courses = group[['CourseCode', 'LTPS', 'CourseDesc', 'Course Nature', 'Offered By']].to_dict('records')
        memo_data.append({
            'AcademicYear': year,
            'Semester': sem,
            'Bucket Group': bucket,
            'Courses': courses
        })

    # Calculate course count per Bucket Group
    bucket_counts = student_data.groupby('Bucket Group').size().reset_index(name='Course Count').to_dict('records')

    return student_name, memo_data, bucket_counts, None

# Generate student report
def generate_report(roll_no):
    df = load_report_data()
    if df is None:
        return None, "Error: studentcgpa_data.csv file is missing, empty, or has missing columns."

    roll_no = str(roll_no).strip()
    student_data = df[df['Roll No'].astype(str) == roll_no].to_dict('records')
    app.logger.debug(f"Searching for Roll No: '{roll_no}'")
    if not student_data:
        return None, f"No student found with Roll No: {roll_no}."

    student = student_data[0]
    student['Not Declared Courses'] = (
        student['Not Declared Courses'].split('||')
        if 'Not Declared Courses' in student and pd.notna(student['Not Declared Courses'])
        else []
    )
    student['Backlog Details'] = (
        student['Backlog Details'].split('||')
        if 'Backlog Details' in student and pd.notna(student['Backlog Details'])
        else []
    )
    app.logger.debug(f"Found student: {student['Name']}")
    return student, None

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/memo', methods=['GET', 'POST'])
def memo():
    student_name = None
    memo_data = None
    bucket_counts = None
    error = None

    if request.method == 'POST':
        student_id = request.form.get('student_id')
        app.logger.debug(f"Received University ID: {student_id}")
        student_name, memo_data, bucket_counts, error = generate_memo(student_id)

    return render_template('memo.html', student_name=student_name, memo_data=memo_data, bucket_counts=bucket_counts, error=error)

@app.route('/report', methods=['GET', 'POST'])
def report():
    student = None
    error_message = None
    if request.method == 'POST':
        roll_no = request.form.get('roll_no')
        student, error_message = generate_report(roll_no)
    return render_template('report.html', student=student, error_message=error_message)

if __name__ == '__main__':
    app.run()