import datetime

from fitnessapp import database

def food_to_json(food, with_photos=False, with_children=False):
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
            food_to_json(c, with_photos, with_children) for c in children
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
            if p.date != data['date']:
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
