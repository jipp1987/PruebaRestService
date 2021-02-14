from decimal import Decimal
from typing import Dict

from core.model.modeldefinition import BaseEntity, FieldDefinition
from impl.model.tipocliente import TipoCliente
from impl.model.usuario import Usuario


class Cliente(BaseEntity):
    """Modelo de cliente."""

    # clienteid -> id (no puedo usar el mismo nombre de campo, id es una función interna de python y no se recomienda)
    # llamar a variables de la misma forma
    # Diccionario valores modelo
    __model_dict: Dict[str, FieldDefinition] = {
        'cliente_id': FieldDefinition(field_type=int, name_in_db='id', is_primary_key=True, is_mandatory=True),
        'codigo': FieldDefinition(field_type=str, name_in_db='codigo', length_in_db=10, is_mandatory=True),
        'nombre': FieldDefinition(field_type=str, name_in_db='nombre', length_in_db=50, is_mandatory=True),
        'apellidos': FieldDefinition(field_type=str, name_in_db='apellidos', length_in_db=120),
        'saldo': FieldDefinition(field_type=Decimal, name_in_db='saldo', range_in_db=(6, 2), is_mandatory=True,
                                 default_value=Decimal(str('0'))),
        'tipo_cliente': FieldDefinition(field_type=TipoCliente, name_in_db='tipoclienteid', is_mandatory=True,
                                        referenced_table_name='tiposcliente'),
        'usuario_creacion': FieldDefinition(field_type=Usuario, name_in_db='usuariocreacionid', is_mandatory=False,
                                            referenced_table_name='usuarios'),
        'usuario_ult_mod': FieldDefinition(field_type=Usuario, name_in_db='usuarioultmodid', is_mandatory=False,
                                           referenced_table_name='usuarios')
    }
    """Diccionario con los datos de los campos del modelo."""

    # Constructor
    def __init__(self, cliente_id: int, codigo: str, nombre: str,
                 saldo: Decimal, tipo_cliente: TipoCliente, apellidos: str = None, usuario_creacion: Usuario = None,
                 usuario_ult_mod: Usuario = None):
        super().__init__()
        self.cliente_id = cliente_id
        """Id del cliente."""
        self.codigo = codigo
        """Código único."""
        self.nombre = nombre
        """Nombre del cliente."""
        self.saldo = saldo
        """Saldo del cliente."""
        self.tipo_cliente = tipo_cliente
        """Tipo de cliente."""
        self.apellidos = apellidos
        """Apellidos."""
        self.usuario_creacion = usuario_creacion
        """Usuario de creación."""
        self.usuario_ult_mod = usuario_ult_mod
        """Usuario de última modificación."""

    # PROPIEDADES Y SETTERS
    @property
    def cliente_id(self):
        return self.__cliente_id

    @cliente_id.setter
    def cliente_id(self, cliente_id):
        self.__cliente_id = cliente_id

    @property
    def codigo(self):
        return self.__codigo

    @codigo.setter
    def codigo(self, codigo):
        self.__codigo = codigo

    @property
    def nombre(self):
        return self.__nombre

    @nombre.setter
    def nombre(self, nombre):
        self.__nombre = nombre

    @property
    def apellidos(self):
        return self.__apellidos

    @apellidos.setter
    def apellidos(self, apellidos):
        self.__apellidos = apellidos

    @property
    def saldo(self):
        return self.__saldo

    @saldo.setter
    def saldo(self, saldo):
        # Si no es Decimal transformarlo: mejor pasarlo primero a String y de String a decimal para evitar pérdida de
        # preción decimal.
        if saldo is not None:
            self.__saldo = saldo if isinstance(saldo, Decimal) else Decimal(str(saldo))
        else:
            self.__saldo = None

    @property
    def tipo_cliente(self):
        return self.__tipo_cliente

    @tipo_cliente.setter
    def tipo_cliente(self, tipo_cliente):
        self.__tipo_cliente = tipo_cliente

    @property
    def usuario_creacion(self):
        return self.__usuario_creacion

    @usuario_creacion.setter
    def usuario_creacion(self, usuario_creacion):
        self.__usuario_creacion = usuario_creacion

    @property
    def usuario_ult_mod(self):
        return self.__usuario_ult_mod

    @usuario_ult_mod.setter
    def usuario_ult_mod(self, usuario_ult_mod):
        self.__usuario_ult_mod = usuario_ult_mod

    # FUNCIONES
    @classmethod
    def get_id_field_name(cls) -> str:
        return 'cliente_id'

    # equals: uso el id para saber si es el mismo cliente
    def __eq__(self, other):
        # Primero se comprueba que sea una instancia de la misma clase o de una subclase
        if isinstance(other, self.__class__):
            # El id es el campo que me dice si es el mismo
            # Hay una función interna, __dict__, que serían todos los atributos modificables del objeto,
            # pero en este caso al ser un modelo de la base de datos me quedo con el id
            return self.cliente_id == other.cliente_id
        else:
            return False

    # not equals: uso el id
    # se supone que en python3 esto no es necesario, si eq está sobrescrito en la clase ne lo que hace es usarlo,
    # pero yo lo pongo para saber que existe a modo de ejemplo
    def __ne__(self, other):
        return not self.__eq__(other)

    # hashcode. Devuelve un entero en base a una/s propiedad/es para mejorar la búsqueda del objeto en cuestión
    # en diccionarios. Para añadir un objeto aun diccionario es imprescindible que sea hasheable, es decir, que tenga
    # implementadas las funciones __eq__ y __hash__. Esto implica en el momemento en que se añade el objeto a un
    # conjunto como un diccionario, set... no puede cambiar su valor clave que se emplea en el hash
    def __hash__(self):
        # En este caso uso el mismo atributo que para el hash
        return hash(self.cliente_id)

    # función para representar como string el objeto
    def __repr__(self):
        # esto es una nueva forma en python3 de dar formato a un string, es mejor esto que concatenar cadenas,
        # sobretodo porque si le intentamos concatenar a una cadena un campo no string lanzará error durante
        # la ejecución
        return f'cliente_id = {self.cliente_id}, codigo = {self.codigo}, (tipo de cliente = {str(self.tipo_cliente)})'
