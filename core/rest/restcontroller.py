import abc
from functools import wraps
from typing import List

import flask_restful
from flask import make_response, request
from werkzeug.local import LocalProxy

from core.dao.querytools import JsonQuery
from core.exception.exceptionhandler import CustomException, catch_exceptions
from core.model.modeldefinition import BaseEntity
from core.rest.apitools import EnumPostRequestActions, RequestResponse, \
    EnumHttpResponseStatusCodes, RequestBody
from core.service.service import BaseService
from core.util.i18nutils import translate
from core.util.jsonutils import encode_object_to_json, decode_object_from_json
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
        self.get_main_service().insert(entity)

        return translate("i18n_base_common_insert_success", None, *[str(entity)])

    def _delete_with_response(self, entity: BaseEntity):
        """Método para borrar una entidad devolviendo una respuesta."""
        self.get_main_service().delete_entity(entity)

        return translate("i18n_base_common_delete_success", None, *[str(entity)])

    def _update_with_response(self, entity: BaseEntity):
        """Método para actualizar una entidad devolviendo una respuesta."""
        self.get_main_service().update(entity)

        return translate("i18n_base_common_update_success", None, *[str(entity)])

    def _select_with_response(self, query_object: JsonQuery):
        """Método para seleccionar datos de una tabla."""
        # Hago la consulta, comprobando si es un conteo de filas o una select normal
        if query_object.is_count:
            result: int = self.get_main_service().count_rows(filters=query_object.filters,
                                                             joins=query_object.joins)
        else:
            result: List[BaseEntity] = self.get_main_service().select(filters=query_object.filters,
                                                                      order_by=query_object.order,
                                                                      fields=query_object.fields,
                                                                      group_by=query_object.group_by,
                                                                      joins=query_object.joins,
                                                                      offset=query_object.offset,
                                                                      limit=query_object.limit)
        return result

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
        json_format = encode_object_to_json(request_proxy.get_json(force=True))
        # Luego transformo el string json a un objeto RequestBody, pasando el tipo como parámetro
        request_body: RequestBody = decode_object_from_json(json_format, RequestBody)
        # Resolver acción
        return self._resolve_action(request_body.action, request_body.request_object)

    def __convert_request_object_to_base_entity(self, request_object: any, is_update: bool = False) -> BaseEntity:
        """
        Convierte el objeto json de la petición en una BaseEntity. Pensado para crear, modificar y eliminar.
        :param request_object: Objecto request que va a convertirse en BaseEntity.
        :param is_update: Si es update, la operación de convertir de diccionario a entidad devuelve dos parámetros.
        :return: BaseEntity
        """
        # Si es update, me llegan dos parámetros. Por un lado, la entidad creada a partir del diccionari, y por otro un
        # listado de atributos que existen en la entidad pero que no se han enviado en json. Eso quiere decir que esos
        # atributos no se quieren actualizar.
        result = self.get_main_service().get_entity_type().convert_dict_to_entity(request_object, is_update)
        id_field_name = self.get_main_service().get_entity_type().get_id_field_name()

        if is_update:
            # Primer valor: entidad
            entity = result[0]
            # Si no hay id, lanzar error porque es imprescindible para actualizar
            if getattr(entity, id_field_name) is None:
                raise CustomException(translate("i18n_base_commonError_not_id_in_update"))

            # Segundo valor: listado de valores que no se desea actualizar
            non_updatable_values = result[1]

            # Si hay valores que no se desean actualizar, traer de la base de datos la entidad existente y establecer
            # desde la enviada por json los nuevos valores, dejando el resto iguales.
            if non_updatable_values and len(non_updatable_values) > 0:
                id_value = getattr(entity, id_field_name)

                # Buscar entidad por id
                original_entity = self.get_main_service().select_by_id(id_value)
                # Recorro los campos de la entidad original, y acualizo a partir de la enviada por json sólo aquéllos
                # que se han enviado.
                original_entity_dict = self.get_main_service().get_entity_type().get_model_dict()
                for k in original_entity_dict.keys():
                    if k not in non_updatable_values:
                        setattr(original_entity, k, getattr(entity, k))

                # Devuelvo la entidad original con los campos enviados por json actualizados.
                return original_entity
            else:
                # En caso contrario, devolver la entidad directamente
                return entity
        else:
            return result

    def _resolve_action(self, action: int, request_object: any):
        """
        Método que resuelve la acción a realizar en post a través del RequestBody, en concreto de un int con la acción
        seleccionada. Las implementaciones de RestController que lo necesiten pueden sobrescribir esta función.
        :param action: Entero con una acción a resolver.
        1 -> Crear
        2 -> Actualizar
        3 -> Borrar
        4 -> Seleccionar
        :return: Devuelve bien un mensaje de éxito o error, o si es una select un json con el resultado.
        """
        # Comprobar la acción enviada en la Request
        request_action = EnumPostRequestActions(action)

        # Si request_action distinto de "select", preparar una BaseEntity
        entity = None
        query_object = None
        if request_action != EnumPostRequestActions.SELECT:
            entity = self.__convert_request_object_to_base_entity(request_object,
                                                                  request_action == EnumPostRequestActions.UPDATE)
        else:
            # El objeto QueryObject espera un diccionario como argumento del constructor para inicializar sus atributos
            query_object = JsonQuery(request_object)

        if request_action == EnumPostRequestActions.CREATE:
            result = self._create_with_response(entity)
        elif request_action == EnumPostRequestActions.DELETE:
            result = self._delete_with_response(entity)
        elif request_action == EnumPostRequestActions.UPDATE:
            result = self._update_with_response(entity)
        else:
            result = self._select_with_response(query_object)

        return result

    def post(self):
        """
        Método post de controller rest. NO se recomienda su sobrescritura. Si lo que se desea es
        sobrescribir el comportamiento de RestController, lo mejor es sobrescribir _resolve_action o mejor aún
        _create_with_response, _delete_with_response, _update_with_response o _update_with_response, según proceda.
        :return: Cadena con mensaje formateado para devolver al solicitante.
        """
        try:
            # Obtengo datos json de la petición
            result = self.__resolve_action_outer(request)
            # Devuelvo una respuesta correcta
            response_body = RequestResponse(response_object=result, success=True,
                                            status_code=EnumHttpResponseStatusCodes.OK.value)

            return self._convert_request_response_to_json_response(response_body)
        except CustomException as e:
            # Se produce algún error
            print(str(e))
            # Si hay error conocido, pasarlo en el mensaje de error, sino enviar su representación en forma de string.
            error: str = e.known_error if e.known_error is not None else (str(e.exception) if e.exception is not None
                                                                          else str(e))
            result = translate("i18n_base_commonError_request", None, *[error])

            response_body = RequestResponse(response_object=result, success=False,
                                            status_code=EnumHttpResponseStatusCodes.BAD_REQUEST.value)

            return self._convert_request_response_to_json_response(response_body)
