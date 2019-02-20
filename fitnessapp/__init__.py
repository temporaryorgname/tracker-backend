import flask
from flask import Flask, jsonify
from flask_cors import CORS
import flask_login
from flask_login import LoginManager
from flasgger import Swagger
import sqlalchemy
import json
import traceback

from fitnessapp.views.auth import auth_bp
#from fitnessapp.views.user import user_bp
#from fitnessapp.views.food import food_bp
#from fitnessapp.views.body import body_bp

from fitnessapp.resources.food import blueprint as food_bp
from fitnessapp.resources.photos import blueprint as photos_bp
from fitnessapp.resources.photo_groups import blueprint as photo_groups_bp
from fitnessapp.resources.tags import blueprint as tags_bp
from fitnessapp.resources.labels import blueprint as labels_bp
from fitnessapp.resources.body import blueprint as body_bp
from fitnessapp.resources.users import blueprint as user_bp

from fitnessapp import database

app = Flask(__name__,
        instance_relative_config=True,
        static_url_path='/thisshouldneverbeused', # static_paths with the `static/*` path doesn't work without this.
        static_folder='./static')
swagger = Swagger(app)
app.secret_key = 'super secret key'
CORS(app, supports_credentials=True)
app.config.from_object('config')
app.config.from_pyfile('config.py')

app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(user_bp, url_prefix='/api/data')
app.register_blueprint(food_bp, url_prefix='/api/data')
app.register_blueprint(photos_bp, url_prefix='/api/data')
app.register_blueprint(photo_groups_bp, url_prefix='/api/data')
app.register_blueprint(tags_bp, url_prefix='/api/data')
app.register_blueprint(labels_bp, url_prefix='/api/data')
app.register_blueprint(body_bp, url_prefix='/api/data')

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return database.User.query.filter_by(id=user_id).first()

@login_manager.request_loader
def request_loader(request):
    email = request.form.get('email')
    password = request.form.get('password')
    if email is None or password is None:
        return

    user = database.User.query.filter_by(email=email)
    if user is None:
        return
    user.authenticated = password == user.password
    print(user.id)

    return user

@app.route('/favicon.ico')
def favicon_paths():
    return app.send_static_file("favicon.ico")

@app.route('/static', defaults={'path': ''})
@app.route('/static/<path:path>')
def static_paths(path):
    return app.send_static_file('static/'+path)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def react_paths(path):
    return app.send_static_file("index.html")

@app.errorhandler(sqlalchemy.exc.TimeoutError)
def timeouterror_handler(error):
    print(traceback.format_exc())
    database.db_session.rollback()
    return json.dumps({
        'error': 'Server too busy. Try again later.'
    }), 503

@app.errorhandler(Exception)
def exception_handler(error):
    print(traceback.format_exc())
    database.db_session.rollback()
    return json.dumps({
        'error': 'Server error encountered'
    }), 500
