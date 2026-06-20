import random

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from models import Certificate, User, db

auth_bp = Blueprint('auth', __name__)


def _make_student_id():
    sid = 'STU' + str(random.randint(10000, 99999))
    while User.query.filter_by(student_id=sid).first():
        sid = 'STU' + str(random.randint(10000, 99999))
    return sid


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()
        if user and user.is_active and user.check_password(password):
            session['user_id'] = user.id
            session['role'] = user.role
            session['full_name'] = user.full_name
            flash(f'Welcome back, {user.full_name.split()[0]}.', 'success')
            return redirect(url_for('admin.dashboard' if user.role == 'admin' else 'student.dashboard'))
        flash('That username and password don\'t match our records.', 'danger')
    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been signed out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        phone = request.form.get('phone', '').strip()

        error = None
        if not all([full_name, email, username, password]):
            error = 'Please fill out every required field.'
        elif len(password) < 4:
            error = 'Choose a password with at least 4 characters.'
        elif password != confirm:
            error = 'Your passwords don\'t match.'
        elif User.query.filter_by(username=username).first():
            error = 'That username is already taken.'
        elif User.query.filter_by(email=email).first():
            error = 'That email is already registered.'

        if error:
            flash(error, 'danger')
            return render_template('register.html', form=request.form)

        user = User(full_name=full_name, email=email, username=username,
                    phone=phone, role='student', student_id=_make_student_id())
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        db.session.add(Certificate(student_user_id=user.id))
        db.session.commit()

        flash(f'You\'re enrolled. Your student ID is {user.student_id} — log in to get started.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html')
