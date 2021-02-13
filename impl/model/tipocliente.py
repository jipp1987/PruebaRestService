from typing import Dict

from core.model.modeldefinition import BaseEntity, FieldDefinition
from impl.model.usuario import Usuario


class TipoCliente(BaseEntity):
    """Modelo de tipo de cliente."""

    # Diccionario valores modelo
    __model_dict: Dict[str, FieldDefinition] = {
        'tipo_cliente_id': FieldDefinition(field_type=int, name_in_db='id', is_primary_key=True, is_mandatory=True),
        'codigo': FieldDefinition(field_type=str, name_in_db='codigo', length_in_db=4, is_mandatory=True),
        'descripcion': FieldDefinition(field_type=str, name_in_db='descripcion', length_in_db=50, is_mandatory=True),
        'usuario_creacion': FieldDefinition(field_type=Usuario, name_in_db='usuariocreacionid', is_mandatory=False,
                                            referenced_table_name='usuarios'),
        'usuario_ult_mod': FieldDefinition(field_type=Usuario, name_in_db='usuarioultmodid', is_mandatory=False,
                                           referenced_table_name='usuarios')
    }
    """Diccionario con los datos de los campos del modelo."""

    # Constructor
    def __init__(self, tipo_cliente_id: int, codigo: str, descripcion: str, usuario_creacion: Usuario = None,
                 usuario_ult_mod: Usuario = None):
        super().__init__()
        self.tipo_cliente_id = tipo_cliente_id
        """Id del tipo de cliente."""
        self.codigo = codigo
        """Código único del tipo de cliente."""
        self.descripcion = descripcion
        """Descripción."""
        self.usuario_creacion = usuario_creacion
        """Usuario de creación."""
        self.usuario_ult_mod = usuario_ult_mod
        """Usuario de última modificación."""

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

    @property
    def usuario_creacion(self):
        return self.usuario_creacion

    @usuario_creacion.setter
    def usuario_creacion(self, usuario_creacion):
        self.__usuario_creacion = usuario_creacion

    @property
    def usuario_ult_mod(self):
        return self.usuario_ult_mod

    @usuario_ult_mod.setter
    def usuario_ult_mod(self, usuario_ult_mod):
        self.__usuario_ult_mod = usuario_ult_mod

    # FUNCIONES
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
