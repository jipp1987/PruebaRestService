from core.model.baseentity import BaseEntity


class TipoCliente(BaseEntity):
    """Modelo de tipo de cliente."""

    # Constructor
    def __init__(self, id: int=None, codigo: str=None, descripcion: str=None):
        super().__init__()
        self.id = id
        self.codigo = codigo
        self.descripcion = descripcion

    # PROPIEDADES Y SETTERS
    @property
    def id(self):
        return self.__id

    @id.setter
    def id(self, id):
        self.__id = id if id is not None and id > 0 else None

    @property
    def codigo(self):
        return self.__codigo

    @codigo.setter
    def codigo(self, codigo):
        self.__codigo = codigo

    @property
    def descripcion(self):
        return self.__descripcion

    @descripcion.setter
    def descripcion(self, descripcion):
        self.__descripcion = descripcion

    # FUNCIONES
    # equals: uso el id para saber si es el mismo tipo de cliente
    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.id == other.id
        else:
            return False

    # not equals
    def __ne__(self, other):
        return not self.__eq__(other)

    # hashcode
    def __hash__(self):
        # En este caso uso el mismo atributo que para el hash
        return hash(self.id)

    # tostring
    def __repr__(self):
        return f'id = {self.id}, codigo = {self.codigo}'
