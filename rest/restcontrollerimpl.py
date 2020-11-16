from core.rest.restcontroller import RestController
from core.service.service import ServiceFactory
from model.tipocliente import TipoCliente
from service.serviceimpl import TipoClienteService, ClienteService


# Hereda de Resource de flask_restful
class TipoClienteRestController(RestController):
    """Rest controller para tipos de cliente."""

    def get_main_service(self):
        return ServiceFactory.get_service(TipoClienteService)


# Hereda de Resource de flask_restful
class ClienteRestController(RestController):
    """Rest controller para tipos de cliente."""

    def get_main_service(self):
        return ServiceFactory.get_service(ClienteService)
