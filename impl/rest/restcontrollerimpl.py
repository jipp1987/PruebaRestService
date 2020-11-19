from core.rest.restcontroller import RestController
from core.service.service import ServiceFactory
from impl.service.serviceimpl import TipoClienteService, ClienteService


class TipoClienteRestController(RestController):
    """Rest controller para tipos de cliente."""

    def get_main_service(self):
        return ServiceFactory.get_service(TipoClienteService)


class ClienteRestController(RestController):
    """Rest controller para tipos de cliente."""

    def get_main_service(self):
        return ServiceFactory.get_service(ClienteService)
