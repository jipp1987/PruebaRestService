from typing import Dict

from core.model.modeldefinition import BaseEntity, FieldDefinition


class TipoCliente(BaseEntity):
    """Modelo de tipo de cliente."""

    # Diccionario valores modelo
    __model_dict: Dict[str, FieldDefinition] = {
        'tipo_cliente_id': FieldDefinition(field_type=int, name_in_db='id', is_primary_key=True, is_mandatory=True),
        'codigo': FieldDefinition(field_type=str, name_in_db='codigo', length_in_db=4, is_mandatory=True),
        'descripcion': FieldDefinition(field_type=str, name_in_db='descripcion', length_in_db=50, is_mandatory=True),
    }
    """Diccionario con los datos de los campos del modelo."""

    # Constructor
    def __init__(self, tipo_cliente_id: int = None, codigo: str = None, descripcion: str = None):
        super().__init__()
        self.tipo_cliente_id = tipo_cliente_id
        self.codigo = codigo
        self.descripcion = descripcion

    # PROPIEDADES Y SETTERS
    @property
    def tipo_cliente_id(self):
        return self.__tipo_cliente_id

    @tipo_cliente_id.setter
    def tipo_cliente_id(self, tipo_cliente_id):
        self.__tipo_cliente_id = tipo_cliente_id

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
    @classmethod
    def get_model_dict(cls):
        return cls.__model_dict

    @classmethod
    def get_id_field_name_in_db(cls) -> str:
        return cls.__model_dict.get('tipo_cliente_id').name_in_db

    @classmethod
    def get_id_field_name(cls) -> str:
        return 'tipo_cliente_id'

    # equals: uso el id para saber si es el mismo tipo de cliente
    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.tipo_cliente_id == other.tipo_cliente_id
        else:
            return False

    # not equals
    def __ne__(self, other):
        return not self.__eq__(other)

    # hashcode
    def __hash__(self):
        # En este caso uso el mismo atributo que para el hash
        return hash(self.tipo_cliente_id)

    # tostring
    def __repr__(self):
        return f'tipo_cliente_id = {self.tipo_cliente_id}, codigo = {self.codigo}'
