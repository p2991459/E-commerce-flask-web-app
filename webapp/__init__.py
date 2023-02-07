# init.py
from celery import Celery
from decouple import config
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData
from flask_login import LoginManager
from flask_migrate import Migrate
from os.path import join, dirname, realpath

UPLOADS_PATH = join(dirname(realpath(__file__)), 'static/vehicle_receipt')
# init SQLAlchemy so we can use it later in our models

convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=convention)
db = SQLAlchemy(metadata=metadata)
migrate = Migrate()
celery = Celery(__name__, broker='filesystem://')
celery.conf.update({
    'broker_url': 'filesystem://',
    'broker_transport_options': {
        'data_folder_in': config('DATA_FOLDER_IN', '/home/pcoder/Desktop/broker/out'),
        'data_folder_out': config('DATA_FOLDER_OUT', '/home/pcoder/Desktop/broker/out'),
        'data_folder_processed': config('DATA_FOLDER_PROCESSED', '/home/pcoder/Desktop/broker/processed'),
    },
    'imports': ('project',),
    'result_persistent': False,
    'task_serializer': 'json',
    'result_serializer': 'json',
    'accept_content': ['json']})
celery.autodiscover_tasks(['project.main'])


def create_app():
    app = Flask(__name__, static_url_path='', static_folder='static')
    app.config['SECRET_KEY'] = '9OLWxND4o83j4K4iuopO'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'
    app.config['UPLOAD_FOLDER'] = UPLOADS_PATH
    db.init_app(app)
    migrate.init_app(app, db, render_as_batch=True)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        # since the user_id is just the primary key of our user table, use it
        # in the query for the user
        return User.query.get(int(user_id))

    # blueprint for auth routes in our app
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    # blueprint for non-auth parts of app
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    # blueprint for vehicle route
    # from .vehicle_api import api_vehicle as vehicle_blueprint
    # app.register_blueprint(vehicle_blueprint)

    from .controllers.VehicleController import api_vehicle as vehicle_api
    app.register_blueprint(vehicle_api)

    from .tests import tests as tests_blueprint
    app.register_blueprint(tests_blueprint)

    from .youth_roster import youth as youth_blueprint
    app.register_blueprint(youth_blueprint)

    from project.context_processor import utility_processor
    app.context_processor(utility_processor)

    return app
