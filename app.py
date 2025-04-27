from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, Admin, Lecturer, Course, Student, Attendance
import qrcode
import cv2
import os
from datetime import datetime, timedelta
import io
import random
from flask_migrate import Migrate

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Change this in production
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    # Try to load admin first, then lecturer
    admin = Admin.query.get(int(user_id))
    if admin:
        return admin
    return Lecturer.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user_type = request.form.get('user_type')

        if not all([email, password, user_type]):
            flash('Please fill in all fields')
            return render_template('login.html')

        user = None
        if user_type == 'admin':
            user = Admin.query.filter_by(email=email).first()
            if not user:
                flash('Admin account not found')
                return render_template('login.html')
        else:
            user = Lecturer.query.filter_by(email=email).first()
            if not user:
                flash('Lecturer account not found')
                return render_template('login.html')

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid password')
            
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    if isinstance(current_user, Admin):
        lecturers = Lecturer.query.all()
        courses = Course.query.all()
        return render_template('dashboard.html', lecturers=lecturers, courses=courses, is_admin=True)
    else:
        # For lecturers, only show their assigned courses
        courses = Course.query.filter_by(lecturer_id=current_user.id).all()
        return render_template('dashboard.html', courses=courses, is_admin=False)

@app.route('/scan/<int:course_id>')
@login_required
def scan(course_id):
    course = Course.query.get_or_404(course_id)
    if isinstance(current_user, Lecturer) and course.lecturer_id != current_user.id:
        flash('Unauthorized access')
        return redirect(url_for('dashboard'))
    return render_template('scan.html', course=course)

@app.route('/mark_attendance', methods=['POST'])
@login_required
def mark_attendance():
    student_id = request.form.get('student_id')
    course_id = request.form.get('course_id')
    
    student = Student.query.filter_by(unique_id=student_id).first()
    if not student:
        return {'status': 'error', 'message': 'Student not found'}
    
    # Check if attendance already marked for today
    today = datetime.now().date()
    existing_attendance = Attendance.query.filter_by(
        student_id=student.id,
        course_id=course_id,
        date=today
    ).first()
    
    if existing_attendance:
        return {'status': 'error', 'message': 'Attendance already marked'}
    
    attendance = Attendance(
        student_id=student.id,
        course_id=course_id,
        date=today,
        time=datetime.now().time(),
        method='auto'
    )
    db.session.add(attendance)
    db.session.commit()
    
    return {'status': 'success', 'message': 'Attendance marked successfully'}

@app.route('/manual_attendance')
@login_required
def manual_attendance():
    if isinstance(current_user, Lecturer):
        courses = Course.query.filter_by(lecturer_id=current_user.id).all()
    else:
        courses = Course.query.all()
    return render_template('manual_attendance.html', courses=courses)

@app.route('/reports')
@login_required
def reports():
    if isinstance(current_user, Lecturer):
        courses = Course.query.filter_by(lecturer_id=current_user.id).all()
    else:
        courses = Course.query.all()
    return render_template('reports.html', courses=courses)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

def create_qr_code(student_id):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(student_id)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img_path = f"static/images/qr_{student_id}.png"
    img.save(img_path)
    return img_path

@app.route('/get_attendance_report')
@login_required
def get_attendance_report():
    course_id = request.args.get('course_id')
    date_range = request.args.get('date_range')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    course = Course.query.get_or_404(course_id)
    if isinstance(current_user, Lecturer) and course.lecturer_id != current_user.id:
        return {'error': 'Unauthorized'}, 403

    # Calculate date range
    today = datetime.now().date()
    if date_range == 'today':
        start_date = end_date = today
    elif date_range == 'week':
        start_date = today - timedelta(days=today.weekday())
        end_date = today
    elif date_range == 'month':
        start_date = today.replace(day=1)
        end_date = today
    else:  # custom range
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

    # Get attendance data
    attendance_records = Attendance.query.join(Student).filter(
        Attendance.course_id == course_id,
        Attendance.date >= start_date,
        Attendance.date <= end_date
    ).all()

    # Calculate statistics
    total_students = Student.query.filter_by(course_id=course_id).count()
    present_today = Attendance.query.filter_by(
        course_id=course_id,
        date=today,
        status='present'
    ).count()
    
    attendance_rate = (present_today / total_students * 100) if total_students > 0 else 0

    # Prepare daily trend data
    daily_counts = {}
    current_date = start_date
    while current_date <= end_date:
        daily_counts[current_date.strftime('%Y-%m-%d')] = 0
        current_date += timedelta(days=1)

    for record in attendance_records:
        if record.status == 'present':
            date_str = record.date.strftime('%Y-%m-%d')
            daily_counts[date_str] = daily_counts.get(date_str, 0) + 1

    # Prepare attendance list
    attendance_list = [{
        'student_id': record.student.unique_id,
        'name': record.student.name,
        'date': record.date.strftime('%Y-%m-%d'),
        'time': record.time.strftime('%H:%M'),
        'status': record.status
    } for record in attendance_records]

    return {
        'total_students': total_students,
        'present_today': present_today,
        'attendance_rate': round(attendance_rate, 1),
        'daily_trend': {
            'dates': list(daily_counts.keys()),
            'counts': list(daily_counts.values())
        },
        'attendance_list': attendance_list
    }

@app.route('/export_attendance_report')
@login_required
def export_attendance_report():
    import pandas as pd
    
    course_id = request.args.get('course_id')
    date_range = request.args.get('date_range')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    # Reuse the same date range logic from get_attendance_report
    today = datetime.now().date()
    if date_range == 'today':
        start_date = end_date = today
    elif date_range == 'week':
        start_date = today - timedelta(days=today.weekday())
        end_date = today
    elif date_range == 'month':
        start_date = today.replace(day=1)
        end_date = today
    else:  # custom range
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

    # Get attendance data
    attendance_records = Attendance.query.join(Student).filter(
        Attendance.course_id == course_id,
        Attendance.date >= start_date,
        Attendance.date <= end_date
    ).all()

    # Convert to DataFrame
    data = [{
        'Student ID': record.student.unique_id,
        'Name': record.student.name,
        'Date': record.date.strftime('%Y-%m-%d'),
        'Time': record.time.strftime('%H:%M'),
        'Status': record.status,
        'Method': record.method
    } for record in attendance_records]

    df = pd.DataFrame(data)
    
    # Create the response
    output = io.BytesIO()
    df.to_csv(output, index=False)
    output.seek(0)
    
    return send_file(
        output,
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'attendance_report_{start_date}_to_{end_date}.csv'
    )

@app.route('/manage_students/<int:course_id>', methods=['GET', 'POST'])
@login_required
def manage_students(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Check if user has permission for this course
    if not isinstance(current_user, Admin) and course.lecturer_id != current_user.id:
        flash('Unauthorized access')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        roll_number = request.form.get('roll_number')
        year = course.year
        section = course.section
        
        # Check if roll number already exists in this course
        existing_student = Student.query.filter_by(
            course_id=course_id, 
            roll_number=roll_number
        ).first()
        
        if existing_student:
            flash('Roll number already exists in this course')
            return redirect(url_for('manage_students', course_id=course_id))
        
        # Generate unique student ID: YEAR + SECTION + ROLL_NUMBER + COURSE_ID
        unique_id = f"{year}{section}{roll_number}{course_id}"
                
        student = Student(
            name=name,
            roll_number=roll_number,
            unique_id=unique_id,
            course_id=course_id,
            year=year,
            section=section
        )
        db.session.add(student)
        db.session.commit()
        
        # Generate QR code
        create_qr_code(unique_id)
        flash(f'Student added successfully. ID: {unique_id}')
        
    students = Student.query.filter_by(course_id=course_id).all()
    return render_template('manage_students.html', course=course, students=students)

@app.route('/manage_lecturers', methods=['GET', 'POST'])
@login_required
def manage_lecturers():
    try:
        if not isinstance(current_user, Admin):
            flash('Unauthorized access - Admin only', 'error')
            return redirect(url_for('dashboard'))
        
        if request.method == 'POST':
            try:
                name = request.form.get('name')
                email = request.form.get('email')
                department = request.form.get('department')
                
                # Validate input
                if not all([name, email, department]):
                    flash('All fields are required', 'error')
                    return redirect(url_for('manage_lecturers'))
                
                # Check if email already exists
                existing_lecturer = Lecturer.query.filter_by(email=email).first()
                if existing_lecturer:
                    flash('Email already registered', 'error')
                    return redirect(url_for('manage_lecturers'))
                
                password = generate_password_hash('lecturer123')  # Default password
                lecturer = Lecturer(
                    name=name,
                    email=email,
                    password=password,
                    department=department
                )
                
                db.session.add(lecturer)
                db.session.commit()
                flash('Lecturer added successfully', 'success')
                
            except Exception as e:
                db.session.rollback()
                flash(f'Error adding lecturer: {str(e)}', 'error')
                app.logger.error(f'Error adding lecturer: {str(e)}')
        
        lecturers = Lecturer.query.all()
        return render_template('manage_lecturers.html', lecturers=lecturers)
    
    except Exception as e:
        app.logger.error(f'Error in manage_lecturers: {str(e)}')
        flash('An unexpected error occurred', 'error')
        return redirect(url_for('dashboard'))

@app.route('/edit_lecturer/<int:lecturer_id>', methods=['GET', 'POST'])
@login_required
def edit_lecturer(lecturer_id):
    if not isinstance(current_user, Admin):
        flash('Unauthorized access', 'error')
        return redirect(url_for('dashboard'))

    lecturer = Lecturer.query.get_or_404(lecturer_id)

    if request.method == 'POST':
        try:
            lecturer.name = request.form.get('name')
            new_email = request.form.get('email')
            
            # Check if email is being changed and if it's already in use
            if new_email != lecturer.email:
                existing_lecturer = Lecturer.query.filter_by(email=new_email).first()
                if existing_lecturer:
                    flash('Email already in use by another lecturer', 'error')
                    return render_template('edit_lecturer.html', lecturer=lecturer)
                lecturer.email = new_email

            lecturer.department = request.form.get('department')
            
            # Update password only if provided
            new_password = request.form.get('password')
            if new_password:
                lecturer.password = generate_password_hash(new_password)

            db.session.commit()
            flash('Lecturer updated successfully', 'success')
            return redirect(url_for('manage_lecturers'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating lecturer: {str(e)}', 'error')
            return render_template('edit_lecturer.html', lecturer=lecturer)

    return render_template('edit_lecturer.html', lecturer=lecturer)

@app.route('/delete_lecturer/<int:lecturer_id>')
@login_required
def delete_lecturer(lecturer_id):
    if not isinstance(current_user, Admin):
        flash('Unauthorized access')
        return redirect(url_for('dashboard'))
        
    lecturer = Lecturer.query.get_or_404(lecturer_id)
    db.session.delete(lecturer)
    db.session.commit()
    flash('Lecturer deleted successfully')
    return redirect(url_for('manage_lecturers'))

@app.route('/delete_student/<int:student_id>')
@login_required
def delete_student(student_id):
    student = Student.query.get_or_404(student_id)
    course_id = student.course_id
    
    if not isinstance(current_user, Admin) and student.course.lecturer_id != current_user.id:
        flash('Unauthorized access')
        return redirect(url_for('dashboard'))
        
    db.session.delete(student)
    db.session.commit()
    flash('Student deleted successfully')
    return redirect(url_for('manage_students', course_id=course_id))

@app.route('/edit_student/<int:student_id>', methods=['GET', 'POST'])
@login_required
def edit_student(student_id):
    student = Student.query.get_or_404(student_id)
    
    # Check permissions
    if not isinstance(current_user, Admin) and student.course.lecturer_id != current_user.id:
        flash('Unauthorized access', 'error')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        try:
            student.name = request.form.get('name')
            student.roll_number = request.form.get('roll_number')
            student.year = int(request.form.get('year'))
            student.section = request.form.get('section')
            
            # Only admin can change student's course
            if isinstance(current_user, Admin):
                new_course_id = int(request.form.get('course_id'))
                if new_course_id != student.course_id:
                    student.course_id = new_course_id
                    # Update unique_id based on new course
                    course = Course.query.get(new_course_id)
                    student.unique_id = f'{course.year}{course.section}{student.roll_number}'

            db.session.commit()
            flash('Student updated successfully', 'success')
            return redirect(url_for('manage_students', course_id=student.course_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating student: {str(e)}', 'error')

    # Get all courses for admin to choose from
    courses = Course.query.all() if isinstance(current_user, Admin) else None
    return render_template('edit_student.html', 
                         student=student, 
                         courses=courses, 
                         is_admin=isinstance(current_user, Admin))

@app.route('/manage_courses', methods=['GET', 'POST'])
@login_required
def manage_courses():
    if not isinstance(current_user, Admin):
        flash('Unauthorized access', 'error')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        try:
            name = request.form.get('name')
            year = request.form.get('year')
            section = request.form.get('section')
            lecturer_id = request.form.get('lecturer_id')

            course = Course(
                name=name,
                year=int(year),
                section=section,
                lecturer_id=int(lecturer_id)
            )
            db.session.add(course)
            db.session.commit()
            flash('Course added successfully', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding course: {str(e)}', 'error')

    lecturers = Lecturer.query.all()
    courses = Course.query.all()
    return render_template('manage_courses.html', courses=courses, lecturers=lecturers)

@app.route('/edit_course/<int:course_id>', methods=['GET', 'POST'])
@login_required
def edit_course(course_id):
    if not isinstance(current_user, Admin):
        flash('Unauthorized access', 'error')
        return redirect(url_for('dashboard'))

    course = Course.query.get_or_404(course_id)
    lecturers = Lecturer.query.all()

    if request.method == 'POST':
        try:
            course.name = request.form.get('name')
            course.year = int(request.form.get('year'))
            course.section = request.form.get('section')
            course.lecturer_id = int(request.form.get('lecturer_id'))
            
            db.session.commit()
            flash('Course updated successfully', 'success')
            return redirect(url_for('manage_courses'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating course: {str(e)}', 'error')

    return render_template('edit_course.html', course=course, lecturers=lecturers)

@app.route('/delete_course/<int:course_id>')
@login_required
def delete_course(course_id):
    if not isinstance(current_user, Admin):
        flash('Unauthorized access', 'error')
        return redirect(url_for('dashboard'))

    try:
        course = Course.query.get_or_404(course_id)
        db.session.delete(course)
        db.session.commit()
        flash('Course deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting course: {str(e)}', 'error')

    return redirect(url_for('manage_courses'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)