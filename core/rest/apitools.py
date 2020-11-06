"""
Módulo con herramientas para la api. Incluyendo un constructor para objetos API usando flask_restful y blue print,
una clase abstracta para los controladores de peticiones rest, y funciones y enumerados útiles para tratamiento de
JSON, códigos de estado http...
"""

import enum
from functools import wraps
from typing import List, Tuple

import flask_restful
import jsonpickle
from flask import Blueprint, request, Flask


class EnumPostRequestActions(enum.Enum):
    """Enumerado de acciones de peticiones POST."""

    CREATE = 1
    """Crear entidad"""

    UPDATE = 2
    """Actualizar entidad"""

    DELETE = 3
    """Borrar entidad"""


class EnumHttpResponseStatusCodes(enum.Enum):
    """Enumerado de códigos de estado para respuestas de peticiones Http."""

    OK = 200
    """OK."""

    CREATED = 201
    """Creado."""

    BAD_REQUEST = 400
    """Algún error en los datos enviados para realizar la petición."""

    UNAUTHORIZED = 401
    """Sin autorización."""

    FORBIDDEN = 403
    """Prohibido."""

    NOT_FOUND = 404
    """Recurso no encontrado."""

    METHOD_NOT_FOUND = 405
    """Método no encontrado."""

    REQUEST_TIMEOUT = 408
    """Tiempo para ejecutar la petición consumido."""

    SERVER_ERROR = 500
    """Error de servidor."""


class RequestBody:
    """Objeto de cuerpo de Request."""

    def __init__(self, username: str = None, password: str = None, action: int = None,
                 request_object: any = None):
        super().__init__()
        self.username = username
        self.password = password
        self.action = action
        self.request_object = request_object


class RequestResponse:
    """Objeto de respuesta de request."""

    def __init__(self, message: str, success: bool, status_code: int = None, response_object: any = None):
        super().__init__()
        self.message = message
        self.success = success
        self.status_code = status_code
        self.response_object = response_object


def authenticate(func):
    """Decorator para forzar la autenticación de cualquier llamada de API rest."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        # Comprueba si la función tiene el atributo authenticated, devolviendo True en caso de que no exista
        # Si existe, la función se ejecuta directamente porque ya está autenticada.
        if not getattr(func, 'authenticated', True):
            return func(*args, **kwargs)

        # TODO Implementar autenticación
        # acct = basic_authentication()
        acct = True

        if acct:
            return func(*args, **kwargs)

        flask_restful.abort(EnumHttpResponseStatusCodes.UNAUTHORIZED.value)

    return wrapper


def encode_object_to_json(object_to_encode: any):
    """
    Serializa un objeto en json. Usa la librería jsonpickle.
    :param object_to_encode: Objeto a codificar en json.
    :return: json
    """
    # Preparo el objeto jsonpickle
    jsonpickle.set_preferred_backend('json')
    jsonpickle.set_encoder_options('json', ensure_ascii=False)
    # unpicklable Si es true, lo que hace es dar más información de la clase tanto del objeto principal como de
    # los objetos anidados. En principio lo pongo a false.
    return jsonpickle.encode(object_to_encode, unpicklable=False)


def create_api_from_blueprint(api_name: str = "api"):
    """
    Crea un blueprint y asociado a éste una api. Al blueprint se le inyecta una función para gestionar los errores
    durante la request, excepto aquéllos ya controlados por los servicios.
    :param api_name: Nombre de la api, por defecto "api".
    :return: Devuelve por un lado el blueprint, y por otro la api.
    """
    # Este módulo son los puntos de entrada de la api
    api_bp = Blueprint(api_name, __name__)

    # Defino los errorHandlers para el BluePrint. Estos errores son los normales que pueden producirse durante la
    # request. Los errores de servicio se manejan dentro de cada implementación de RestController, se devuelve un
    # objeto RequestResponse con un código de error.
    @api_bp.app_errorhandler(EnumHttpResponseStatusCodes.UNAUTHORIZED.value)
    @api_bp.app_errorhandler(EnumHttpResponseStatusCodes.NOT_FOUND.value)
    @api_bp.app_errorhandler(EnumHttpResponseStatusCodes.METHOD_NOT_FOUND.value)
    @api_bp.app_errorhandler(EnumHttpResponseStatusCodes.SERVER_ERROR.value)
    def _handle_api_error(ex):
        if request.path.startswith(f'/{api_name}/'):
            response = RequestResponse(ex.description, success=False, status_code=ex.code)
            return encode_object_to_json(response)
        else:
            return ex

    # Con catch_all_404s el objeto Api manejará todos los errores 404 además de los de sus propias rutas
    api = flask_restful.Api(api_bp, catch_all_404s=False)
    # Devuelvo tanto el blueprint como la api
    return api_bp, api


def create_app(api_name: str, pairs: List[Tuple[any, str]], config_object: any = None):
    """
    Crea una app flask. Registrará un blueprint y una api.
    :param api_name: Nombre de la api.
    :param pairs: Lista de tuplas para registrar las direcciones de los servicios de la api y sus controladores.
    El primer valor de la tupla es el objeto controlador, y el segundo es la ruta dentro de la api.
    :param config_object: Objeto python con la configuración de la app. Por defecto None.
    :return: Devuelve una app_rest de flask con la api y sus rutas registradas usando un blueprint.
    """
    # Objeto app_rest de Flask
    app_rest = Flask(__name__)

    # Esto es para establecer una configuración de la api a partir de un objeto.
    if config_object:
        app_rest.config.from_object(config_object)

    # Registro el blueprint con la api y me traigo los dos
    api_bp, api = create_api_from_blueprint(api_name)

    # Definir las distintas rutas de los rest controllers y asociarles una ruta de la api
    for a, b in pairs:
        # Primer valor, objeto controlador; segundo valor, string con el nombre de la ruta en la api
        api.add_resource(a, b)

    # Registro en el objeto app el blueprint
    app_rest.register_blueprint(api_bp, url_prefix=f'/{api_name}')

    return app_rest
