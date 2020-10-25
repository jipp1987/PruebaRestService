from flask import request
from flask_restful import Resource

from core.exception.exceptionhandler import CustomException
from core.service.service import ServiceFactory
from core.util import i18n
from model.tipocliente import TipoCliente
from service.tipoclienteservice import TipoClienteService


# Hereda de Resource de flask_restful
class TipoClienteRestController(Resource):
    """Rest controller para tipos de cliente."""

    def post(self):
        """
        Método post de controller rest de tipos de cliente.
        :return: Cadena con mensaje formateado para devolver al solicitante.
        """
        # Obtengo datos json de la petición
        req_data = request.get_json()
        codigo = req_data['codigo']
        descripcion = req_data['descripcion']

        try:
            # Inserto el tipo de cliente
            tipo_cliente = TipoCliente(None, codigo, descripcion)
            tipo_cliente_service = ServiceFactory.get_service(TipoClienteService)

            # Importante llamar la función dentro de una transacción
            tipo_cliente_service.start_transaction(tipo_cliente_service.insert, tipo_cliente)

            return i18n.translate("i18n_base_common_insert_success", None, *[str(tipo_cliente)])
        except CustomException as e:
            return i18n.translate("i18n_base_commonError_request", None, *[e.known_error])
