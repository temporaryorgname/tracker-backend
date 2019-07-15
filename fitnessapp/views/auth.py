import flask
from flask import render_template
from flask import Blueprint
from flask import request
from flask import session
import flask_login
from flask_login import login_required, current_user, login_user

import json
import bcrypt

import tracker_database as database

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data['email']
    session.permanent = False
    if 'permanent' in data:
        permanent = data['permanent']
        session.permanent = permanent
    user = database.User.query.filter_by(email=email).first()
    if user is None:
        return json.dumps({'error': "Incorrect email/password"}), 403
    if bcrypt.checkpw(data['password'].encode('utf-8'), user.password.tobytes()):
        flask_login.login_user(user)
        print("successful login")
        return json.dumps(user.id), 200
    print("failed login")
    return json.dumps({'error': 'Bad login'}), 403

@auth_bp.route('/current_session', methods=['GET'])
def get_current_session():
    try:
        print(current_user)
        if current_user.get_id() is not None:
            return "%s" % current_user.get_id(), 200
    except:
        pass
    return "{}", 200

@auth_bp.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    flask_login.logout_user()
    return '{}', 200
