import pandas as pd
import os


# Function to load and clean the CSV data
def load_file_data():
    pass


def load_data():
    csv_path = 'attendance31july.csv'
    if not os.path.exists(csv_path):
        # Placeholder for embedded CSV data
        with open(csv_path, 'w') as f:
            f.write(load_file_data())
    df = pd.read_csv(csv_path, dtype=str)
    # Clean data
    df.fillna({'student_name': 'Unknown', 'counselorname': 'Unknown', 'counselorcontact': 'Unknown'}, inplace=True)
    numeric_cols = ['cgpa', 'backlogs', 'totalclassesconducted', 'totalclassesattended', 'attendance_percentage']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df


# Function to filter students by attendance threshold
def filter_by_attendance(df, threshold):
    filtered_df = df[df['attendance_percentage'] < threshold][
        ['student_uni_id', 'student_name', 'coursename', 'attendance_percentage']]
    return filtered_df


# Main function to process and output results
def main():
    # Load data
    df = load_data()

    # Define attendance thresholds
    thresholds = [85, 75, 65]

    # Process each threshold
    for threshold in thresholds:
        print(f"\nStudents with Attendance < {threshold}%:")
        print("=" * 50)
        filtered_df = filter_by_attendance(df, threshold)

        if filtered_df.empty:
            print(f"No students found with attendance below {threshold}%.")
        else:
            # Display results
            for _, row in filtered_df.iterrows():
                print(f"Student ID: {row['student_uni_id']}, Name: {row['student_name']}, "
                      f"Course: {row['coursename']}, Attendance: {row['attendance_percentage']}%")

            # Export to CSV
            output_file = f'students_below_{threshold}_percent.csv'
            filtered_df.to_csv(output_file, index=False)
            print(f"\nResults exported to {output_file}")

        print("\n" + "=" * 50)


if __name__ == '__main__':
    main()
