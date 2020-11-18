from core.model.baseentity import BaseEntity
from core.service.service import BaseService, ServiceFactory
from dao.daoimpl import TipoClienteDao, ClienteDao
from model.cliente import Cliente
from model.tipocliente import TipoCliente


class TipoClienteService(BaseService):
    """Implementacion de service de tiposcliente. La herencia se realiza pasando como parámetro la clase padre."""

    # Constructor
    def __init__(self):
        # de esta forma llamo al constructor del padre
        super().__init__(TipoClienteDao())

    def get_main_entity_type(self):
        return TipoCliente


class ClienteService(BaseService):
    """Implementacion de service de clientes. La herencia se realiza pasando como parámetro la clase padre."""

    # Constructor
    def __init__(self):
        # de esta forma llamo al constructor del padre
        super().__init__(ClienteDao())

    def get_main_entity_type(self):
        return Cliente

    def convert_dict_to_entity(self, request_object_dict: dict) -> BaseEntity:
        # Primero convierto el diccionario a cliente
        cliente = super().convert_dict_to_entity(request_object_dict)

        # En este punto, el tipo de cliente es un diccionario debido a la conversión json. Lo transformo usando
        # el servicio de tipos de cliente.
        tipo_cliente_service = ServiceFactory.get_service(TipoClienteService)
        cliente.tipo_cliente = tipo_cliente_service.convert_dict_to_entity(cliente.tipo_cliente)

        return cliente
