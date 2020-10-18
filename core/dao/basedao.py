from typing import Generic, TypeVar

import pymysql as pymysql

from core.decometa.decometa import DecoMetaExceptions
from core.exception.exceptionhandler import CustomException

from core.util import i18n, resourceutils

from core.model.BaseEntity import BaseEntity

T = TypeVar("T", bound=BaseEntity)
"""Clase genérica que herede de BaseEntity, que son las entidades persistidas en la base de datos."""


class BaseDao(Generic[T], metaclass=DecoMetaExceptions):
    """Dao genérico."""

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
        self._db = pymysql.connect(self.__host, self.__username, self.__password, self.__dbname)
        # desactivar autocommit, las transacciones se manejan mejor manualmente
        self._db.autocommit = False

    def disconnect(self):
        """Desconectar de la base de datos."""
        if self._db is not None and self._db.open:
            self._db.close()
            self._db = None
        else:
            raise CustomException(i18n.translate("i18n_base_commonError_database_connection"))

    def commit(self):
        """Hace commit."""
        if self._db is not None and self._db.open:
            self._db.commit()
        else:
            raise CustomException(i18n.translate("i18n_base_commonError_database_connection"))

    def rollback(self):
        """Hace rollback."""
        if self._db is not None and self._db.open:
            self._db.rollback()
        else:
            raise CustomException(i18n.translate("i18n_base_commonError_database_connection"))

    def execute_query(self, sql):
        """Crea un cursor y ejecuta una query."""
        cursor = None
        if self._db is not None and self._db.open:
            # Crear cursor
            cursor = self._db.cursor()
            # Ejecutar query
            cursor.execute(sql)
            # Cerrar cursor
            cursor.close()
        else:
            raise CustomException(i18n.translate("i18n_base_commonError_database_connection"))

    def insert(self, entity: T):
        """Insertar registros."""
        try:
            sql = f"insert into {self.__table} ({entity.get_field_names_as_str()}) " \
                  f"values ({entity.get_field_values_as_str()}) "

            # Conectar
            self.connect()
            # Ejecutar query
            self.execute_query(sql)
            # Consignar operación
            self.commit()
        except pymysql.Error:
            # Rollback si hay error
            self.rollback()
            # La metaclase ya se ocupa de tratar la excepción, el mensaje, tipo, archivo, etc.
            raise
        finally:
            # Desconectar siempre al final
            self.disconnect()
