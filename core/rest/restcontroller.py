import abc
import json

import flask_restful
from flask import make_response, request
from werkzeug.local import LocalProxy

from core.exception.exceptionhandler import ServiceException
from core.rest.apitools import encode_object_to_json, EnumPostRequestActions, RequestResponse, \
    EnumHttpResponseStatusCodes, authenticate, RequestBody
from core.util import i18n
from core.util.noconflict import makecls


class RestController(flask_restful.Resource):
    """Implementación de los Resource de flask_restful. Los recursos de la aplicación deberán heredar de esta clase.
    Es una clase abstracta, por eso su metaclase es ABCMeta. """

    # Esta clase hereda de Rousource de flask_restful, una clase que tiene definida su propia metaclase. Además,
    # quiero que en el core sea abstracta por lo que tiene que tener la metaclase abc.ABCMeta. Sucede que Python no es
    # capaz por sí mismo de decidir cuál de las dos metaclases es la principal, por lo que uso una utilidad que genera
    # una metaclase a partir de las clases de las que herede la clase principal, o bien directamente le paso como
    # parámetro una metaclase (como es este caso) con la que quiero mezclar.
    __metaclass__ = makecls(abc.ABCMeta)

    # Resource de flask_restful tiene esta propiedad que son los decoradores de las funciones.
    # Lo que hago es forzar que todas las funciones de las clases que hereden de CustomResource pasen por una
    # autenticación.
    method_decorators = [authenticate]

    @abc.abstractmethod
    def _create_with_response(self, request_object: dict):
        """Método para crear una entidad devolviendo una respuesta."""
        pass

    @abc.abstractmethod
    def _delete_with_response(self, request_object: dict):
        """Método para borrar una entidad devolviendo una respuesta."""
        pass

    @abc.abstractmethod
    def _update_with_response(self, request_object: dict):
        """Método para actualizar una entidad devolviendo una respuesta."""
        pass

    @staticmethod
    def _convert_request_to_request_body(request_local_proxy: LocalProxy):
        """
        Convierte el get_json de un LocalProxy a un RequestBody.
        :param request_local_proxy: Objeto LocalProxy que contiene el json
        :return: RequestBody
        """

        # get_json devuelve un diccionario. Lo convierto a formato json para poder convertirlo a objeto
        if request_local_proxy.get_json() is not None:
            json_format = json.dumps(request_local_proxy.get_json(), ensure_ascii=False)

            # lo convierto a diccionario
            json_dict = json.loads(json_format)

            # deserializo el diccionario en el objeto deseado
            request_body = RequestBody(**json_dict)

            return request_body

    @staticmethod
    def _convert_request_response_to_json_response(response_body: RequestResponse):
        """
        Crea una respuesta json a partir de un RequestResponse.
        :param response_body: Objeto RequestResponse
        :return: Respuesta válida para el solicitante en formato json.
        """
        return make_response(encode_object_to_json(response_body), response_body.status_code)

    def post(self):
        """
        Método post de controller rest de tipos de cliente.
        :return: Cadena con mensaje formateado para devolver al solicitante.
        """
        # Obtengo datos json de la petición
        request_body = self._convert_request_to_request_body(request)

        try:
            result = None

            # Comprobar la acción enviada en la Request
            request_action = EnumPostRequestActions(request_body.action)

            if request_action == EnumPostRequestActions.CREATE:
                result = self._create_with_response(request_body.request_object)

            # Devuelvo una respuesta correcta
            response_body = RequestResponse(result, success=True, status_code=EnumHttpResponseStatusCodes.OK.value)
            return self._convert_request_response_to_json_response(response_body)
        except ServiceException as e:
            result = i18n.translate("i18n_base_commonError_request", None, *[e.known_error])
            response_body = RequestResponse(result, success=False,
                                            status_code=EnumHttpResponseStatusCodes.BAD_REQUEST.value)
        return self._convert_request_response_to_json_response(response_body)