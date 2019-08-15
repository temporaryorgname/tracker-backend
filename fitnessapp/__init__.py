import flask
from flask import Flask, jsonify
import sqlalchemy
import json
import traceback

from fitnessapp.extensions import login_manager, db, swagger, cors

from tracker_database import User

app = Flask(__name__,
        instance_relative_config=True,
        # static_paths with the `static/*` path doesn't work without this.
        static_url_path='/thisshouldneverbeused',
        static_folder='./static')
app.secret_key = 'super secret key'
app.config.from_object('config')
app.config.from_pyfile('config.py')

cors.init_app(app, supports_credentials=True)
swagger.init_app(app)
db.init_app(app)
login_manager.init_app(app)

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
    db.session.rollback()
    return json.dumps({
        'error': 'Server too busy. Try again later.'
    }), 503

@app.errorhandler(Exception)
def exception_handler(error):
    print(traceback.format_exc())
    db.session.rollback()
    return json.dumps({
        'error': 'Server error encountered'
    }), 500

from fitnessapp.views.auth import auth_bp
from fitnessapp.resources.food import blueprint as food_bp
from fitnessapp.resources.photos import blueprint as photos_bp
from fitnessapp.resources.tags import blueprint as tags_bp
from fitnessapp.resources.labels import blueprint as labels_bp
from fitnessapp.resources.body import blueprint as body_bp
from fitnessapp.resources.users import blueprint as user_bp

app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(user_bp, url_prefix='/api/data')
app.register_blueprint(food_bp, url_prefix='/api/data')
app.register_blueprint(photos_bp, url_prefix='/api/data')
app.register_blueprint(tags_bp, url_prefix='/api/data')
app.register_blueprint(labels_bp, url_prefix='/api/data')
app.register_blueprint(body_bp, url_prefix='/api/data')
