from core.model.BaseEntity import BaseEntity


class TipoCliente(BaseEntity):
    """Modelo de tipo de cliente."""

    # Constructor
    def __init__(self, dbid=None, codigo=None, descripcion=None):
        super().__init__()
        self.id = dbid
        self.codigo = codigo
        self.descripcion = descripcion

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
