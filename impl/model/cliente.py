# Modelo para tabla clientes
from decimal import Decimal

from core.model.baseentity import BaseEntity
from impl.model.tipocliente import TipoCliente


class Cliente(BaseEntity):
    """Modelo de cliente."""

    # clienteid -> id (no puedo usar el mismo nombre de campo, id es una función interna de python y no se recomienda)
    # llamar a variables de la misma forma

    # Constructor
    def __init__(self, id: int=None, codigo: str=None, nombre: str=None, apellidos: str=None, saldo: Decimal=None,
                 tipo_cliente: TipoCliente = None):
        super().__init__()
        self.id = id
        self.codigo = codigo
        self.nombre = nombre
        self.apellidos = apellidos
        self.saldo = saldo
        self.tipo_cliente = tipo_cliente

    @classmethod
    def convert_dict_to_entity(cls, d: dict):
        """
        Sobrescritura de convert_dict_to_entity para tratar las entidades anidadas. Cuando se convierte de json a
        entidad, las BaseEntities anidadas son dicts. Lo que hay que hacer es ir llamando a convert_dict_to_entity de
        cada una de ellas para ir transformándolas en la clase correcta.
        :param d: Diccionario.
        :return: Cliente
        """
        # Primero convierto el diccionario a cliente
        cliente = super().convert_dict_to_entity(d)

        # En este punto, el tipo de cliente es un diccionario debido a la conversión json. Lo transformo usando
        # el servicio de tipos de cliente.
        # tipo_cliente_service = ServiceFactory.get_service(TipoClienteService)
        # cliente.tipo_cliente = tipo_cliente_service.convert_dict_to_entity(cliente.tipo_cliente)
        if cliente.tipo_cliente is not None:
            cliente.tipo_cliente = TipoCliente.convert_dict_to_entity(cliente.tipo_cliente)

        return cliente

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
