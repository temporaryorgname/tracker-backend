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

from fitnessapp import database

food_bp = Blueprint('food', __name__)

@food_bp.route('/food')
@login_required
def get_food(): # TODO: Filter by user
    date = request.args.get('date')
    date = datetime.datetime.strptime(date, '%Y-%m-%d')
    if date is None:
        #foods = database.Food.query.filter_by(user_id=current_user.get_id()).all()
        foods = database.Food.query.order_by(database.Food.date).all()
    else:
        #foods = database.Food.query.filter_by(date=).all()
        foods = database.Food.query \
                .order_by(database.Food.date.desc()) \
                .filter(database.Food.date.between(date,date+datetime.timedelta(days=1))) \
                .all()
    def get_photos(food_id):
        photos = database.FoodPhoto.query \
                .filter_by(food_id = food_id) \
                .all()
        return [p.id for p in photos]
    data = [{
        "id": f.id, 
        "date": str(f.date),
        "itemName": f.name, 
        "quantity": '%s %s'%(f.quantity,f.quantity_unit),
        "calories": str(f.calories),
        "protein": str(f.protein),
        "photos": get_photos(f.id)
    } for f in foods]
    return json.dumps(data), 200

@food_bp.route('/food', methods=['PUT','POST'])
@login_required
def new_food():
    data = request.get_json()

    if 'itemName' not in data:
        return "No item name listed.", 400

    f = database.Food()
    if 'date' in data:
        f.date = data['date']
    else:
        f.date = datetime.datetime.now()
    if 'itemName' in data:
        f.name = data['itemName']
    if 'quantity' in data:
        f.quantity = data['quantity']
    if 'calories' in data:
        f.calories = data['calories']
    if 'protein' in data:
        f.protein = data['protein']
    f.user_id = current_user.get_id()

    database.db_session.add(f)
    database.db_session.flush()
    database.db_session.commit()

    if 'photos' in data:
        for photo_id in data['photos']:
            food_photo = database.FoodPhoto.query \
                .filter("id='%s'" % photo_id) \
                .first() # FIXME: text query needs to be wrapped in a text(), but I don't know where to find it
            food_photo.food_id = f.id
            database.db_session.flush()
            database.db_session.commit()

    return str(f.id),200

@food_bp.route('/food/<food_id>', methods=['PUT','POST'])
@login_required
def update_food(food_id): # TODO: Does not work for numerical values yet
    data = request.get_json()

    if 'itemName' not in data:
        return "No item name listed.", 400

    f = database.Food.query \
            .filter("id='%s'" % food_id) \
            .first()
    if f is None:
        return "ID not found", 404
    if 'date' in data:
        f.date = data['date']
    else:
        f.date = datetime.datetime.now()
    if 'itemName' in data:
        f.name = data['itemName']
    #if 'quantity' in data:
    #    f.quantity = data['quantity']
    #if 'calories' in data:
    #    f.calories = data['calories']
    #if 'protein' in data:
    #    f.protein = data['protein']
    f.user_id = current_user.get_id()

    database.db_session.add(f)
    database.db_session.flush()
    database.db_session.commit()

    if 'photos' in data:
        for photo_id in data['photos']:
            food_photo = database.FoodPhoto.query \
                .filter("id='%s'" % photo_id) \
                .first() # FIXME: text query needs to be wrapped in a text(), but I don't know where to find it
            food_photo.food_id = f.id
            database.db_session.flush()
            database.db_session.commit()

    return str(f.id),200

@food_bp.route('/food/<food_id>', methods=['DELETE'])
@login_required
def delete_food(food_id):
    print("Requesting to delete entry %s." % request.view_args['id'])
    return "",200

@food_bp.route('/food/photo/<int:photo_id>', methods=['GET'])
@login_required
def get_food_photo(photo_id):
    filename = str(photo_id)
    img = Image.open(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    img.thumbnail((32,32))
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue())
    return json.dumps({
        'data': img_str.decode()
    }), 200

@food_bp.route('/food/photo', methods=['PUT','POST'])
@login_required
def add_food_photo():
    # check if the post request has the file part
    print(request.get_json())
    print(request.files)
    if 'file' not in request.files:
        return "No file provided.", 400
    file = request.files['file']

    # if user does not select file, browser also
    # submit an empty part without filename
    if file.filename == '':
        return "No file name.", 400
    if file:
        # Create food entry
        food_photo = database.FoodPhoto()
        food_photo.file_name = ""
        database.db_session.add(food_photo)
        database.db_session.flush()
        database.db_session.commit()
        # Use ID as file name
        food_photo.file_name = food_photo.id
        filename = str(food_photo.file_name)
        # Save file
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        # Save file name
        database.db_session.flush()
        database.db_session.commit()
        return json.dumps({'id': food_photo.id}),200

#@db_bp.route('/bodystats')
#@login_required
#def account():
#    return json.dumps([{"date": "day 1", "weight": 150},
#        {"date": "day 2", "weight": 150},
#        {"date": "day 3", "weight": 150},
#        {"date": "day 4", "weight": 150},
#        {"date": "day 5", "weight": 150}])
