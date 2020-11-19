# Modelo para tabla clientes
from decimal import Decimal

from core.model.baseentity import BaseEntity
from impl.model.tipocliente import TipoCliente


class Cliente(BaseEntity):
    """Modelo de cliente."""

    # clienteid -> id (no puedo usar el mismo nombre de campo, id es una función interna de python y no se recomienda)
    # llamar a variables de la misma forma

    # Constructor
    def __init__(self, id: int = None, codigo: str = None, nombre: str = None, apellidos: str = None,
                 saldo: Decimal = None,
                 tipo_cliente: TipoCliente = None):
        super().__init__()
        self.id = id
        self.codigo = codigo
        self.nombre = nombre
        self.apellidos = apellidos
        self.saldo = saldo
        self.tipo_cliente = tipo_cliente

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
        # Si tipo de cliente es un diccionario, pasar de diccionario a entidad según la clase tipo de cliente. Puede
        # venir como diccionario por ejemplo desde una conversión desde json.
        self.__tipo_cliente = TipoCliente.convert_dict_to_entity(tipo_cliente) \
            if tipo_cliente is not None and isinstance(tipo_cliente, dict) else tipo_cliente

    # FUNCIONES
    # equals: uso el id para saber si es el mismo cliente
    def __eq__(self, other):
        # Primero se comprueba que sea una instancia de la misma clase o de una subclase
        if isinstance(other, self.__class__):
            # El id es el campo que me dice si es el mismo
            # Hay una función interna, __dict__, que serían todos los atributos modificables del objeto,
            # pero en este caso al ser un modelo de la base de datos me quedo con el id
            return self.id == other.id
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
        return hash(self.id)

    # función para representar como string el objeto
    def __repr__(self):
        # esto es una nueva forma en python3 de dar formato a un string, es mejor esto que concatenar cadenas,
        # sobretodo porque si le intentamos concatenar a una cadena un campo no string lanzará error durante
        # la ejecución
        return f'id = {self.id}, codigo = {self.codigo}, (tipo de cliente = {str(self.tipo_cliente)})'
