from flask import Flask

from rest.app import api_bp


def create_app(config_filename):
    app_rest = Flask(__name__)

    # Esto de momento lo dejo configurado: es para establecer una configuración de la api a partir de un fichero
    # config.py
    # app_rest.config.from_object(config_filename)

    app_rest.register_blueprint(api_bp, url_prefix='/api')

    # from Model import db
    # db.init_app(app)

    return app_rest


if __name__ == "__main__":
    app = create_app("config")
    app.run(debug=True)

