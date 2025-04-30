from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class Admin(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Lecturer(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    courses = db.relationship('Course', backref='lecturer', lazy=True, cascade='all, delete-orphan')

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    section = db.Column(db.String(10), nullable=False)
    lecturer_id = db.Column(db.Integer, db.ForeignKey('lecturer.id', ondelete='CASCADE'), nullable=False)
    students = db.relationship('Student', backref='course', lazy=True, cascade='all, delete-orphan')

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    roll_number = db.Column(db.String(20), nullable=False)
    unique_id = db.Column(db.String(20), unique=True, nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id', ondelete='CASCADE'), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    section = db.Column(db.String(10), nullable=False)
    attendances = db.relationship('Attendance', backref='student', lazy=True, cascade='all, delete-orphan')

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id', ondelete='CASCADE'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id', ondelete='CASCADE'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    time = db.Column(db.Time, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(10), nullable=False, default='present')
    method = db.Column(db.String(10), nullable=False, default='auto')