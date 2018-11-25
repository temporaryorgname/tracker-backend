from flask import render_template
from flask import Blueprint
from flask import request
from flask import current_app as app
from flask_login import login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

import datetime
import json
import os
from PIL import Image
import base64
from io import BytesIO

import os

from fitnessapp import database

user_bp = Blueprint('user', __name__)

@user_bp.route('/user/<user_id>', methods=['GET'])
@login_required
def get_user(user_id):
    user_id = int(user_id);
    user = database.User.query \
            .filter_by(id=user_id) \
            .first()

    if user is None:
        return json.dumps({
            'error': 'No user matching ID '+str(user_id)
        }), 400

    if user_id == current_user.get_id():
        return json.dumps({
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'verified_email': user.verified_email,
            'last_activity': user.last_activity
        }), 200
    else:
        return json.dumps({
            'id': user.id,
            'name': user.name,
            'last_activity': user.last_activity
        }), 200

