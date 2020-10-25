from flask import Blueprint
from flask_restful import Api

from rest.restcontroller import TipoClienteRestController

# Este módulo son los puntos de entrada de la api
api_bp = Blueprint('api', __name__)
api = Api(api_bp)

# Definir las distintas rutas de los rest controllers y asociarles una ruta de la api
api.add_resource(TipoClienteRestController, '/TipoCliente')