import random
import string
from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


def generate_code(prefix, length=8):
    chars = string.ascii_uppercase + string.digits
    return prefix + '-' + ''.join(random.choices(chars, k=length))


class User(db.Model):
    """A person in the system — either an admin/instructor or a student."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student')  # 'admin' or 'student'
    student_id = db.Column(db.String(20), unique=True, nullable=True)
    phone = db.Column(db.String(30))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    attendances = db.relationship(
        'Attendance', backref='student', cascade='all, delete-orphan',
        foreign_keys='Attendance.student_user_id')
    assignment_submissions = db.relationship(
        'AssignmentSubmission', backref='student', cascade='all, delete-orphan')
    project_submissions = db.relationship(
        'ProjectSubmission', backref='student', cascade='all, delete-orphan')
    certificate = db.relationship(
        'Certificate', backref='student', uselist=False, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class ClassSession(db.Model):
    """A single class meeting on which attendance is recorded."""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    attendances = db.relationship('Attendance', backref='session', cascade='all, delete-orphan')


class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('class_session.id'), nullable=False)
    student_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='present')  # present, absent, late
    marked_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('session_id', 'student_user_id', name='uq_session_student'),)


class ClassLink(db.Model):
    """A link to a recorded or live class (video, meeting room, etc.)."""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    url = db.Column(db.String(500), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)


class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    deadline = db.Column(db.DateTime, nullable=False)
    max_score = db.Column(db.Integer, default=100)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    submissions = db.relationship('AssignmentSubmission', backref='assignment', cascade='all, delete-orphan')


class AssignmentSubmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), nullable=False)
    student_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text)  # written answer and/or a link to work
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    score = db.Column(db.Integer)
    feedback = db.Column(db.Text)
    status = db.Column(db.String(20), default='submitted')  # submitted, graded

    __table_args__ = (db.UniqueConstraint('assignment_id', 'student_user_id', name='uq_assignment_student'),)


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    deadline = db.Column(db.DateTime, nullable=False)
    allow_group = db.Column(db.Boolean, default=True)
    allow_individual = db.Column(db.Boolean, default=True)
    max_group_size = db.Column(db.Integer, default=4)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    submissions = db.relationship('ProjectSubmission', backref='project', cascade='all, delete-orphan')


class ProjectSubmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    student_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # who submitted it
    submission_type = db.Column(db.String(20), nullable=False)  # 'group' or 'individual'
    group_name = db.Column(db.String(150))
    group_members = db.Column(db.Text)  # free-text list of teammate names
    content = db.Column(db.Text)  # description and/or link to the work
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    score = db.Column(db.Integer)
    feedback = db.Column(db.Text)
    status = db.Column(db.String(20), default='submitted')

    __table_args__ = (db.UniqueConstraint('project_id', 'student_user_id', name='uq_project_student'),)


class Certificate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    course_name = db.Column(db.String(150), default='Course Completion')
    status = db.Column(db.String(20), default='not_requested')  # not_requested, pending, approved, rejected
    certificate_code = db.Column(db.String(50), unique=True)
    requested_at = db.Column(db.DateTime)
    approved_at = db.Column(db.DateTime)
    approved_by = db.Column(db.String(120))
    remarks = db.Column(db.Text)
