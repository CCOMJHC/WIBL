import os

from flask import Flask
from flask_login import LoginManager

from jinja2 import FileSystemLoader

from wibl_frontend import db
from wibl_frontend import get_templates_path
from wibl_frontend.models import User
from wibl_frontend.auth import auth as auth_blueprint
from wibl_frontend.main import main as main_blueprint


FRONTEND_DATABASE_URI = os.environ.get('FRONTEND_DATABASE_URI', 'sqlite:///database.db')


app = Flask('WIBL-Frontend')
app.config['SECRET_KEY'] = 'secret-key-goes-here'
app.config['SQLALCHEMY_DATABASE_URI'] = FRONTEND_DATABASE_URI
db.init_app(app)

# Patch Flask's Jinja loader so that it can load from `templates` directory in `wibl_frontend` module,
# which for some reason isn't working with the default loader and our project layout.
app.jinja_env.loader = FileSystemLoader(get_templates_path())

# Begin: Initialize authentication middleware
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    # since the user_id is just the primary key of our user table, use it in the query for the user
    return User.query.get(int(user_id))
# End: Initialize authentication middleware


app.register_blueprint(auth_blueprint)
app.register_blueprint(main_blueprint)
