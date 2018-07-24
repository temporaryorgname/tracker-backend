import flask
from flask import Flask, jsonify
from flask_cors import CORS
import flask_login
from flask_login import LoginManager
from fitnessapp.views.auth import auth_bp
from fitnessapp.views.food import food_bp

from fitnessapp import database

app = Flask(__name__,
        instance_relative_config=True,
        static_url_path='',
        static_folder='./static')
app.secret_key = 'super secret key'
CORS(app, supports_credentials=True)
app.config.from_object('config')
app.config.from_pyfile('config.py')

app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(food_bp, url_prefix='/api/data')

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return database.User.query.filter_by(id=user_id).first()

@login_manager.request_loader
def request_loader(request):
    email = request.form.get('email')

    user = database.User.query.filter_by(email=email)
    if user is None:
        return

    user.authenticated = request.form['password'] == user.password
    print(user.id)

    return user

@app.route('/')
def home_page():
    return jsonify({'body': 'Hello world from Flask!'})

#@app.route('/')
@app.route('/<path:path>')
def static_file(path):
    print("Static files")
    return app.send_static_file(path)
