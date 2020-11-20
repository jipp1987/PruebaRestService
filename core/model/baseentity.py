import abc
from typing import Dict, Tuple


class BaseEntity(metaclass=abc.ABCMeta):
    """Entidad base de la que han de extender todos los objetos persistidos en la base de datos."""

    def __init__(self, id_field_name: str = "id"):
        """
        Constructor.
        :param id_field_name: Nombre del campo que contiene el id. Por defecto es "id".
        """
        super().__init__()
        self.id_field_name = id_field_name

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
        entity = cls(**d)

        # Voy a iterar sobre los valores del objeto en función del diccionario de valores del modelo
        # Lo hago porque al transformar un diccionario en un modelo, si tiene otro modelo anidado éste sigue siendo
        # un diccionario tras la transformación, con lo cual lo que hay que hacer es llamar de forma recursiva a esta
        # función para tranformar todos los modelos anidados en objetos BaseEntity
        for key, value in entity.get_model_dict().items():
            # El valor de la clave es una tupla con el tipo de dato y el nombre del campo en la base de datos
            # Cojo el primer valor de la tupla, que es el tipo del campo
            entity_type = value[0]

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
    def get_model_dict(self) -> Dict[str, Tuple[type, str]]:
        """
        Devuelve un diccionario siendo la clave un String con el nombre del campo del modelo en Python, y el valor
        una tupla con el tipo de objeto que le corresponde en el modelo Python y un String con el nombre del campo
        en la base de datos.
        :return: Dict[str, Tuple[any, str]
        """
        pass

    def get_field_names_as_str(self):
        """
        Devuelve una cadena con los nombres de los campos separados por comas.
        :return: Una cadena de los campos de la entidad cuyo primer valor será el campo del id.
        """
        cadena = self.id_field_name
        # Recorrer los nombres de los campos del objeto e ir concatenándolos separados por comas
        for key in self.__dict__.keys():
            # Descartar el campo que almacena el nombre del campo "id"
            if str(key) != "idfieldname" and str(key) != self.id_field_name:
                cadena = cadena + ", " + str(key)

        return cadena

    def get_field_values_as_str(self, is_id_included: bool = False):
        """
        Devuelve una cadena con los valores de los campos de la entidad encadenados por comas
        :param is_id_included: Si True, empieza por el valor del campo id; si False, empieza con "null". False
        por defecto.
        :return: str
        """
        # Si 'is_id_included', incluyo el valor del campo id, sino pongo null. Útil pasarlo como False para inserts
        cadena = getattr(self, self.id_field_name) if is_id_included else "null"

        # Recorrer el resto de campos e ir encadenando su valor
        for key in self.__dict__.keys():
            # Descartar el campo que almacena el nombre del campo "id"
            if str(key) != "idfieldname" and str(key) != self.id_field_name:
                cadena = cadena + ", '" + str(getattr(self, str(key))) + "'"

        return cadena

    def get_fields_with_value_as_str(self):
        """
        Devuelve una cadena con los valores del objeto a modo de "atributo = valor" separados por ", "
        :return: str
        """
        # Empiezo por el id
        cadena = f'{self.id_field_name} = {getattr(self, self.id_field_name)}'

        # Completo con el resto
        for attr, value in self.__dict__.items():
            # Descartar el campo que almacena el nombre del campo "id"
            if str(attr) != "idfieldname" and str(attr) != self.id_field_name:
                # Si el valor es otro BaseEntity significa que es una entidad asociada mediante foreign key.
                if isinstance(value, BaseEntity):
                    # En el mapping de la entidad, el nombre del atributo será siempre el nombre de la clase seguido
                    # de "id"
                    cadena = f"{cadena} , {str(attr)}id = {getattr(value, value.id_field_name)}"
                else:
                    cadena = f"{cadena} , {str(attr)} = '{value}'"

        return cadena
