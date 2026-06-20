from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from models import (Assignment, AssignmentSubmission, Attendance, Certificate,
                     ClassLink, ClassSession, Project, ProjectSubmission, User, db)
from utils import student_required

student_bp = Blueprint('student', __name__)


def current_user():
    return User.query.get(session['user_id'])


@student_bp.route('/dashboard')
@student_required
def dashboard():
    user = current_user()
    total_sessions = ClassSession.query.count()
    present_count = Attendance.query.filter_by(student_user_id=user.id, status='present').count()
    attendance_pct = round((present_count / total_sessions) * 100, 1) if total_sessions else 0

    open_assignments = Assignment.query.filter(Assignment.deadline >= datetime.utcnow()).count()
    submitted_assignments = AssignmentSubmission.query.filter_by(student_user_id=user.id).count()
    open_projects = Project.query.filter(Project.deadline >= datetime.utcnow()).count()
    submitted_projects = ProjectSubmission.query.filter_by(student_user_id=user.id).count()

    cert = Certificate.query.filter_by(student_user_id=user.id).first()
    recent_links = ClassLink.query.order_by(ClassLink.date_added.desc()).limit(3).all()

    upcoming = sorted(
        [(a.title, a.deadline, 'assignment', a.id) for a in Assignment.query.all()
         if a.deadline >= datetime.utcnow()] +
        [(p.title, p.deadline, 'project', p.id) for p in Project.query.all()
         if p.deadline >= datetime.utcnow()],
        key=lambda x: x[1]
    )[:5]

    return render_template('student/dashboard.html', user=user, attendance_pct=attendance_pct,
                            total_sessions=total_sessions, present_count=present_count,
                            open_assignments=open_assignments, submitted_assignments=submitted_assignments,
                            open_projects=open_projects, submitted_projects=submitted_projects,
                            cert=cert, recent_links=recent_links, upcoming=upcoming)


@student_bp.route('/attendance')
@student_required
def attendance():
    user = current_user()
    records = (Attendance.query.filter_by(student_user_id=user.id)
               .join(ClassSession).order_by(ClassSession.date.desc()).all())
    total = len(records)
    present = len([r for r in records if r.status == 'present'])
    late = len([r for r in records if r.status == 'late'])
    absent = len([r for r in records if r.status == 'absent'])
    pct = round((present / total) * 100, 1) if total else 0
    return render_template('student/attendance.html', records=records, total=total,
                            present=present, late=late, absent=absent, pct=pct)


@student_bp.route('/links')
@student_required
def links():
    return render_template('student/links.html', links=ClassLink.query.order_by(ClassLink.date_added.desc()).all())


@student_bp.route('/assignments')
@student_required
def assignments():
    user = current_user()
    items = Assignment.query.order_by(Assignment.deadline.asc()).all()
    my_subs = {s.assignment_id: s for s in AssignmentSubmission.query.filter_by(student_user_id=user.id).all()}
    return render_template('student/assignments.html', assignments=items, my_subs=my_subs, now=datetime.utcnow())


@student_bp.route('/assignments/<int:assignment_id>', methods=['GET', 'POST'])
@student_required
def assignment_detail(assignment_id):
    user = current_user()
    a = Assignment.query.get_or_404(assignment_id)
    sub = AssignmentSubmission.query.filter_by(assignment_id=assignment_id, student_user_id=user.id).first()
    is_open = datetime.utcnow() <= a.deadline

    if request.method == 'POST':
        if not is_open:
            flash('This assignment\'s deadline has passed — submissions are closed.', 'danger')
            return redirect(url_for('student.assignment_detail', assignment_id=assignment_id))
        content = request.form.get('content', '').strip()
        if not content:
            flash('Add your answer or a link to your work before submitting.', 'danger')
            return redirect(url_for('student.assignment_detail', assignment_id=assignment_id))
        if sub:
            sub.content = content
            sub.submitted_at = datetime.utcnow()
            sub.status = 'submitted'
        else:
            sub = AssignmentSubmission(assignment_id=assignment_id, student_user_id=user.id, content=content)
            db.session.add(sub)
        db.session.commit()
        flash('Assignment submitted.', 'success')
        return redirect(url_for('student.assignments'))

    return render_template('student/assignment_detail.html', a=a, sub=sub, is_open=is_open)


@student_bp.route('/projects')
@student_required
def projects():
    user = current_user()
    items = Project.query.order_by(Project.deadline.asc()).all()
    my_subs = {s.project_id: s for s in ProjectSubmission.query.filter_by(student_user_id=user.id).all()}
    return render_template('student/projects.html', projects=items, my_subs=my_subs, now=datetime.utcnow())


@student_bp.route('/projects/<int:project_id>', methods=['GET', 'POST'])
@student_required
def project_detail(project_id):
    user = current_user()
    p = Project.query.get_or_404(project_id)
    sub = ProjectSubmission.query.filter_by(project_id=project_id, student_user_id=user.id).first()
    is_open = datetime.utcnow() <= p.deadline

    if request.method == 'POST':
        if not is_open:
            flash('This project\'s deadline has passed — submissions are closed.', 'danger')
            return redirect(url_for('student.project_detail', project_id=project_id))

        submission_type = request.form.get('submission_type')
        content = request.form.get('content', '').strip()
        group_name = request.form.get('group_name', '').strip()
        group_members = request.form.get('group_members', '').strip()

        if submission_type not in ('group', 'individual'):
            flash('Choose whether you\'re submitting as a group or on your own.', 'danger')
            return redirect(url_for('student.project_detail', project_id=project_id))
        if submission_type == 'group' and not p.allow_group:
            flash('Group submissions aren\'t enabled for this project.', 'danger')
            return redirect(url_for('student.project_detail', project_id=project_id))
        if submission_type == 'individual' and not p.allow_individual:
            flash('Individual submissions aren\'t enabled for this project.', 'danger')
            return redirect(url_for('student.project_detail', project_id=project_id))
        if submission_type == 'group' and not group_name:
            flash('Give your group a name.', 'danger')
            return redirect(url_for('student.project_detail', project_id=project_id))
        if not content:
            flash('Describe your work or add a link before submitting.', 'danger')
            return redirect(url_for('student.project_detail', project_id=project_id))

        if sub:
            sub.submission_type = submission_type
            sub.group_name = group_name if submission_type == 'group' else None
            sub.group_members = group_members if submission_type == 'group' else None
            sub.content = content
            sub.submitted_at = datetime.utcnow()
            sub.status = 'submitted'
        else:
            sub = ProjectSubmission(
                project_id=project_id, student_user_id=user.id, submission_type=submission_type,
                group_name=group_name if submission_type == 'group' else None,
                group_members=group_members if submission_type == 'group' else None,
                content=content)
            db.session.add(sub)
        db.session.commit()
        flash('Project submitted.', 'success')
        return redirect(url_for('student.projects'))

    return render_template('student/project_detail.html', p=p, sub=sub, is_open=is_open)


@student_bp.route('/certificate', methods=['GET', 'POST'])
@student_required
def certificate():
    user = current_user()
    cert = Certificate.query.filter_by(student_user_id=user.id).first()
    if not cert:
        cert = Certificate(student_user_id=user.id)
        db.session.add(cert)
        db.session.commit()

    if request.method == 'POST' and cert.status in ('not_requested', 'rejected'):
        cert.status = 'pending'
        cert.requested_at = datetime.utcnow()
        cert.remarks = None
        db.session.commit()
        flash('Certificate requested — your instructor will review it shortly.', 'success')
        return redirect(url_for('student.certificate'))

    return render_template('student/certificate.html', cert=cert, user=user)


@student_bp.route('/certificate/view')
@student_required
def view_certificate():
    user = current_user()
    cert = Certificate.query.filter_by(student_user_id=user.id).first()
    if not cert or cert.status != 'approved':
        flash('Your certificate hasn\'t been approved yet.', 'warning')
        return redirect(url_for('student.certificate'))
    return render_template('student/certificate_view.html', cert=cert, user=user)
