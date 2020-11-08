from core.service.service import BaseService
from dao.daoimpl import TipoClienteDao
from model.tipocliente import TipoCliente


class TipoClienteService(BaseService[TipoCliente]):
    """Implementacion de service de tiposcliente. La herencia se realiza pasando como parámetro la clase padre."""

    # Constructor
    def __init__(self):
        # de esta forma llamo al constructor del padre
        super().__init__(TipoClienteDao())
