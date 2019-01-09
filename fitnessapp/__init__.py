import flask
from flask import Flask, jsonify
from flask_cors import CORS
import flask_login
from flask_login import LoginManager
from flasgger import Swagger
import sqlalchemy
import json

from fitnessapp.views.auth import auth_bp
from fitnessapp.views.user import user_bp
#from fitnessapp.views.food import food_bp
from fitnessapp.views.body import body_bp

from fitnessapp.resources.food import blueprint as food_bp

from fitnessapp import database

app = Flask(__name__,
        instance_relative_config=True,
        static_url_path='',
        static_folder='./static')
swagger = Swagger(app)
app.secret_key = 'super secret key'
CORS(app, supports_credentials=True)
app.config.from_object('config')
app.config.from_pyfile('config.py')

app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(user_bp, url_prefix='/api/data')
app.register_blueprint(food_bp, url_prefix='/api/data')
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

@app.route('/', defaults={'path': ''})
@app.route("/<string:path>")
@app.route('/<path:path>')
def static_file(path):
    return app.send_static_file("index.html")

@app.errorhandler(sqlalchemy.exc.TimeoutError)
def timeouterror_handler(error):
    return json.dumps({
        'error': 'Server too busy. Try again later.'
    }), 503

@app.errorhandler(Exception)
def exception_handler(error):
    print(error)
    return json.dumps({
        'error': 'Unhandled error encountered'
    }), 500
