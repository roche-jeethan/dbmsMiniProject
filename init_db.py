from app import app, db
from models import Admin, Lecturer, Course, Student
from werkzeug.security import generate_password_hash
import random

def init_db():
    with app.app_context():
        # Create tables
        db.create_all()

        # Create admin
        admin = Admin(
            email='admin@example.com',
            password=generate_password_hash('admin123')
        )
        db.session.add(admin)

        # Create lecturers
        lecturers = [
            Lecturer(
                name='Dr. John Smith',
                email='john.smith@example.com',
                password=generate_password_hash('lecturer123'),
                department='Computer Science'
            ),
            Lecturer(
                name='Dr. Sarah Johnson',
                email='sarah.johnson@example.com',
                password=generate_password_hash('lecturer123'),
                department='Mathematics'
            )
        ]
        for lecturer in lecturers:
            db.session.add(lecturer)
        
        db.session.commit()

        # Create courses
        courses = [
            Course(
                name='Introduction to Programming',
                year=1,
                section='A',
                lecturer_id=lecturers[0].id
            ),
            Course(
                name='Advanced Mathematics',
                year=2,
                section='B',
                lecturer_id=lecturers[1].id
            )
        ]
        for course in courses:
            db.session.add(course)
        
        db.session.commit()

        # Create students
        for course in courses:
            for i in range(1, 11):  # 10 students per course
                student = Student(
                    name=f'Student {i} - {course.name}',
                    roll_number=f'ROLL{i:03d}',  # Add this line
                    unique_id=f'{course.year}{course.section}{i:03d}',
                    course_id=course.id,
                    year=course.year,
                    section=course.section
                )
                db.session.add(student)
        
        db.session.commit()

if __name__ == '__main__':
    init_db()
    # Add debug statements
    with app.app_context():
        admin = Admin.query.filter_by(email='admin@example.com').first()
        if admin:
            print("\nAdmin account created successfully!")
            print(f"Admin ID: {admin.id}")
            print(f"Admin email: {admin.email}")
        else:
            print("\nWARNING: Admin account was not created!")

    print("\nLogin credentials:")
    print("Admin - Email: admin@example.com, Password: admin123")
    print("Lecturer - Email: john.smith@example.com, Password: lecturer123")
    print("Lecturer - Email: sarah.johnson@example.com, Password: lecturer123")