import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'classroom-ledger-dev-key-change-me')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'lms.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
