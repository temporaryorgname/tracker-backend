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

import os

from fitnessapp import database

body_bp = Blueprint('body', __name__)

@body_bp.route('/body/weight', methods=['GET'])
@login_required
def get_bodyweights():
    weights = database.Bodyweight.query \
            .filter_by(user_id=current_user.get_id()) \
            .order_by(database.Bodyweight.date.desc()) \
            .order_by(database.Bodyweight.time.desc()) \
            .all()
    return json.dumps([{
        'date': str(w.date),
        'time': str(w.time) if w.time is not None else '',
        'bodyweight': float(w.bodyweight)
    } for w in weights]), 200


@body_bp.route('/body/weight', methods=['PUT', 'POST'])
@login_required
def new_bodyweights():
    data = request.get_json()
    print(data)
    bw = database.Bodyweight()

    try:
        bw.bodyweight = float(data['bodyweight'])
    except:
        return json.dumps({
            'error': 'No valid bodyweight provided.'
        }), 400
    if 'date' in data:
        bw.date = data['date']
    else:
        return json.dumps({
            'error': 'No valid date provided.'
        }), 400
    if 'time' in data:
        bw.time= data['time']

    bw.user_id = current_user.get_id()

    database.db_session.add(bw)
    database.db_session.flush()
    database.db_session.commit()

    return 'Body weight added successfully.', 200
