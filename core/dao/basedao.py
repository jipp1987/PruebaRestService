import abc
from typing import Generic, TypeVar

import pymysql as pymysql
from dbutils.pooled_db import PooledDB

from core.exception.exceptionhandler import CustomException

from core.util import i18nutils, resourceutils

from core.model.baseentity import BaseEntity

_db_config = {
    'host': resourceutils.get_data_from_resource("host"),
    'user': resourceutils.get_data_from_resource("username"),
    'password': resourceutils.get_data_from_resource("password"),
    'database': resourceutils.get_data_from_resource("dbname"),
    # desactivar autocommit, las transacciones se manejan mejor manualmente
    'autocommit': False,
    'charset': 'utf8',
    'cursorclass': pymysql.cursors.DictCursor
}
"""Configuración de la base de datos."""

# PooledDB: Pool para multihilo.
_POOL = PooledDB(
    creator=pymysql,
    # Número máximo de conexiones permitidas en el pool, 0 y None indican sin límite
    maxconnections=5,
    # Durante la inicialización, al menos la conexión inactiva creada por el pool de conexiones, 0 significa no creado
    mincached=3,
    # El número máximo de conexiones que están inactivas en el pool. 0 y Ninguno indican que no hay límite.
    maxcached=8,
    # El número máximo de conexiones en el pool de conexiones, 0 y Ninguno indican que todas son compartidas (lo cual es
    # inútil)
    maxshared=5,
    # Si no hay una conexión compartida disponible en el pool, ¿espera el bloqueo? True significa esperar, etc.
    # Falso significa no esperar y luego dar un error
    blocking=True,
    # Lista de comandos ejecutados antes de iniciar sesión
    setsession=[],
    # ping Mysql server comprueba si el servicio está disponible
    ping=0,
    # Datos de conexión
    **_db_config)
"""Pool de conexiones."""

T = TypeVar("T", bound=BaseEntity)
"""Clase genérica que herede de BaseEntity, que son las entidades persistidas en la base de datos."""


class BaseDao(Generic[T]):
    """Dao genérico."""

    __metaclass__ = abc.ABCMeta
    """Clase abstracta."""

    # Constructor
    def __init__(self, table: str):
        self.__table = table
        self._conn = None

    # Funciones
    def connect(self):
        """Conectarse a la base de datos."""
        self._conn = _POOL.connection()

    def disconnect(self):
        """Desconectar de la base de datos."""
        # Esto no cierra la conexión, sólo la devuelve al pool de conexiones para que su propio hilo la use de nuevo.
        # La conexión se cierra automáticamente cuando termina el hilo.
        self._conn.close()

    def commit(self):
        """Hace commit."""
        if self._conn is not None:
            self._conn.commit()
        else:
            raise CustomException(i18nutils.translate("i18n_base_commonError_database_connection"))

    def rollback(self):
        """Hace rollback."""
        if self._conn is not None:
            self._conn.rollback()
        else:
            raise CustomException(i18nutils.translate("i18n_base_commonError_database_connection"))

    def execute_query(self, sql):
        """Crea un cursor y ejecuta una query."""
        if self._conn is not None:
            # Crear cursor
            cursor = self._conn.cursor()
            # Ejecutar query
            try:
                cursor.execute(sql)
                return cursor
            except pymysql.Error:
                if cursor is not None:
                    cursor.close()
                raise
        else:
            raise CustomException(i18nutils.translate("i18n_base_commonError_database_connection"))

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
