import abc
from functools import wraps

import flask_restful
from flask import make_response, request
from werkzeug.local import LocalProxy

from core.exception.exceptionhandler import CustomException, catch_exceptions
from core.model.baseentity import BaseEntity
from core.rest.apitools import EnumPostRequestActions, RequestResponse, \
    EnumHttpResponseStatusCodes, RequestBody
from core.service.service import BaseService
from core.util import i18nutils
from core.util.jsonutils import encode_object_to_json, decode_object_to_json
from core.util.noconflict import makecls


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
    def get_main_service(self) -> BaseService:
        """
        Función a implementar que devuelve un SERVICE a modo de servicio principal.
        :return: Objeto que herede de BaseService.
        """
        pass

    def _create_with_response(self, entity: BaseEntity):
        """Método para crear una entidad devolviendo una respuesta."""
        # Importante llamar la función dentro de una transacción
        self.get_main_service().start_transaction(self.get_main_service().insert, entity)

        return i18nutils.translate("i18n_base_common_insert_success", None, *[str(entity)])

    def _delete_with_response(self, entity: BaseEntity):
        """Método para borrar una entidad devolviendo una respuesta."""
        # Importante llamar la función dentro de una transacción
        self.get_main_service().start_transaction(self.get_main_service().delete_entity, entity)

        return i18nutils.translate("i18n_base_common_delete_success", None, *[str(entity)])

    def _update_with_response(self, entity: BaseEntity):
        """Método para actualizar una entidad devolviendo una respuesta."""
        # Importante llamar la función dentro de una transacción
        self.get_main_service().start_transaction(self.get_main_service().update, entity)

        return i18nutils.translate("i18n_base_common_update_success", None, *[str(entity)])

    def _select_with_response(self):
        """Método para seleccionar datos de una tabla."""
        pass

    @staticmethod
    def _convert_request_response_to_json_response(response_body: RequestResponse):
        """
        Crea una respuesta json a partir de un RequestResponse.
        :param response_body: Objeto RequestResponse
        :return: Respuesta válida para el solicitante en formato json.
        """
        return make_response(encode_object_to_json(response_body), response_body.status_code)

    @catch_exceptions
    def __resolve_action_outer(self, request_proxy: LocalProxy):
        """
        Resuelve la acción a realizar a través del objeto RequestBody. Es una función privada a modo de hook para
        tratar las excepciones a través del decorator catch_exceptions, así me despreocupo de tener que acordarme
        en las implementaciones de RestController.
        :param request_proxy: Objeto request.
        :return: Devuelve bien un mensaje de éxito o error, o si es una select un json con el resultado.
        """
        # Primero transformo el objeto json de LocalProxy a string json
        json_format = encode_object_to_json(request_proxy.get_json())
        # Luego transformo el string json a un objeto RequestBody, pasando el tipo como parámetro
        request_body = decode_object_to_json(json_format, RequestBody)
        # Convertir objeto de request a entidad base
        entity = self.get_main_service().entity_type.convert_dict_to_entity(request_body.request_object)
        # Resolver acción
        return self._resolve_action(entity, request_body.action)

    def _resolve_action(self, entity: BaseEntity, action: int):
        """
        Método que resuelve la acción a realizar en post a través del RequestBody, en concreto de un int con la acción
        seleccionada. Las implementaciones de RestController que lo necesiten pueden sobrescribir esta función.
        :param entity: Entidad.
        1 -> Crear
        2 -> Actualizar
        3 -> Borrar
        4 -> Seleccionar
        :param action: Entero con una acción a resolver.
        :return: Devuelve bien un mensaje de éxito o error, o si es una select un json con el resultado.
        """
        # Comprobar la acción enviada en la Request
        request_action = EnumPostRequestActions(action)

        result = None
        if request_action == EnumPostRequestActions.CREATE:
            result = self._create_with_response(entity)
        elif request_action == EnumPostRequestActions.DELETE:
            result = self._delete_with_response(entity)
        elif request_action == EnumPostRequestActions.UPDATE:
            result = self._update_with_response(entity)
        else:
            # TODO Implementar select
            # result = self._select_with_response()
            pass

        return result

    def post(self):
        """
        Método post de controller rest. NO se recomienda su sobrescritura. Si lo que se desea es
        sobrescribir el comportamiento de RestController, lo mejor es sobrescribir _resolve_action.
        :return: Cadena con mensaje formateado para devolver al solicitante.
        """
        try:
            # Obtengo datos json de la petición
            result = self.__resolve_action_outer(request)
            # Devuelvo una respuesta correcta
            response_body = RequestResponse(result, success=True, status_code=EnumHttpResponseStatusCodes.OK.value)

            return self._convert_request_response_to_json_response(response_body)
        except CustomException as e:
            # Se produce algún error
            print(str(e))
            result = i18nutils.translate("i18n_base_commonError_request", None, *[e.known_error])
            response_body = RequestResponse(result, success=False,
                                            status_code=EnumHttpResponseStatusCodes.BAD_REQUEST.value)

            return self._convert_request_response_to_json_response(response_body)
