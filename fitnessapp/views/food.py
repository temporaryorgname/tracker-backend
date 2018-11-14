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
import boto3

from fitnessapp import database

s3 = boto3.resource('s3')
if 'LOGS_PHOTO_BUCKET_NAME' in os.environ:
    PHOTO_BUCKET_NAME = os.environ['LOGS_PHOTO_BUCKET_NAME']
else:
    PHOTO_BUCKET_NAME = 'dev-hhixl-food-photos-700'
food_bp = Blueprint('food', __name__)

def food_to_json(food):
    def get_photos(food_id):
        photos = database.FoodPhoto.query \
                .filter_by(food_id = food_id) \
                .all()
        return [p.id for p in photos]
    def cast_decimal(dec):
        if dec is None:
            return None
        return float(dec)
    return {
        "id": food.id, 
        "date": str(food.date),
        "name": food.name, 
        "quantity": food.quantity,
        "calories": cast_decimal(food.calories),
        "protein": cast_decimal(food.protein),
        "photos": get_photos(food.id)
    }

@food_bp.route('/food')
@login_required
def get_food():
    date = request.args.get('date')
    date = datetime.datetime.strptime(date, '%Y-%m-%d')
    if date is None:
        #foods = database.Food.query.filter_by(user_id=current_user.get_id()).all()
        foods = database.Food.query \
                .filter_by(user_id=current_user.get_id()) \
                .order_by(database.Food.date).all()
    else:
        foods = database.Food.query \
                .order_by(database.Food.date.desc()) \
                .filter_by(date=date, user_id=current_user.get_id()) \
                .all()
    def get_photos(food_id):
        photos = database.FoodPhoto.query \
                .filter_by(food_id = food_id) \
                .all()
        return [p.id for p in photos]
    data = [food_to_json(f) for f in foods]
    return json.dumps(data), 200

@food_bp.route('/food', methods=['PUT','POST'])
@login_required
def new_food():
    data = request.get_json()

    if 'name' not in data:
        return "No item name listed.", 400

    f = database.Food()
    if 'date' in data:
        f.date = data['date']
    else:
        f.date = datetime.datetime.now()
    if 'name' in data:
        f.name = data['name']
    if 'quantity' in data:
        f.quantity = data['quantity']
    if 'calories' in data:
        try:
            f.calories = float(data['calories'])
        except Exception:
            #f.calories = None
            pass
    if 'protein' in data:
        try:
            f.protein = float(data['protein'])
        except Exception:
            #f.protein = None
            pass
    f.user_id = current_user.get_id()

    database.db_session.add(f)
    database.db_session.flush()
    database.db_session.commit()

    if 'photos' in data:
        for photo_id in data['photos']:
            food_photo = database.FoodPhoto.query \
                .filter_by(id=photo_id) \
                .first()
            food_photo.food_id = f.id
            database.db_session.flush()
            database.db_session.commit()

    return str(f.id),200

@food_bp.route('/food/<food_id>', methods=['PUT','POST'])
@login_required
def update_food(food_id): # TODO: Does not work for numerical values yet
    data = request.get_json()

    if 'name' not in data:
        return "No item name listed.", 400

    f = database.Food.query \
            .filter_by(id=food_id) \
            .filter_by(user_id=current_user.get_id()) \
            .first()
    if f is None:
        return "ID not found", 404
    if 'date' in data:
        f.date = data['date']
    else:
        f.date = datetime.datetime.now()
    if 'name' in data:
        f.name = data['name']
    if 'quantity' in data:
        f.quantity = data['quantity']
    if 'calories' in data:
        try:
            f.calories = float(data['calories'])
        except Exception:
            pass
    if 'protein' in data:
        try:
            f.protein = float(data['protein'])
        except Exception:
            pass
    f.user_id = current_user.get_id()

    database.db_session.add(f)
    database.db_session.flush()
    database.db_session.commit()

    if 'photos' in data:
        for photo_id in data['photos']:
            food_photo = database.FoodPhoto.query \
                .filter_by(id=photo_id) \
                .first()
            food_photo.food_id = f.id
            database.db_session.flush()
            database.db_session.commit()

    return str(f.id),200

@food_bp.route('/food', methods=['DELETE'])
@login_required
def delete_many_foods():
    data = request.get_json()
    print("Requesting to delete entry %s." % data['id'])

    for food_id in data['id']:
        f = database.Food.query \
                .filter_by(id=food_id) \
                .filter_by(user_id=current_user.get_id()) \
                .first()

        if f is None:
            return "Unable to find requested food entry.", 404

        database.db_session.delete(f)

    database.db_session.flush()
    database.db_session.commit()
    return "Deleted successfully",200

@food_bp.route('/food/<food_id>', methods=['DELETE'])
@login_required
def delete_food(food_id):
    print("Requesting to delete entry %s." % food_id)
    f = database.Food.query \
            .filter_by(id=food_id) \
            .filter_by(user_id=current_user.get_id()) \
            .first()

    if f is None:
        return "Unable to find requested food entry.", 404

    database.db_session.delete(f)
    database.db_session.flush()
    database.db_session.commit()
    return "Deleted successfully",200

@food_bp.route('/food/photo/<int:photo_id>', methods=['GET'])
@login_required
def get_food_photo(photo_id):
    filename = str(photo_id)
    fp = database.FoodPhoto.query \
            .filter_by(id=photo_id) \
            .first()
    if fp is None:
        return "File ID not found.", 404

    # FIXME: Can't do this, because the photo isn't immediately attached to a food item
    #f = database.Food.query \
    #        .filter_by(id=fp.food_id) \
    #        .filter_by(user_id=current_user.get_id()) \
    #        .first()
    #if f is None:
    #    return "No photo with matching id for user.", 404

    filename = fp.file_name
    filename_32 = os.path.join(app.config['UPLOAD_FOLDER'], '%s-32'%filename)
    try:
        img = Image.open(filename_32)
        img.thumbnail((32,32))
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue())
        return json.dumps({
            'data': img_str.decode()
        }), 200
    except Exception:
        print('Failed to load tiny thumbnail locally for file %s.' % filename)
    # Couldn't find a local image, so get it from the aws server
    filename_700 = os.path.join(app.config['UPLOAD_FOLDER'], '%s-700'%filename)
    try:
        with open(filename_700, "wb") as f:
            s3.Bucket(PHOTO_BUCKET_NAME).Object(filename).download_fileobj(f)
        img = Image.open(filename_700) # FIXME: DRY
        img.thumbnail((32,32))
        img.save(filename_32,'jpeg')
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue())
        return json.dumps({
            'data': img_str.decode()
        }), 200
    except Exception:
        print("Unable to retrieve file %s from AWS servers." % filename)

    return json.dumps({
        'body': 'Unable to get file %s' % filename
    }), 404

@food_bp.route('/food/photo', methods=['PUT','POST'])
@login_required
def add_food_photo():
    # check if the post request has the file part
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
        filename_original = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        filename_700 = os.path.join(app.config['UPLOAD_FOLDER'],'%s-700' % filename)
        filename_32 = os.path.join(app.config['UPLOAD_FOLDER'],'%s-32' % filename)
        file.save(filename_original)
        # Resize photo
        img = Image.open(filename_original)
        img.thumbnail((700,700))
        # Remove transparency if there's an alpha channel
        if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
            print('Found transparency. Processing alpha channels.')
            alpha = img.split()[3]
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=alpha)
            img = background
        # Save smaller image
        img.save(filename_700, 'jpeg') 
        # Upload small image to AWS
        with open(filename_700, 'rb') as data:
            s3.Bucket(PHOTO_BUCKET_NAME).put_object(Key=filename, Body=data)
        # Resize to tiny thumbnail size
        img.thumbnail((32,32))
        img.save(filename_32, 'jpeg') 
        # Delete large local files
        os.remove(filename_original)
        os.remove(filename_700)
        # Save file name
        database.db_session.flush()
        database.db_session.commit()
        return json.dumps({'id': food_photo.id}),200

@food_bp.route('/food/search', methods=['GET'])
@login_required
def search_food():
    if 'q' not in request.args:
        return 'Invalid request. A query is required.', 400
    query = request.args['q']
    foods = database.Food.query \
            .order_by(database.Food.date.desc()) \
            .filter_by(user_id=current_user.get_id()) \
            .filter(database.Food.name.ilike('%{0}%'.format(query))) \
            .all()
    data = [food_to_json(f) for f in foods]
    return json.dumps(data), 200
