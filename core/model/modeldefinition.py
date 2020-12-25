import abc
from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass(repr=True, init=False)
class FieldDefinition(object):
    """Clase para definir los campos del modelo respecto a sus equivalentes en la base de datos."""

    def __init__(self, field_type: type, name_in_db: str, is_primary_key: bool = False, is_mandatory: bool = False,
                 length_in_db: int = None, range_in_db: Tuple[int, int] = None, referenced_table_name: str = None,
                 default_value: any = None):
        """
        :param field_type: Tipo de campo esperado en python.
        :param name_in_db: Nombre del campo en la base de datos.
        :param is_primary_key: Es o no la clave primaria.
        :param is_mandatory: Es o no campo obligatorio.
        :param length_in_db: Tamaño del campo esperado en la base de datos.
        :param range_in_db: Rango del campo. Pensado para números decimales.
        :param referenced_table_name: Nombre de tabla referenciada en caso de que sea una clave foránea.
        :param default_value: Valor por defecto.
        """
        self.field_type: type = field_type
        self.name_in_db: str = name_in_db
        self.is_primary_key: bool = is_primary_key
        self.is_mandatory: bool = is_mandatory
        self.length_in_db: int = length_in_db
        self.range_in_db: Tuple[int, int] = range_in_db
        self.referenced_table_name: str = referenced_table_name
        self.default_value: any = default_value


class BaseEntity(object, metaclass=abc.ABCMeta):
    """Entidad base de la que han de extender todos los objetos persistidos en la base de datos."""

    @classmethod
    def convert_dict_to_entity(cls, d: dict):
        """
        Convierte un diccionario en una entidad base, siendo la clave el nombre de cada campo. Por defecto, lo que
        hace es descomponer el diccionario pasado como parámetro y usar los pares clave-valor obtenidos como argumentos
        del contructor de la entidad base. Es posible que haya que implementar esta función en caso de que la entidad
        tenga otras BaseEntity anidadas, en ese caso lo mejor es ir llamando a convert_dict_to_entity de esas entidades.
        :param d: Diccionario con el atributo y valor de los campos de la entidad base.
        :return: Instancia de la entidad base con los atributos indicados en el diccionario.
        """
        # En este caso, de forma genérica, lo que hago es descomponer el diccionario en pares clave-valor con el
        # operador **. Lo que va a hacer es ir al constructor del objeto y sustituir los argumentos de éste por los
        # pares obtenidos.
        # La siguiente línea es para ignorar un warning de parámetro inesperado que no me interesa.
        # noinspection PyArgumentList
        entity = cls(**d)

        # Voy a iterar sobre los valores del objeto en función del diccionario de valores del modelo
        # Lo hago porque al transformar un diccionario en un modelo, si tiene otro modelo anidado éste sigue siendo
        # un diccionario tras la transformación, con lo cual lo que hay que hacer es llamar de forma recursiva a esta
        # función para tranformar todos los modelos anidados en objetos BaseEntity
        for key, value in entity.get_model_dict().items():
            # El valor de la clave es un objeto FieldDefinition.
            entity_type = value.field_type

            # Compruebo si el tipo hereda de BaseEntity
            if issubclass(entity_type, BaseEntity):
                other_entity = getattr(entity, key)

                # si es el valor es un diccionario, llamo de forma recursiva a esta función para transformarlo
                if isinstance(other_entity, dict):
                    # Al llamarse de forma recursiva, se irán transformando también los objetos anidados que tenga
                    # el diccionario
                    setattr(entity, key, entity_type.convert_dict_to_entity(other_entity))

        return entity

    @abc.abstractmethod
    def get_id_field_name(self) -> str:
        """
        Devuelve el nombre del campo id.
        :return: str
        """
        pass

    @abc.abstractmethod
    def get_model_dict(self) -> Dict[str, FieldDefinition]:
        """
        Devuelve un diccionario siendo la clave un String con el nombre del campo del modelo en Python, y el valor
        un objeto FieldDefinition con la definición del campo teniendo en cuenta el modelo de la base de datos.
        :return: Dict[str, Tuple[any, FieldDefinition]
        """
        pass

    def to_json(self) -> Dict[str, any]:
        """Serializa la entidad a json."""
        # Devuelvo un diccionario sólo con los valores del correspondiente al modelo de datos.
        json_dict = {}

        d = self.get_model_dict()
        v: any
        for key, value in d.items():
            # Codifico cada valor a json (compruebo si ya tiene una función to_json)
            v = getattr(self, key)
            json_dict[key] = v.to_json() if hasattr(v, "to_json") else v

        return json_dict

    def get_field_names_as_str(self):
        """
        Devuelve una cadena con los nombres de los campos separados por comas.
        :return: Una cadena de los campos de la entidad cuyo primer valor será el campo del id.
        """
        cadena: str = self.get_id_field_name()

        # Recorrer los nombres de los campos del objeto e ir concatenándolos separados por comas
        d = self.get_model_dict()
        for key, value in d.items():
            # key es un string con el nombre del campo dentro del objeto.
            # Value es una objeto de tipo FieldDefinition
            if key != self.get_id_field_name():
                cadena += ", " + value.name_in_db

        return cadena

    def get_field_values_as_str(self, is_id_included: bool = False):
        """
        Devuelve una cadena con los valores de los campos de la entidad encadenados por comas
        :param is_id_included: Si True, empieza por el valor del campo id; si False, empieza con "null". False
        por defecto.
        :return: str
        """
        # Si 'is_id_included', incluyo el valor del campo id, sino pongo null. Útil pasarlo como False para inserts
        cadena = getattr(self, self.get_id_field_name()) if is_id_included else "null"

        # Recorrer los nombres de los campos del objeto e ir concatenándolos separados por comas
        d = self.get_model_dict()

        for key, value in d.items():
            # key es un string con el nombre del campo dentro del objeto.
            # Value es un objeto de tipo FieldDefinition
            if key != self.get_id_field_name():
                v = getattr(self, key)

                # Hay que comprobar si el campo es de tipo BaseEntity, en ese caso habrá que usar el campo id de éste
                # como valor
                if issubclass(value.field_type, BaseEntity):
                    # Con esto obtengo el valor del id del campo referenciado
                    v = getattr(v, v.get_id_field_name())

                # Si es un str, encerrarlo entre comillas simples
                if isinstance(v, str):
                    cadena += ", '" + str(v) + "'"
                else:
                    cadena += ", " + str(v)

        return cadena

    def get_fields_with_value_as_str(self):
        """
        Devuelve una cadena con los valores del objeto a modo de "atributo = valor" separados por ", "
        :return: str
        """
        # Empiezo por el id
        cadena = f'{self.get_id_field_name()} = {getattr(self, self.get_id_field_name())}'

        # Recorrer los nombres de los campos del objeto e ir concatenándolos separados por comas
        d = self.get_model_dict()

        # Completo con el resto
        for key, value in d.items():
            # key es un string con el nombre del campo dentro del objeto.
            # Value es un objeto de tipo FieldDefinition
            if key != self.get_id_field_name():
                v = getattr(self, key)

                # Hay que comprobar si el campo es de tipo BaseEntity, en ese caso habrá que usar el campo id de éste
                # como valor
                if issubclass(value.field_type, BaseEntity):
                    # Con esto obtengo el valor del id del campo referenciado
                    v = getattr(v, v.get_id_field_name())

                # Si es un str, encerrarlo entre comillas simples
                if isinstance(v, str):
                    cadena = f"{cadena} , {value.name_in_db} = '{v}'"
                else:
                    cadena = f"{cadena} , {value.name_in_db} = {v}"

        return cadena
