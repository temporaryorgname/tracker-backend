import flask
from flask import render_template
from flask import Blueprint
from flask import request
import flask_login
from flask_login import login_required, current_user, login_user

import json
import bcrypt

from fitnessapp import database

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    user = database.User()
    user.name = data['name']
    user.email = data['email']
    user.password = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt(12))

    existing_user = database.User.query.filter_by(email=user.email).all()
    if len(existing_user) == 0:
        database.db_session.add(user)
        database.db_session.flush()
        database.db_session.commit()
        return "User created", 200
    else:
        return "User already exists", 400

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data['email']
    user = database.User.query.filter_by(email=email).first()
    if user is None:
        return "Incorrect email/password", 403
    if bcrypt.checkpw(data['password'].encode('utf-8'), user.password.tobytes()):
        flask_login.login_user(user)
        print("successful login")
        return json.dumps('Login successful'), 200
    print("failed login")
    return 'Bad login', 403

@auth_bp.route('/current_session', methods=['GET'])
def get_current_session():
    try:
        print(current_user)
        return "%s" % current_user.get_id(), 200
    except:
        return "None", 200

@auth_bp.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    flask_login.logout_user()
    return 'Logged out'
