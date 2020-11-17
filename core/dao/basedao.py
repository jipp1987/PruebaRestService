import abc
from typing import Generic, TypeVar

import pymysql as pymysql
from dbutils.persistent_db import PersistentDB

from core.exception.exceptionhandler import CustomException

from core.util import i18nutils, resourceutils

from core.model.baseentity import BaseEntity

# PersistentDB: crea una conexión para cada hilo. Incluso si el hilo llama al método close, no se cerrará. Simplemente
# vuelve a colocar la conexión en el grupo de conexiones para que su propio hilo la use nuevamente. Cuando termina
# el hilo, la conexión se cierra automáticamente.
POOL = PersistentDB(
    creator=pymysql,
    # Número máximo de veces que un link es reutilizado, None indica ilimitado
    maxusage=None,
    # Lista de comandos ejecutados antes de comenzar una sesión. Ejemplos:["set datestyle to ...", "set time zone ..."]
    setsession=[],
    # ping MySQL Server, comprueba si el servicio está disponible.# Ejemplo: 0 = none = never (nunca detectar),
    # 1 = Default = Siempre que se solicite, 2 = Cuando un cursor es creado, 4 = Cuando se ejecuta una consulta,
    # 7 = Siempre
    ping=0,
    # Si False, conn.close() De hecho, se ignora para el próximo uso, y el enlace se cerrará automáticamente cuando
    # el hilo se cierre de nuevo.
    # Si true, conn.close() Luego cierre el enlace y vuelva a llamar
    # pool.connection se informará un error porque la conexión se ha cerrado (pool.steady_connection ()
    # Puede obtener un nuevo enlace)
    closeable=False,
    # Este hilo tiene un objeto de valor exclusivo, que se utiliza para guardar el objeto vinculado.
    threadlocal=None,
    # Datos de conexión
    host=resourceutils.get_data_from_resource("host"),
    user=resourceutils.get_data_from_resource("username"),
    password=resourceutils.get_data_from_resource("password"),
    database=resourceutils.get_data_from_resource("dbname"),
    # desactivar autocommit, las transacciones se manejan mejor manualmente
    autocommit=False,
    charset='utf8',
    cursorclass=pymysql.cursors.DictCursor)
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
        self._conn = POOL.connection(shareable=False)

    def disconnect(self):
        """Desconectar de la base de datos."""
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
