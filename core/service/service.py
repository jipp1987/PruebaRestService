from typing import TypeVar, Generic

from core.dao.basedao import BaseDao
from core.exception.exceptionhandler import BugBarrier
from core.model.BaseEntity import BaseEntity

T = TypeVar("T", bound=BaseEntity)
"""Clase genérica que herede de BaseEntity, que son las entidades persistidas en la base de datos."""
DAO = TypeVar("DAO", bound=BaseDao[T])
"""Implementación de BaseDao que utilice la entidad base"""


class BaseService(Generic[T], metaclass=BugBarrier):
    """
    Clase genérica de la que han de heredar el resto de servicios del programa.
    """

    def __init__(self, dao: DAO):
        # Tienen un dao asociado
        self._dao = dao

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

    def insert(self, entity: T):
        """Insertar registros."""
        self._dao.insert(entity)

    def delete_entity(self, entity: T):
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
