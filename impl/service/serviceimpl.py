from typing import List

from core.dao.querytools import FilterClause, EnumFilterTypes, FieldClause
from core.service.service import BaseService
from core.util.passwordutils import hash_password_using_bcrypt, check_password_using_bcrypt
from impl.dao.daoimpl import TipoClienteDao, ClienteDao, UsuarioDao
from impl.model.usuario import Usuario


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


class UsuarioService(BaseService):
    """Implementacion de service de usuarios. La herencia se realiza pasando como parámetro la clase padre."""

    # Constructor
    def __init__(self):
        # de esta forma llamo al constructor del padre
        super().__init__(dao=UsuarioDao())

    def check_password(self, usuario: Usuario):
        """
        Comprueba y establece el valor encriptado del password del usuario si es necesario.
        :param usuario:
        :return: None
        """
        if usuario.password is not None:
            # Si el usuario no tiene id significa que aún no se ha creado en la base de datos, con lo cual se
            # establecer el password encriptado directamente
            if usuario.usuario_id is None:
                usuario.password = hash_password_using_bcrypt(usuario.password)
            else:
                # Si tiene id, busco el password antiguo en la base de datos para comprobar si realmente ha cambiado
                # usando el comparador de bcrypt. Dado que bcrypt va a hashear el password de otra forma, no quiero
                # modificar el valor en la base de datos salvo que realmente sea otro password.
                filters: List[FilterClause] = [FilterClause(field_name="usuario_id", filter_type=EnumFilterTypes.EQUALS,
                                                            object_to_compare=usuario.usuario_id)]
                fields: List[FieldClause] = [FieldClause(field_name="password")]
                result: List[Usuario] = self.select(fields=fields, filters=filters, offset=0, limit=1)

                if result and len(result) > 0:
                    usuario_old = result[0]

                    # Si el password del usuario ya estuviese encriptado en este punto, sería igual que el original
                    if usuario.password != usuario_old.password:
                        if not check_password_using_bcrypt(usuario.password, usuario_old.password):
                            usuario.password = hash_password_using_bcrypt(usuario.password)
                        else:
                            # Mantener el password original en caso contrario (el password del usuario es el mismo
                            # pero está desencriptado)
                            usuario.password = usuario_old.password

    def insert(self, entity: Usuario):
        # Sobrescritura de insert para comprobar password
        self.check_password(entity)
        super().insert(entity)

    def update(self, entity: Usuario):
        # Sobrescritura de update para comprobar password
        self.check_password(entity)
        super().update(entity)
