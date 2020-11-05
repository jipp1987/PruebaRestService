from flask import Blueprint, request
from flask_restful import Api

from core.rest.apitools import RequestResponse, encode_object_to_json, EnumHttpResponseStatusCodes
from rest.restcontroller import TipoClienteRestController


# Este módulo son los puntos de entrada de la api
api_bp = Blueprint('api', __name__)


# Defino los errorHandlers para el BluePrint. Estos errores son los normales que pueden producirse durante la request.
# Los errores de servicio se manejan dentro de cada implementación de RestController, se devuelve un objeto
# RequestResponse con un código de error.
@api_bp.app_errorhandler(EnumHttpResponseStatusCodes.UNAUTHORIZED.value)
@api_bp.app_errorhandler(EnumHttpResponseStatusCodes.NOT_FOUND.value)
@api_bp.app_errorhandler(EnumHttpResponseStatusCodes.METHOD_NOT_FOUND.value)
@api_bp.app_errorhandler(EnumHttpResponseStatusCodes.SERVER_ERROR.value)
def _handle_api_error(ex):
    if request.path.startswith('/api/'):
        response = RequestResponse(ex.description, success=False, status_code=ex.code)
        return encode_object_to_json(response)
    else:
        return ex


# Con catch_all_404s el objeto Api manejará todos los errores 404 además de los de sus propias rutas
api = Api(api_bp, catch_all_404s=False)

# Definir las distintas rutas de los rest controllers y asociarles una ruta de la api
api.add_resource(TipoClienteRestController, '/TipoCliente')
