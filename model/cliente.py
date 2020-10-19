# Modelo para tabla clientes
from core.model.BaseEntity import BaseEntity
from model.tipocliente import TipoCliente


class Cliente(BaseEntity):
    """Modelo de cliente."""

    # clienteid -> id (no puedo usar el mismo nombre de campo, id es una función interna de python y no se recomienda)
    # llamar a variables de la misma forma

    # Constructor
    def __init__(self, dbid=None, codigo=None, nombre=None, apellidos=None, saldo=None):
        super().__init__()
        self.id = dbid
        self.codigo = codigo
        self.nombre = nombre
        self.apellidos = apellidos
        self.saldo = saldo
        self.tipocliente = TipoCliente()

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
        return f'id = {self.id}, codigo = {self.codigo}, (tipo de cliente = {self.tipocliente})'
