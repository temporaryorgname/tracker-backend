import datetime
import os
from PIL import Image
from io import BytesIO
import base64
import boto3

from flask import current_app as app

from fitnessapp import database

s3 = boto3.resource('s3')
if 'LOGS_PHOTO_BUCKET_NAME' in os.environ:
    PHOTO_BUCKET_NAME = os.environ['LOGS_PHOTO_BUCKET_NAME']
else:
    PHOTO_BUCKET_NAME = 'dev-hhixl-food-photos-700'

def food_to_dict(food, with_photos=False, with_children=False):
    """ Convert a food entry to a dictionary, along with a list of photo IDs, and children
    """
    output = food.to_dict()

    # Add photo data
    if with_photos:
        if food.photo_group_id is not None:
            photo_ids = database.Photo.query \
                    .with_entities(
                            database.Photo.id
                    )\
                    .filter_by(user_id=food.user_id) \
                    .filter_by(group_id=food.photo_group_id) \
                    .all()
            output['photo_ids'] = [x[0] for x in photo_ids]
        elif food.photo_id is not None:
            output['photo_ids'] = [food.photo_id]
        else:
            output['photo_ids'] = []

    # Add children data
    if with_children:
        children = database.Food.query \
                .filter_by(user_id=food.user_id) \
                .filter_by(parent_id=food.id) \
                .all()
        output['children'] = [
            food_to_dict(c, with_photos, with_children) for c in children
        ]

    return output

def update_food_from_dict(data, user_id, parent_id=None):
    """ Parse a dictionary representing a food entry and return make the appropriate updates in the database
    Args:
        data: dictionary representing the food entry.
            children: children food entries of the same format as `data`
            photo_ids: a list containing IDs of photos associated with this entry.
        user_id: User who owns these entries
        parent_id: ID of the food entry that is parent to the entry represented by `data`.
    """
    # If editing an existing entry, load it up. Otherwise, create a new entry.
    if 'id' in data and data['id'] is not None:
        f = database.Food.query \
            .filter_by(id = data['id']) \
            .filter_by(user_id=user_id) \
            .first()
    else:
        f = database.Food.from_dict(data)
        f.user_id = user_id

    f.parent_id = parent_id

    if 'photo_ids' in data:
        # Check if the photos are already part of a group
        # If so, assign the food entry to that group
        # If different photos are part of different groups, then remove them from those groups and create a new one
        # If not, then either create a new group, or assign it to the single photo
        photos = database.Photo.query \
                .filter(database.Photo.id.in_(data['photo_ids'])) \
                .all()

        # Photos should be assigned to the same date
        for p in photos:
            if str(p.date) != data['date']:
                raise ValueError('Provided photos do not belong to the same date as the created food entry. Photo was taken on %s and the entry is being created for %s.' % (p.date, data['date']))

        # Ensure they all belong to the same group
        group_ids = set([p.group_id for p in photos if p.group_id is not None])
        # TODO: Ensure that there are no other photos in the group
        if len(group_ids) == 1:
            # There's already a group assigned to the photo(s), so use that
            group = database.PhotoGroup.query \
                    .filter_by(id = list(group_ids)[0]) \
                    .first()
            if group.date != data['date']:
                raise ValueError('Provided photo group does not belong to the same date as the created food entry.')
            f.photo_group_id = group.id
            f.photo_id = None
        elif len(photos) > 1:
            # No group or multiple groups were assigned to the photos,
            # so create one
            group = database.PhotoGroup()
            group.date = data['date']
            group.user_id = user_id
            database.db_session.add(group)
            database.db_session.flush()
            f.photo_group_id = group.id
            f.photo_id = None
            for p in photos:
                p.group_id = group.id
        elif len(photos) == 1:
            # No group was assigned, and there was only one photo,
            # so no group is needed
            group = None
            f.photo_group_id = None
            f.photo_id = photos[0].id
        else:
            # No photos
            group = None
            f.photo_group_id = None
            f.photo_id = None

    database.db_session.add(f)
    database.db_session.flush()

    ids = [int(f.id)]

    # Parse children
    if 'children' in data:
        for child in data['children']:
            ids += update_food_from_dict(child, user_id, parent_id=f.id)

    # Commit once when everything is done.
    if parent_id is None:
        database.db_session.commit()

    return ids

def delete_food(food, depth=0):
    """ Delete a food entry along with all children recursively.
    """
    children = database.Food.query \
                .filter_by(parent_id=food.id) \
                .all()
    for c in children:
        delete_food(c, depth=depth+1)

    database.db_session.delete(food)
    database.db_session.flush()

    if depth == 0:
        database.db_session.commit()

def photo_group_to_dict(group, with_photos=False):
    """ Convert a photo group entry to a dictionary, along with a list of photo IDs
    """
    output = group.to_dict()

    # Add photo data
    if with_photos:
        photo_ids = database.PhotoGroup.query \
                .with_entities(
                        database.Photo.id
                )\
                .filter_by(user_id=group.user_id) \
                .filter_by(group_id=group.id) \
                .all()
        output['photo_ids'] = [x[0] for x in photo_ids]
    return output

def get_photo_data_base64(photo_id, format='png', size=32):
    filename = str(photo_id)
    fp = database.Photo.query \
            .filter_by(id=photo_id) \
            .one()
    if fp is None:
        raise Exception("File ID not found.")

    def get_Local_image(size):
        filename = os.path.join(
                app.config['UPLOAD_FOLDER'],
                '%s-%s'%(fp.file_name, size))
        try:
            return Image.open(filename)
        except Exception:
            print('Failed to load tiny thumbnail locally for file %s.' % filename)
    def get_s3_image(size):
        filename = os.path.join(
                app.config['UPLOAD_FOLDER'],
                '%s-700'%(fp.file_name))
        filename_resized = os.path.join(
                app.config['UPLOAD_FOLDER'],
                '%s-%s'%(fp.file_name,size))
        try:
            with open(filename, "wb") as f:
                s3.Bucket(PHOTO_BUCKET_NAME) \
                  .Object(str(photo_id)) \
                  .download_fileobj(f)
            img = Image.open(filename)
            if size == 700:
                return img
            img.thumbnail((size,size))
            img.save(filename_resized,'PNG')
            return img
        except Exception as e:
            print("Unable to retrieve file %s from AWS servers." % filename)

    img = get_Local_image(size)
    if img is None:
        img = get_s3_image(size)
    if img is None:
        raise Exception(
            'Unable to retrieve file %s.' % filename
        )

    buffered = BytesIO()
    img.save(buffered, format=format)
    img_str = base64.b64encode(buffered.getvalue())
    # TODO: Return a application/octect-stream response instead of a JSON-wrapped base64 string.
    return img_str.decode()

def save_photo_data(file, file_name):
    print('saving file ', file_name)
    # Save file
    file_name_original = os.path.join(app.config['UPLOAD_FOLDER'], file_name)
    file_name_700 = os.path.join(app.config['UPLOAD_FOLDER'],'%s-700' % file_name)
    file_name_32 = os.path.join(app.config['UPLOAD_FOLDER'],'%s-32' % file_name)
    file.save(file_name_original)
    # Resize photo
    img = Image.open(file_name_original)
    # Remove transparency if there's an alpha channel
    if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
        print('Found transparency. Processing alpha channels.')
        alpha = img.split()[3]
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=alpha)
        img = background
    # Save smaller image
    img.thumbnail((700,700))
    img.save(file_name_700, 'jpeg') 
    # Upload small image to AWS
    with open(file_name_700, 'rb') as data:
        s3.Bucket(PHOTO_BUCKET_NAME).put_object(Key=file_name, Body=data)
    # Resize to tiny thumbnail size
    img.thumbnail((32,32))
    img.save(file_name_32, 'jpeg') 
    # Delete large local files
    os.remove(file_name_original)
    os.remove(file_name_700)

def photo_to_dict(photo, with_data=False, photo_size=32):
    output = photo.to_dict()
    if with_data:
        output['file'] = {
                'format': 'png',
                'content': get_photo_data_base64(photo.id, format='png', size=photo_size)
        }
    return output
