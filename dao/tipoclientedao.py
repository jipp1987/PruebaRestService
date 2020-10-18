from core.dao.basedao import BaseDao
from model.tipocliente import TipoCliente


class TipoClienteDao(BaseDao[TipoCliente]):
    """Implementacion de Dao de tiposcliente. La herencia se realiza pasando como parámetro la clase padre."""

    # Constructor
    def __init__(self):
        # de esta forma llamo al constructor del padre
        super().__init__("tiposcliente")