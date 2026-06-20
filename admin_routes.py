import random
from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from models import (Assignment, AssignmentSubmission, Attendance, Certificate,
                     ClassLink, ClassSession, Project, ProjectSubmission, User,
                     db, generate_code)
from utils import admin_required

admin_bp = Blueprint('admin', __name__)


def _make_student_id():
    sid = 'STU' + str(random.randint(10000, 99999))
    while User.query.filter_by(student_id=sid).first():
        sid = 'STU' + str(random.randint(10000, 99999))
    return sid


# ---------------------------------------------------------------- dashboard
@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    stats = {
        'students': User.query.filter_by(role='student').count(),
        'sessions': ClassSession.query.count(),
        'links': ClassLink.query.count(),
        'assignments': Assignment.query.count(),
        'projects': Project.query.count(),
        'pending_certs': Certificate.query.filter_by(status='pending').count(),
    }
    recent_assignment_subs = (AssignmentSubmission.query
                               .order_by(AssignmentSubmission.submitted_at.desc()).limit(5).all())
    recent_project_subs = (ProjectSubmission.query
                            .order_by(ProjectSubmission.submitted_at.desc()).limit(5).all())
    upcoming_deadlines = sorted(
        [(a.title, a.deadline, 'Assignment') for a in Assignment.query.all() if a.deadline >= datetime.utcnow()] +
        [(p.title, p.deadline, 'Project') for p in Project.query.all() if p.deadline >= datetime.utcnow()],
        key=lambda x: x[1]
    )[:5]
    return render_template('admin/dashboard.html', stats=stats,
                            recent_assignment_subs=recent_assignment_subs,
                            recent_project_subs=recent_project_subs,
                            upcoming_deadlines=upcoming_deadlines)


# ---------------------------------------------------------------- students
@admin_bp.route('/students')
@admin_required
def students():
    q = request.args.get('q', '').strip()
    query = User.query.filter_by(role='student')
    if q:
        like = f'%{q}%'
        query = query.filter(db.or_(User.full_name.ilike(like), User.username.ilike(like),
                                     User.student_id.ilike(like), User.email.ilike(like)))
    roster = query.order_by(User.full_name).all()
    return render_template('admin/students.html', students=roster, q=q)


@admin_bp.route('/students/add', methods=['GET', 'POST'])
@admin_required
def add_student():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        username = request.form.get('username', '').strip()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '').strip() or 'student123'

        error = None
        if not all([full_name, email, username]):
            error = 'Full name, email and username are required.'
        elif User.query.filter_by(username=username).first():
            error = 'That username already exists.'
        elif User.query.filter_by(email=email).first():
            error = 'That email is already registered.'

        if error:
            flash(error, 'danger')
            return render_template('admin/student_form.html', form=request.form, mode='add')

        user = User(full_name=full_name, email=email, username=username, phone=phone,
                    role='student', student_id=_make_student_id())
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        db.session.add(Certificate(student_user_id=user.id))
        db.session.commit()
        flash(f'Enrolled {full_name} — ID {user.student_id}, username "{username}", password "{password}".',
              'success')
        return redirect(url_for('admin.students'))
    return render_template('admin/student_form.html', mode='add')


@admin_bp.route('/students/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_student(user_id):
    student = User.query.filter_by(id=user_id, role='student').first_or_404()
    if request.method == 'POST':
        student.full_name = request.form.get('full_name', '').strip()
        student.email = request.form.get('email', '').strip()
        student.phone = request.form.get('phone', '').strip()
        new_password = request.form.get('password', '').strip()
        if new_password:
            student.set_password(new_password)
        db.session.commit()
        flash('Student record updated.', 'success')
        return redirect(url_for('admin.students'))
    return render_template('admin/student_form.html', student=student, mode='edit')


@admin_bp.route('/students/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_student(user_id):
    student = User.query.filter_by(id=user_id, role='student').first_or_404()
    db.session.delete(student)
    db.session.commit()
    flash('Student removed from the roster.', 'info')
    return redirect(url_for('admin.students'))


@admin_bp.route('/students/<int:user_id>/toggle', methods=['POST'])
@admin_required
def toggle_student(user_id):
    student = User.query.filter_by(id=user_id, role='student').first_or_404()
    student.is_active = not student.is_active
    db.session.commit()
    flash(f'{student.full_name} is now {"active" if student.is_active else "suspended"}.', 'info')
    return redirect(url_for('admin.students'))


# ---------------------------------------------------------------- attendance
@admin_bp.route('/attendance')
@admin_required
def attendance_sessions():
    sessions = ClassSession.query.order_by(ClassSession.date.desc()).all()
    return render_template('admin/attendance.html', sessions=sessions)


@admin_bp.route('/attendance/new', methods=['GET', 'POST'])
@admin_required
def new_session():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        date_str = request.form.get('date')
        notes = request.form.get('notes', '').strip()
        if not title or not date_str:
            flash('Give the session a title and a date.', 'danger')
            return redirect(url_for('admin.new_session'))
        cs = ClassSession(title=title, date=datetime.strptime(date_str, '%Y-%m-%d').date(), notes=notes)
        db.session.add(cs)
        db.session.commit()
        flash('Session created — mark who showed up below.', 'success')
        return redirect(url_for('admin.mark_attendance', session_id=cs.id))
    return render_template('admin/session_form.html', today=datetime.utcnow().strftime('%Y-%m-%d'))


@admin_bp.route('/attendance/<int:session_id>/mark', methods=['GET', 'POST'])
@admin_required
def mark_attendance(session_id):
    cs = ClassSession.query.get_or_404(session_id)
    roster = User.query.filter_by(role='student', is_active=True).order_by(User.full_name).all()
    existing = {a.student_user_id: a for a in Attendance.query.filter_by(session_id=session_id).all()}

    if request.method == 'POST':
        for student in roster:
            status = request.form.get(f'status_{student.id}', 'absent')
            att = existing.get(student.id)
            if att:
                att.status = status
                att.marked_at = datetime.utcnow()
            else:
                db.session.add(Attendance(session_id=session_id, student_user_id=student.id, status=status))
        db.session.commit()
        flash('Attendance recorded.', 'success')
        return redirect(url_for('admin.attendance_sessions'))

    return render_template('admin/mark_attendance.html', cs=cs, students=roster, existing=existing)


@admin_bp.route('/attendance/<int:session_id>/delete', methods=['POST'])
@admin_required
def delete_session(session_id):
    db.session.delete(ClassSession.query.get_or_404(session_id))
    db.session.commit()
    flash('Session deleted.', 'info')
    return redirect(url_for('admin.attendance_sessions'))


# ---------------------------------------------------------------- class links
@admin_bp.route('/links')
@admin_required
def links():
    return render_template('admin/links.html', links=ClassLink.query.order_by(ClassLink.date_added.desc()).all())


@admin_bp.route('/links/add', methods=['GET', 'POST'])
@admin_required
def add_link():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        url = request.form.get('url', '').strip()
        description = request.form.get('description', '').strip()
        if not title or not url:
            flash('A title and a URL are both required.', 'danger')
            return redirect(url_for('admin.add_link'))
        db.session.add(ClassLink(title=title, url=url, description=description))
        db.session.commit()
        flash('Class link published.', 'success')
        return redirect(url_for('admin.links'))
    return render_template('admin/link_form.html', mode='add')


@admin_bp.route('/links/<int:link_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_link(link_id):
    link = ClassLink.query.get_or_404(link_id)
    if request.method == 'POST':
        link.title = request.form.get('title', '').strip()
        link.url = request.form.get('url', '').strip()
        link.description = request.form.get('description', '').strip()
        db.session.commit()
        flash('Link updated.', 'success')
        return redirect(url_for('admin.links'))
    return render_template('admin/link_form.html', link=link, mode='edit')


@admin_bp.route('/links/<int:link_id>/delete', methods=['POST'])
@admin_required
def delete_link(link_id):
    db.session.delete(ClassLink.query.get_or_404(link_id))
    db.session.commit()
    flash('Link removed.', 'info')
    return redirect(url_for('admin.links'))


# ---------------------------------------------------------------- assignments
@admin_bp.route('/assignments')
@admin_required
def assignments():
    return render_template('admin/assignments.html',
                            assignments=Assignment.query.order_by(Assignment.deadline.desc()).all(),
                            now=datetime.utcnow())


@admin_bp.route('/assignments/add', methods=['GET', 'POST'])
@admin_required
def add_assignment():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        deadline_str = request.form.get('deadline')
        max_score = request.form.get('max_score', 100)
        if not title or not deadline_str:
            flash('Give the assignment a title and a deadline.', 'danger')
            return redirect(url_for('admin.add_assignment'))
        deadline = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M')
        db.session.add(Assignment(title=title, description=description, deadline=deadline,
                                   max_score=int(max_score or 100)))
        db.session.commit()
        flash('Assignment posted to the class.', 'success')
        return redirect(url_for('admin.assignments'))
    return render_template('admin/assignment_form.html', mode='add')


@admin_bp.route('/assignments/<int:assignment_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_assignment(assignment_id):
    a = Assignment.query.get_or_404(assignment_id)
    if request.method == 'POST':
        a.title = request.form.get('title', '').strip()
        a.description = request.form.get('description', '').strip()
        a.deadline = datetime.strptime(request.form.get('deadline'), '%Y-%m-%dT%H:%M')
        a.max_score = int(request.form.get('max_score') or 100)
        db.session.commit()
        flash('Assignment updated.', 'success')
        return redirect(url_for('admin.assignments'))
    return render_template('admin/assignment_form.html', assignment=a, mode='edit')


@admin_bp.route('/assignments/<int:assignment_id>/delete', methods=['POST'])
@admin_required
def delete_assignment(assignment_id):
    db.session.delete(Assignment.query.get_or_404(assignment_id))
    db.session.commit()
    flash('Assignment removed.', 'info')
    return redirect(url_for('admin.assignments'))


@admin_bp.route('/assignments/<int:assignment_id>/submissions')
@admin_required
def assignment_submissions(assignment_id):
    a = Assignment.query.get_or_404(assignment_id)
    subs = (AssignmentSubmission.query.filter_by(assignment_id=assignment_id)
            .order_by(AssignmentSubmission.submitted_at.desc()).all())
    total_students = User.query.filter_by(role='student', is_active=True).count()
    return render_template('admin/assignment_submissions.html', assignment=a, subs=subs,
                            total_students=total_students)


@admin_bp.route('/submissions/<int:sub_id>/grade', methods=['POST'])
@admin_required
def grade_assignment_submission(sub_id):
    sub = AssignmentSubmission.query.get_or_404(sub_id)
    sub.score = request.form.get('score', type=int)
    sub.feedback = request.form.get('feedback', '').strip()
    sub.status = 'graded'
    db.session.commit()
    flash('Grade saved.', 'success')
    return redirect(url_for('admin.assignment_submissions', assignment_id=sub.assignment_id))


# ---------------------------------------------------------------- projects
@admin_bp.route('/projects')
@admin_required
def projects():
    return render_template('admin/projects.html',
                            projects=Project.query.order_by(Project.deadline.desc()).all(),
                            now=datetime.utcnow())


@admin_bp.route('/projects/add', methods=['GET', 'POST'])
@admin_required
def add_project():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        deadline_str = request.form.get('deadline')
        allow_group = 'allow_group' in request.form
        allow_individual = 'allow_individual' in request.form
        max_group_size = request.form.get('max_group_size') or 4

        if not title or not deadline_str:
            flash('Give the project a title and a deadline.', 'danger')
            return redirect(url_for('admin.add_project'))
        if not allow_group and not allow_individual:
            flash('Allow at least one submission mode — group or individual.', 'danger')
            return redirect(url_for('admin.add_project'))

        deadline = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M')
        db.session.add(Project(title=title, description=description, deadline=deadline,
                                allow_group=allow_group, allow_individual=allow_individual,
                                max_group_size=int(max_group_size)))
        db.session.commit()
        flash('Project posted to the class.', 'success')
        return redirect(url_for('admin.projects'))
    return render_template('admin/project_form.html', mode='add')


@admin_bp.route('/projects/<int:project_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_project(project_id):
    p = Project.query.get_or_404(project_id)
    if request.method == 'POST':
        p.title = request.form.get('title', '').strip()
        p.description = request.form.get('description', '').strip()
        p.deadline = datetime.strptime(request.form.get('deadline'), '%Y-%m-%dT%H:%M')
        p.allow_group = 'allow_group' in request.form
        p.allow_individual = 'allow_individual' in request.form
        p.max_group_size = int(request.form.get('max_group_size') or 4)
        db.session.commit()
        flash('Project updated.', 'success')
        return redirect(url_for('admin.projects'))
    return render_template('admin/project_form.html', project=p, mode='edit')


@admin_bp.route('/projects/<int:project_id>/delete', methods=['POST'])
@admin_required
def delete_project(project_id):
    db.session.delete(Project.query.get_or_404(project_id))
    db.session.commit()
    flash('Project removed.', 'info')
    return redirect(url_for('admin.projects'))


@admin_bp.route('/projects/<int:project_id>/submissions')
@admin_required
def project_submissions(project_id):
    p = Project.query.get_or_404(project_id)
    subs = (ProjectSubmission.query.filter_by(project_id=project_id)
            .order_by(ProjectSubmission.submitted_at.desc()).all())
    return render_template('admin/project_submissions.html', project=p, subs=subs)


@admin_bp.route('/project_submissions/<int:sub_id>/grade', methods=['POST'])
@admin_required
def grade_project_submission(sub_id):
    sub = ProjectSubmission.query.get_or_404(sub_id)
    sub.score = request.form.get('score', type=int)
    sub.feedback = request.form.get('feedback', '').strip()
    sub.status = 'graded'
    db.session.commit()
    flash('Grade saved.', 'success')
    return redirect(url_for('admin.project_submissions', project_id=sub.project_id))


# ---------------------------------------------------------------- certificates
@admin_bp.route('/certificates')
@admin_required
def certificates():
    certs = Certificate.query.join(User).order_by(Certificate.status.desc(), User.full_name).all()
    return render_template('admin/certificates.html', certs=certs)


@admin_bp.route('/certificates/<int:cert_id>/approve', methods=['POST'])
@admin_required
def approve_certificate(cert_id):
    cert = Certificate.query.get_or_404(cert_id)
    cert.status = 'approved'
    cert.certificate_code = generate_code('CERT')
    cert.approved_at = datetime.utcnow()
    cert.approved_by = session.get('full_name', 'Administrator')
    cert.remarks = None
    db.session.commit()
    flash(f'Certificate approved for {cert.student.full_name}.', 'success')
    return redirect(url_for('admin.certificates'))


@admin_bp.route('/certificates/<int:cert_id>/reject', methods=['POST'])
@admin_required
def reject_certificate(cert_id):
    cert = Certificate.query.get_or_404(cert_id)
    cert.status = 'rejected'
    cert.remarks = request.form.get('remarks', '').strip()
    db.session.commit()
    flash('Certificate request declined.', 'info')
    return redirect(url_for('admin.certificates'))
