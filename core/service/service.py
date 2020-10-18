from typing import TypeVar, Generic

from core.dao.basedao import BaseDao
from core.model.BaseEntity import BaseEntity

T = TypeVar("T", bound=BaseEntity)
"""Clase genérica que herede de BaseEntity, que son las entidades persistidas en la base de datos."""
DAO = TypeVar("DAO", bound=BaseDao[T])
"""Implementación de BaseDao que utilice la entidad base"""


class BaseService(Generic[T]):
    """
    Clase genérica de la que han de heredar el resto de servicios del programa.
    """

    def __init__(self, dao: DAO):
        # Tienen un dao asociado
        self._dao = dao

    def insert(self, entity: T):
        """Insertar registros."""
        self._dao.insert(entity)
