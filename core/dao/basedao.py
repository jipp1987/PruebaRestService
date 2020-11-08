import abc
from typing import Generic, TypeVar

import pymysql as pymysql

from core.exception.exceptionhandler import ServiceException

from core.util import i18n, resourceutils

from core.model.baseentity import BaseEntity

T = TypeVar("T", bound=BaseEntity)
"""Clase genérica que herede de BaseEntity, que son las entidades persistidas en la base de datos."""


class BaseDao(Generic[T]):
    """Dao genérico."""

    __metaclass__ = abc.ABCMeta
    """Clase abstracta."""

    # Constructor
    def __init__(self, table: str):
        self.__table = table
        # Los datos los cargo de un fichero situado en resources/db.properties (ignorado en git)
        self.__host = resourceutils.get_data_from_resource("host")
        self.__username = resourceutils.get_data_from_resource("username")
        self.__password = resourceutils.get_data_from_resource("password")
        self.__dbname = resourceutils.get_data_from_resource("dbname")
        self._db = None

    # Funciones
    def connect(self):
        """Conectarse a la base de datos."""
        if self._db is None or self._db.open is False:
            self._db = pymysql.connect(self.__host, self.__username, self.__password, self.__dbname)
            # desactivar autocommit, las transacciones se manejan mejor manualmente
            self._db.autocommit = False

    def disconnect(self):
        """Desconectar de la base de datos."""
        if self._db is not None and self._db.open:
            self._db.close()
            self._db = None

    def commit(self):
        """Hace commit."""
        if self._db is not None and self._db.open:
            self._db.commit()
        else:
            raise ServiceException(i18n.translate("i18n_base_commonError_database_connection"))

    def rollback(self):
        """Hace rollback."""
        if self._db is not None and self._db.open:
            self._db.rollback()
        else:
            raise ServiceException(i18n.translate("i18n_base_commonError_database_connection"))

    def execute_query(self, sql):
        """Crea un cursor y ejecuta una query."""
        if self._db is not None and self._db.open:
            # Crear cursor
            cursor = self._db.cursor()
            # Ejecutar query
            try:
                cursor.execute(sql)
                return cursor
            except pymysql.Error:
                if cursor is not None:
                    cursor.close()
                raise
        else:
            raise ServiceException(i18n.translate("i18n_base_commonError_database_connection"))

    def insert(self, entity: T):
        """Insertar registros."""
        # Ejecutar query
        sql = f"insert into {self.__table} ({entity.get_field_names_as_str()}) " \
              f"values ({entity.get_field_values_as_str()}) "
        cursor = self.execute_query(sql)
        # A través del cursor, le setteo a la entidad el id asignado en la base de datos
        setattr(entity, entity.idfieldname, cursor.lastrowid)
        # cerrar cursor
        cursor.close()

    def update(self, entity: T):
        """Actualizar registros."""
        # Ejecutar query
        sql = f"update {self.__table} set {entity.get_fields_with_value_as_str()} " \
              f"where id = {getattr(entity, entity.idfieldname)}"
        cursor = self.execute_query(sql)
        # cerrar cursor
        cursor.close()

    def delete_entity(self, entity: T):
        """
        Elimina una entidad de la base de datos.
        :param entity: Entidad a eliminar.
        """
        sql = f"delete from {self.__table} where id = {getattr(entity, entity.idfieldname)}"
        cursor = self.execute_query(sql)
        # cerrar cursor
        cursor.close()
