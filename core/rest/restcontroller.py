import abc
import enum
import json
from functools import wraps

import flask_restful
from werkzeug.local import LocalProxy

from core.util.noconflict import makecls


class RequestActions(enum.Enum):
    """Enumerado de acciones de peticiones."""

    CREATE = 1
    """Crear entidad"""

    UPDATE = 2
    """Actualizar entidad"""

    DELETE = 3
    """Borrar entidad"""

    SELECT = 4
    """Seleccionar con filtros"""


class RequestBody:
    """Objeto de cuerpo de Request."""

    def __init__(self, username: str = None, password: str = None, action: int = None,
                 request_object: any = None):
        super().__init__()
        self.username = username
        self.password = password
        self.action = action
        self.request_object = request_object


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

        flask_restful.abort(401)

    return wrapper


def convert_request_to_request_body(request: LocalProxy):
    """Convierte un json a un RequestBody"""
    # get_json devuelve un diccionario. Lo convierto a formato json para poder convertirlo a objeto
    json_format = json.dumps(request.get_json(), ensure_ascii=False)
    # lo convierto a diccionario
    json_dict = json.loads(json_format)
    # deserializo el diccionario en el objeto deseado
    return RequestBody(**json_dict)


class CustomResource(flask_restful.Resource):
    __metaclass__ = makecls(abc.ABCMeta)

    """Implementación de los Resource de flask_restful. Los recursos de la aplicación deberán heredar de esta clase.
    Es una clase abstracta, por eso su metaclase es ABCMeta. """

    # Resource de flask_restful tiene esta propiedad que son los decoradores de las funciones.
    # Lo que hago es forzar que todas las funciones de las clases que hereden de CustomResource pasen por una
    # autenticación.
    method_decorators = [authenticate]

    @abc.abstractmethod
    def _create_with_response(self, request_object: any):
        """Método para crear una entidad devolviendo una respuesta."""
        return

    @abc.abstractmethod
    def _delete_with_response(self, request_object: any):
        """Método para borrar una entidad devolviendo una respuesta."""
        return

    @abc.abstractmethod
    def _update_with_response(self, request_object: any):
        """Método para actualizar una entidad devolviendo una respuesta."""
        return
