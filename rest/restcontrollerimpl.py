from core.exception.exceptionhandler import ServiceException
from core.rest.restcontroller import RestController
from core.service.service import ServiceFactory
from core.util import i18n
from model.tipocliente import TipoCliente
from service.tipoclienteservice import TipoClienteService


# Hereda de Resource de flask_restful
class TipoClienteRestController(RestController):
    """Rest controller para tipos de cliente."""

    def _create_with_response(self, request_object: dict):
        try:
            # deserializo el request_object (es un diccionario) y lo convierto a tipo de cliente
            tipo_cliente = TipoCliente(**request_object)
            # Inserto el tipo de cliente
            tipo_cliente_service = ServiceFactory.get_service(TipoClienteService)
            # Importante llamar la función dentro de una transacción
            tipo_cliente_service.start_transaction(tipo_cliente_service.insert, tipo_cliente)

            return i18n.translate("i18n_base_common_insert_success", None, *[str(tipo_cliente)])
        except ServiceException as e:
            raise e

    def _delete_with_response(self, request_object: dict):
        pass

    def _update_with_response(self, request_object: dict):
        pass
