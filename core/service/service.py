import abc

from core.dao.basedao import BaseDao
from core.exception.exceptionhandler import BugBarrier
from core.model.baseentity import BaseEntity
from core.util.noconflict import makecls


class BaseService:
    """
    Clase abstract de la que han de heredar el resto de servicios del programa.
    """
    # Llamo a la factoría de metaclases para que me "fusione" las dos metaclases que me interesan.
    __metaclass__ = makecls(BugBarrier, abc.ABCMeta)

    def __init__(self, dao: BaseDao):
        # Tienen un dao asociado
        self._dao = dao

    @abc.abstractmethod
    def get_main_entity_type(self):
        """
        Función a implementar que devuelve la clase de la entidad principal.
        :return: Clase de la entidad principal.
        """
        pass

    def convert_dict_to_entity(self, request_object_dict: dict) -> BaseEntity:
        """
        Convierte un diccionario en una entidad base, siendo la clave el nombre de cada campo. Por defecto, lo que
        hace es descomponer el diccionario pasado como parámetro y usar los pares clave-valor obtenidos como argumentos
        del contructor de la entidad base. Es posible que haya que implementar esta función en caso de que la entidad
        tenga otras BaseEntity anidadas, en ese caso lo mejor es ir llamando a convert_dict_to_entity de los servicios
        de esas entidades.
        :param request_object_dict: Diccionario con el atributo y valor de los campos de la entidad base.
        :return: Instancia de la entidad base con los atributos indicados en el diccionario.
        """
        # En este caso, de forma genérica, lo que hago es descomponer el diccionario en pares clave-valor con el
        # operador **. Lo que va a hacer es ir al constructor del objeto y sustituir los argumentos de éste por los
        # pares obtenidos.
        return self.get_main_entity_type()(**request_object_dict)

    def start_transaction(self, function, *args, **kwargs):
        """
        Envuelve la función dentro de un contexto transaccional: se hace commit al final si no hay problemas,
        y si sucede algo se hace rollback.
        :param function: Función miembro a ejecutar. Se accede a ella poniendo primero su nombre prececido de punto
        y el nombre del objeto al que pertenece
        :param args: Argumentos de la función.
        :param kwargs: Argumentos de la función que se han pasado por teclado.
        :return: Resultado de la función
        """
        try:
            # Conectar
            self._dao.connect()
            result = function(*args, **kwargs)
            # Consignar operación
            self._dao.commit()
            return result
        except Exception:
            # Rollback si hay error
            self._dao.rollback()
            raise
        finally:
            # Desconectar siempre al final
            self._dao.disconnect()

    def insert(self, entity: BaseEntity):
        """Insertar registros."""
        self._dao.insert(entity)

    def update(self, entity: BaseEntity):
        """Actualizar registros."""
        self._dao.update(entity)

    def delete_entity(self, entity: BaseEntity):
        """Eliminar registros."""
        self._dao.delete_entity(entity)


class ServiceFactory:
    """
    Factoría de servicios, de tal modo que sólo se tendrá en el contexto de la aplicación una instancia de un servicio.
    """

    services = {}
    """Diccionario de servicios ya instanciados."""

    @classmethod
    def get_service(cls, class_to_instanciate: type):
        """
        Devuelve una instancia de un servicio. Si no existe, la instancia y la guarda en el diccionario; si existe,
        devuelve la que tenga ya almacenada.
        :param class_to_instanciate: Clase del servicio a instanciar. Es el tipo, directamente, no el nombre.
        :return: Servicio.
        """
        # Obtengo el nombre de la clase
        class_name = class_to_instanciate.__name__

        # Si no existe, la creo y la almaceno en el diccionario
        if class_name not in cls.services:
            cls.services[class_name] = class_to_instanciate()

        # devuelvo la instancia del diccionario
        return cls.services[class_name]
