from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///honey_producer.db'
app.config['SECRET_KEY'] = 'cf4919e217fd7v7795e15c1b'
app.config['UPLOADED_IMAGES_DEST'] = 'market/static/uploads'

db = SQLAlchemy(app)
with app.app_context():
    db.create_all()
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login_page"
login_manager.login_message_category = "info"
from market import routes
