from flask import Flask, request, render_template, redirect, url_for, flash
import pandas as pd
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

ATTENDANCE_CSV = 'attendance31july.csv'
MEMO_CSV = 'student_data.csv'

# Load attendance data
df = pd.read_csv('attendance31july.csv')

def load_attendance_data():
    if not os.path.exists(ATTENDANCE_CSV):
        return None
    return pd.read_csv(ATTENDANCE_CSV)


# Load memo data
def load_memo_data():
    try:
        if not os.path.exists(MEMO_CSV):
            raise FileNotFoundError(f"CSV file not found at {MEMO_CSV}")
        df = pd.read_csv(MEMO_CSV, delimiter=',', encoding='utf-8')
        app.logger.debug(f"Loaded {len(df)} records from CSV")
        app.logger.debug(f"Unique University IDs: {df['University ID'].astype(str).str.strip().unique()}")
        return df
    except Exception as e:
        app.logger.error(f"Error loading CSV: {e}")
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

    # Extract CourseCode prefix (remove last character if L, T, P, S)
    student_data = student_data.copy()
    student_data['CourseCodePrefix'] = student_data['CourseCode'].str[:-1].where(
        student_data['CourseCode'].str[-1].isin(['L', 'T', 'P', 'S']),
        student_data['CourseCode']
    )

    # Group by AcademicYear, Semester, and CourseCodePrefix
    grouped = student_data.groupby(['AcademicYear', 'Semester', 'CourseCodePrefix'])

    # Prepare memo data
    memo_data = []
    for (year, sem, course_prefix), group in grouped:
        # Combine LTPS, CourseDesc, Course Nature, Offered By, and Bucket Group for all components
        components = group[['CourseCode', 'LTPS', 'CourseDesc', 'Course Nature', 'Offered By', 'Bucket Group']].to_dict(
            'records')
        # Use the first component's details for display
        first_component = components[0]
        memo_data.append({
            'AcademicYear': year,
            'Semester': sem,
            'Courses': [{
                'CourseCode': course_prefix,
                'LTPS': ', '.join(c['LTPS'] for c in components),
                'CourseDesc': first_component['CourseDesc'],
                'Course Nature': first_component['Course Nature'],
                'Offered By': first_component['Offered By'],
                'Bucket Group': first_component['Bucket Group']
            }]
        })

    # Group memo_data by AcademicYear and Semester for display
    grouped_memo = {}
    for item in memo_data:
        key = (item['AcademicYear'], item['Semester'])
        if key not in grouped_memo:
            grouped_memo[key] = {
                'AcademicYear': item['AcademicYear'],
                'Semester': item['Semester'],
                'Courses': []
            }
        grouped_memo[key]['Courses'].extend(item['Courses'])

    memo_data = list(grouped_memo.values())

    # Calculate course count per Bucket Group based on unique CourseCodePrefix
    bucket_counts = student_data.groupby('Bucket Group')['CourseCodePrefix'].nunique().reset_index(
        name='Course Count').to_dict('records')

    return student_name, memo_data, bucket_counts, None




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

    return render_template('memo.html',  student_name=student_name, memo_data=memo_data, bucket_counts=bucket_counts,
                           error=error)
@app.route('/report', methods=['GET', 'POST'])
def report():
    if request.method == 'POST':
        attendance_df = load_attendance_data()
        if attendance_df is None:
            flash("Attendance data file not found.", 'danger')
            return redirect(url_for('report'))

        student_id = request.form['student_id']
        try:
            student_data = attendance_df[attendance_df['student_uni_id'] == int(student_id)]
        except ValueError:
            flash(f"Invalid ID format: '{student_id}'", 'danger')
            return redirect(url_for('report'))

        if student_data.empty:
            flash(f"No attendance data found for Student ID: {student_id}", 'warning')
            return redirect(url_for('report'))

        name = student_data['student_name'].iloc[0]
        cgpa = student_data['cgpa'].iloc[0]
        backlogs = student_data['backlogs'].iloc[0]
        councelorname = student_data['counselorname'].iloc[0]
        councelorcontact = student_data['counselorcontact'].iloc[0]
        courses = student_data[[
            'coursecode', 'coursename', 'totalclassesconducted',
            'totalclassesattended', 'attendance_percentage'
        ]].to_dict('records')

        notdeclaredcoursessplit = student_data['notdeclaredcourses'].iloc[0].split("||") if 'notdeclaredcourses' in student_data.columns else []
        backlogdetailssplit = student_data['backlogdetails'].iloc[0].split("||") if 'backlogdetails' in student_data.columns else []

        return render_template('result.html',
                               student_id=student_id,
                               name=name,
                               cgpa=cgpa,
                               backlogs=backlogs,
                               councelorname=councelorname,
                               councelorcontact=councelorcontact,
                               courses=courses,
                               notdeclaredcoursessplit=notdeclaredcoursessplit,
                               backlogdetailssplit=backlogdetailssplit)
    return render_template('search.html')


@app.route('/all_reports')
def all_reports():
    all_students = []

    for _, student_data in df.groupby('student_uni_id'):
        student_info = {
            'student_id': student_data['student_uni_id'].iloc[0],
            'name': student_data['student_name'].iloc[0],
            'cgpa': student_data['cgpa'].iloc[0],
            'Postal_Address': student_data['Postal_Address'].iloc[0],
            'phone': student_data['phone'].iloc[0],

            'backlogs': student_data['backlogs'].iloc[0],
            'councelorname': student_data['counselorname'].iloc[0],
            'councelorcontact': student_data['counselorcontact'].iloc[0],
            'courses': student_data[[
                'coursecode',
                'coursename',
                'totalclassesconducted',
                'totalclassesattended',
                'attendance_percentage'
            ]].to_dict('records'),
            'notdeclaredcoursessplit': student_data['notdeclaredcourses'].iloc[0].split("||") if 'notdeclaredcourses' in student_data.columns and pd.notna(student_data['notdeclaredcourses'].iloc[0]) else 'Not Available',

            'backlogdetailssplit': student_data['backlogdetails'].iloc[0].split(
                "||") if 'backlogdetails' in student_data.columns and pd.notna(
                student_data['backlogdetails'].iloc[0]) else 'No Backlogs'
        }
        all_students.append(student_info)

    return render_template('all_results.html', all_students=all_students)


if __name__ == '__main__':
    app.run()