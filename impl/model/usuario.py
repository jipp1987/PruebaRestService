from typing import Dict

from core.model.modeldefinition import FieldDefinition, BaseEntity


class Usuario(BaseEntity):
    """Modelo de usuario."""

    # Diccionario valores modelo
    __model_dict: Dict[str, FieldDefinition] = {
        'usuario_id': FieldDefinition(field_type=int, name_in_db='id', is_primary_key=True, is_mandatory=True),
        'username': FieldDefinition(field_type=str, name_in_db='username', length_in_db=80, is_mandatory=True),
        'password': FieldDefinition(field_type=str, name_in_db='password', length_in_db=60, is_mandatory=True)
    }
    """Diccionario con los datos de los campos del modelo."""

    # Constructor
    def __init__(self, usuario_id: int, username: str, password: str):
        super().__init__()
        self.usuario_id = usuario_id
        """Id del usuario."""
        self.username = username
        """Nombre único del usuario."""
        self.password = password
        """Password."""

    # PROPIEDADES Y SETTERS
    @property
    def usuario_id(self):
        return self.__usuario_id

    @usuario_id.setter
    def usuario_id(self, usuario_id):
        self.__usuario_id = usuario_id

    @property
    def username(self):
        return self.__username

    @username.setter
    def username(self, username: str):
        self.__username = username

    @property
    def password(self):
        return self.__password

    @password.setter
    def password(self, password):
        self.__password = password

    # FUNCIONES
    @classmethod
    def get_id_field_name(cls) -> str:
        return 'usuario_id'

    # equals: uso el id para saber si es el mismo tipo de cliente
    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.usuario_id == other.usuario_id
        else:
            return False

    # not equals
    def __ne__(self, other):
        return not self.__eq__(other)

    # hashcode
    def __hash__(self):
        # En este caso uso el mismo atributo que para el hash
        return hash(self.usuario_id)

    # tostring
    def __repr__(self):
        return f'usuario_id = {self.usuario_id}, username = {self.username}'
