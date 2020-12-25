from core.service.service import BaseService
from impl.dao.daoimpl import TipoClienteDao, ClienteDao
from impl.model.cliente import Cliente
from impl.model.tipocliente import TipoCliente


class TipoClienteService(BaseService):
    """Implementacion de service de tiposcliente. La herencia se realiza pasando como parámetro la clase padre."""

    # Constructor
    def __init__(self):
        # de esta forma llamo al constructor del padre
        super().__init__(dao=TipoClienteDao())


class ClienteService(BaseService):
    """Implementacion de service de clientes. La herencia se realiza pasando como parámetro la clase padre."""

    # Constructor
    def __init__(self):
        # de esta forma llamo al constructor del padre
        super().__init__(dao=ClienteDao())
