from typing import TypeVar, Generic

from core.dao.basedao import BaseDao
from core.exception.decometaexceptions import DecoMetaExceptions
from core.model.BaseEntity import BaseEntity

T = TypeVar("T", bound=BaseEntity)
"""Clase genérica que herede de BaseEntity, que son las entidades persistidas en la base de datos."""
DAO = TypeVar("DAO", bound=BaseDao[T])
"""Implementación de BaseDao que utilice la entidad base"""


class BaseService(Generic[T], metaclass=DecoMetaExceptions):
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
