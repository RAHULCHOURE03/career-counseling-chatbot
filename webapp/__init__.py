"""Flask application package for the engineering chatbot."""

from flask import Flask
from .config import Config
from .extensions import bcrypt, db


def create_app(test_config=None):
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.from_object(Config)
    if test_config is None:
        Config.validate()
    else:
        app.config.update(test_config)
    db.init_app(app)
    bcrypt.init_app(app)
    from . import models
    from .routes import web
    app.register_blueprint(web)
    with app.app_context():
        db.create_all()
    return app
