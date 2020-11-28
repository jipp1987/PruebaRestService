from typing import Dict

from core.model.modeldefinition import BaseEntity, FieldDefinition


class TipoCliente(BaseEntity):
    """Modelo de tipo de cliente."""

    # Diccionario valores modelo
    __model_dict: Dict[str, FieldDefinition] = {
        'id': FieldDefinition(field_type=int, name_in_db='id', is_primary_key=True, is_mandatory=True),
        'codigo': FieldDefinition(field_type=str, name_in_db='codigo', length_in_db=4, is_mandatory=True),
        'descripcion': FieldDefinition(field_type=str, name_in_db='descripcion', length_in_db=50, is_mandatory=True),
    }
    """Diccionario con los datos de los campos del modelo."""

    # Constructor
    def __init__(self, id: int = None, codigo: str = None, descripcion: str = None):
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
        self.__id = id

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
    def get_model_dict(self):
        return TipoCliente.__model_dict

    def get_id_field_name(self) -> str:
        return TipoCliente.__model_dict.get('id').name_in_db

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
