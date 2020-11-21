import abc
from importlib.resources import Package

import pymysql as pymysql
from dbutils.pooled_db import PooledDB

from core.exception.exceptionhandler import CustomException

from core.util import i18nutils

from core.model.baseentity import BaseEntity


class BaseDao(object, metaclass=abc.ABCMeta):
    """Dao genérico."""

    __db_config: dict = None
    """Diccionario con los datos de conexión con la base de datos. Nulo por defecto."""

    __POOL: PooledDB = None
    """Pool de conexiones para aplicación multihilo, nulo por defecto."""

    # Constructor
    def __init__(self, table: str):
        self.__table = table
        self._conn = None

    # Funciones
    @classmethod
    def set_db_config_values(cls, host: str, user: str, password: str, database: str, autocommit: bool = False,
                             charset: str = 'utf8', cursorclass: any = pymysql.cursors.DictCursor,
                             creator: Package = pymysql, maxconnections: int = 5, mincached: int = 3,
                             maxcached: int = 8, maxshared: int = 5, blocking: bool = True, setsession: list = None,
                             ping: int = 0):
        """
        Establece los parámetros  de conexión de la base de datos, inicializando el diccionario de parámetros de la
        clase. Luego establecerá el pool de conexiones.
        :param host: Host de la base de datos.
        :param user: Usuario autorizado de la base de datos.
        :param password: Password del usuario.
        :param database: Nombre de la base de datos.
        :param autocommit: Hacer commits automáticamente. False por defecto.
        :param charset: Set de caracteres de la base de datos, utf8 por defecto.
        :param cursorclass: Clase del cursor, pymysql.cursors.DictCursor por defecto.
        :param creator: Paquete de Python que se usará como base para la creación del pool de conexiones.
        :param maxconnections: Número máximo de conexiones permitidas en el pool, 0 y None indican sin límite.
        :param mincached: Durante la inicialización, al menos la conexión inactiva creada por el pool de conexiones, 0
        significa no creado.
        :param maxcached: El número máximo de conexiones que están inactivas en el pool. 0 y Ninguno indican que no hay
        límite.
        :param maxshared: El número máximo de conexiones en el pool de conexiones, 0 y Ninguno indican que todas son
        compartidas (lo cual es inútil).
        :param blocking: Si no hay una conexión compartida disponible en el pool, ¿espera el bloqueo? True significa
        esperar, etc. Falso significa no esperar y luego dar un error.
        :param setsession: Lista de comandos ejecutados antes de iniciar sesión.
        :param ping: Mysql server comprueba si el servicio está disponible.
        :return: Nada.
        """
        cls.__db_config = {
            'host': host,
            'user': user,
            'password': password,
            'database': database,
            'autocommit': autocommit,
            'charset': charset,
            'cursorclass': cursorclass
        }
        # Establecer pool de conexiones.
        cls.__set_pool_values(creator=creator, maxconnections=maxconnections, mincached=mincached, maxcached=maxcached,
                              maxshared=maxshared, blocking=blocking, setsession=setsession, ping=ping)

    @classmethod
    def __set_pool_values(cls, creator: Package, maxconnections: int, mincached: int, maxcached: int, maxshared: int,
                          blocking: bool, setsession: list, ping: int):
        """
        Establece los valores para el pool de conexiones. OJO!!! Es impresincible que antes estén establecidos los
        valores de db_config a través de set_db_config_values. Sino no se establecerá el pool de conexiones.
        :param creator: Paquete de Python que se usará como base para la creación del pool de conexiones.
        :param maxconnections: Número máximo de conexiones permitidas en el pool, 0 y None indican sin límite.
        :param mincached: Durante la inicialización, al menos la conexión inactiva creada por el pool de conexiones, 0
        significa no creado.
        :param maxcached: El número máximo de conexiones que están inactivas en el pool. 0 y Ninguno indican que no hay
        límite.
        :param maxshared: El número máximo de conexiones en el pool de conexiones, 0 y Ninguno indican que todas son
        compartidas (lo cual es inútil).
        :param blocking: Si no hay una conexión compartida disponible en el pool, ¿espera el bloqueo? True significa
        esperar, etc. Falso significa no esperar y luego dar un error.
        :param setsession: Lista de comandos ejecutados antes de iniciar sesión.
        :param ping: Mysql server comprueba si el servicio está disponible.
        :return: Nada.
        """
        if cls.__db_config:
            cls.__POOL = PooledDB(
                creator=creator,
                maxconnections=maxconnections,
                mincached=mincached,
                maxcached=maxcached,
                maxshared=maxshared,
                blocking=blocking,
                setsession=setsession,
                ping=ping,
                # Deserializo el diccionario con datos para la conexión con la base de datos.
                **cls.__db_config)

    def connect(self):
        """Conectarse a la base de datos."""
        self._conn = self.__POOL.connection()

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

    def insert(self, entity: BaseEntity):
        """Insertar registros."""
        # Ejecutar query
        sql = f"insert into {self.__table} ({entity.get_field_names_as_str()}) " \
              f"values ({entity.get_field_values_as_str()}) "
        cursor = self.execute_query(sql)
        # A través del cursor, le setteo a la entidad el id asignado en la base de datos
        setattr(entity, entity.id_field_name, cursor.lastrowid)
        # cerrar cursor
        cursor.close()

    def update(self, entity: BaseEntity):
        """Actualizar registros."""
        # Ejecutar query
        sql = f"update {self.__table} set {entity.get_fields_with_value_as_str()} " \
              f"where id = {getattr(entity, entity.id_field_name)}"
        cursor = self.execute_query(sql)
        # cerrar cursor
        cursor.close()

    def delete_entity(self, entity: BaseEntity):
        """
        Elimina una entidad de la base de datos.
        :param entity: Entidad a eliminar.
        """
        sql = f"delete from {self.__table} where id = {getattr(entity, entity.id_field_name)}"
        cursor = self.execute_query(sql)
        # cerrar cursor
        cursor.close()
