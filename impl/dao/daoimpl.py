from core.dao.basedao import BaseDao
from impl.model.cliente import Cliente
from impl.model.tipocliente import TipoCliente
from impl.model.usuario import Usuario


class TipoClienteDao(BaseDao):
    """Implementacion de Dao de tiposcliente. La herencia se realiza pasando como parámetro la clase padre."""

    # Constructor
    def __init__(self):
        # de esta forma llamo al constructor del padre
        super().__init__(table="tiposcliente", entity_type=TipoCliente)


class ClienteDao(BaseDao):
    """Implementacion de Dao de clientes. La herencia se realiza pasando como parámetro la clase padre."""

    # Constructor
    def __init__(self):
        # de esta forma llamo al constructor del padre
        super().__init__(table="clientes", entity_type=Cliente)


class UsuarioDao(BaseDao):
    """Implementacion de Dao de usuarios. La herencia se realiza pasando como parámetro la clase padre."""

    # Constructor
    def __init__(self):
        # de esta forma llamo al constructor del padre
        super().__init__(table="usuarios", entity_type=Usuario)
