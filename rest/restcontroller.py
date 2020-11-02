import json
from types import SimpleNamespace

from flask import request

from core.exception.exceptionhandler import CustomException
from core.rest.restcontroller import CustomResource, RequestActions
from core.service.service import ServiceFactory
from core.util import i18n
from model.tipocliente import TipoCliente
from service.tipoclienteservice import TipoClienteService


# Hereda de Resource de flask_restful
class TipoClienteRestController(CustomResource):
    """Rest controller para tipos de cliente."""

    def _create_with_response(self, tipo_cliente: TipoCliente):
        try:
            # Inserto el tipo de cliente
            tipo_cliente_service = ServiceFactory.get_service(TipoClienteService)
            # Importante llamar la función dentro de una transacción
            tipo_cliente_service.start_transaction(tipo_cliente_service.insert, tipo_cliente)
        except CustomException as e:
            raise e

    def _delete_with_response(self, tipo_cliente: TipoCliente):
        pass

    def _update_with_response(self, tipo_cliente: TipoCliente):
        pass

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
            request_action = RequestActions(request_body.action)

            if request_action == RequestActions.CREATE:
                tipo_cliente = request_body.request_object
                self._create_with_response(tipo_cliente)
                result = i18n.translate("i18n_base_common_insert_success", None, *[str(tipo_cliente)])

            return result
        except CustomException as e:
            return i18n.translate("i18n_base_commonError_request", None, *[e.known_error])
