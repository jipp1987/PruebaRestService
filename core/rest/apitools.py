"""
Módulo con herramientas para la api. Incluyendo un constructor para objetos API usando flask_restful y blue print,
una clase abstracta para los controladores de peticiones rest, y funciones y enumerados útiles para tratamiento de
JSON, códigos de estado http...
"""

import enum
from dataclasses import dataclass
from typing import List, Tuple

import flask_restful
from flask import Blueprint, request, Flask
from flask_cors import CORS

from core.dao.basedao import BaseDao
from core.util.i18nutils import add_language_dictionaries
from core.util.jsonutils import encode_object_to_json
from core.util.resourceutils import load_resource_files, get_data_from_resource


class EnumPostRequestActions(enum.Enum):
    """Enumerado de acciones de peticiones POST."""

    CREATE = 1
    """Crear entidad"""

    UPDATE = 2
    """Actualizar entidad"""

    DELETE = 3
    """Borrar entidad"""

    SELECT = 4
    """Seleccionar de una tabla."""


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
        """Nombre de usuario para token de autenticación."""
        self.password = password
        """Password de usuario para token de autenticación."""
        self.action = action
        """Acción a realizar."""
        self.request_object = request_object
        """Objeto de la request. Puede ser un BaseEntity, una lista de filtros..."""


@dataclass(init=True, frozen=True)
class RequestResponse:
    """Objeto de respuesta de request."""
    success: bool
    status_code: int
    response_object: any


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
            response = RequestResponse(response_object=ex.description, success=False, status_code=ex.code)
            return encode_object_to_json(response)
        else:
            return ex

    # Con catch_all_404s el objeto Api manejará todos los errores 404 además de los de sus propias rutas
    api = flask_restful.Api(api_bp, catch_all_404s=False)
    # Devuelvo tanto el blueprint como la api
    return api_bp, api


def create_and_run_app(api_name: str, controllers: List[Tuple[any, str]], resource_list: List[str],
                       i18n_dictionaries: List[Tuple[str, str, str]] = None, debug=False, threaded=True):
    """
    Crea una app flask. Registrará un blueprint y una api.
    :param api_name: Nombre de la api.
    :param controllers: Lista de tuplas para registrar las direcciones de los servicios de la api y sus controladores.
    El primer valor de la tupla es el objeto controlador, y el segundo es la ruta dentro de la api.
    :param resource_list: Lista con los recursos de propiedades.
    :param i18n_dictionaries: Lista de tuplas de tres valores. El primer valor es el iso de la lengua, el segundo valor
    es el nombre del fichero sin la extensión, el tercero la ruta en que se encuentran. Por ejemplo: la ruta completa
    podría ser esta (desde la raíz del proyecto): resources/locales/fr_FR/diccionario.mo: el primero valor sería
    'fr_FR', el segundo sería './resources/locales' y el tercero sería 'diccionario'.
    :param debug: Si true, activado modo debug. DEBE ser False para producción.
    :param threaded: Si true, aplicación multihilo.
    :return: Devuelve una app_rest de flask con la api y sus rutas registradas usando un blueprint.
    """
    # Cargar recursos de propiedades.
    load_resource_files(resource_list=resource_list)

    # Establecer valores para BaseDao: datos de conexión con la base de datos y pool de conexiones.
    db_config = {
        'host': get_data_from_resource("host"),
        'user': get_data_from_resource("username"),
        'password': get_data_from_resource("password"),
        'database': get_data_from_resource("dbname"),
        'db_engine': get_data_from_resource("db_engine")
    }

    # Configurar conexión de base dao
    # Esto va a modificar un atributo de clase de BaseDao: la idea es que estas apis se encapsulen en un virtualenv
    # para que sean independientes unas de otras, de tal modo que cada una modifique su dao y no altere el de otras
    # apis desplegadas en el mismo servidor. Esto también crea el pool de conexiones.
    BaseDao.set_db_config_values(**db_config)

    # Cargar diccionarios para gettext
    if i18n_dictionaries:
        add_language_dictionaries(i18n_dictionaries)

    # Objeto app_rest de Flask
    app_rest = Flask(__name__)

    # Registro el blueprint con la api y me traigo los dos
    api_bp, api = create_api_from_blueprint(api_name)

    # Definir las distintas rutas de los rest controllers y asociarles una ruta de la api
    for a, b in controllers:
        # Primer valor, objeto controlador; segundo valor, string con el nombre de la ruta en la api
        api.add_resource(a, b)

    # Registro en el objeto app el blueprint
    app_rest.register_blueprint(api_bp, url_prefix=f'/{api_name}')

    # Usar la librería CORS para permitir request cross-origin.
    CORS(app_rest)

    # Multihilo. Pero al ser un servidor para debug, es posible que sólo haya un hilo en ejecución.
    app_rest.run(debug=debug, threaded=threaded)
