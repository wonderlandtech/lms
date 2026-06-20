from datetime import datetime

from flask import Flask, redirect, render_template, session, url_for

from admin_routes import admin_bp
from auth import auth_bp
from config import Config
from models import User, db
from student_routes import student_bp


def seed_admin():
    if not User.query.filter_by(role='admin').first():
        admin = User(username='admin', email='admin@lms.local', full_name='Administrator', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(student_bp, url_prefix='/student')

    @app.context_processor
    def inject_globals():
        return {'current_year': datetime.utcnow().year}

    @app.route('/')
    def index():
        if 'user_id' in session:
            return redirect(url_for('admin.dashboard' if session.get('role') == 'admin'
                                     else 'student.dashboard'))
        return render_template('home.html')

    with app.app_context():
        db.create_all()
        seed_admin()

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
