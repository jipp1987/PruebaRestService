import abc
import threading
from importlib.resources import Package
from typing import Dict, Union, List

import pymysql as pymysql
from dbutils.pooled_db import PooledDB, PooledSharedDBConnection, PooledDedicatedDBConnection

from core.dao.querytools import FilterClause, OrderByClause, EnumSQLOperationTypes
from core.exception.exceptionhandler import CustomException

from core.util import i18nutils

from core.model.modeldefinition import BaseEntity


class _BaseConnection(object):
    """Clase interna para conexión con la base de datos. La idea es que por cada transacción en un hilo se crée un
    objeto de éstos, y al final de la transacción, ya haya sido consignada o haya hecho rollback, se cierre el cursor
    y se elimine del ámbito del programa."""

    # CONSTRUCTOR
    def __init__(self, connection: Union[PooledSharedDBConnection, PooledDedicatedDBConnection],
                 thread_id: int):
        self.connection = connection
        """Objeto de conexión."""
        self.thread_id = thread_id
        """Identificador del hilo."""
        # Abro un cursor para reusar durante toda la transacción.
        self.cursor = None
        """Cursor SQL."""
        self.open_cursor()

    # FUNCIONES
    def open_cursor(self):
        """Abre un cursor."""
        if self.connection:
            self.cursor = self.connection.cursor()

    def commit(self):
        """Consigna la transacción."""
        self.connection.commit()

    def close(self):
        """Cierra cursor y conexión."""
        # Al cerrar la conexión, que primero cierre el cursor.
        self.cursor.close()
        # Cierra la conexión con la base de datos.
        self.connection.close()

    def rollback(self):
        """Deshace todos los cambios durante la transacción."""
        self.connection.rollback()


class BaseDao(object, metaclass=abc.ABCMeta):
    """Dao genérico."""

    __db_config: dict = None
    """Diccionario con los datos de conexión con la base de datos. Nulo por defecto."""

    __POOL: PooledDB = None
    """Pool de conexiones para aplicación multihilo, nulo por defecto."""

    # Esto es un atributo de clase, todas las instancias de BaseDao lo compartirán, como si fuese una variable
    # estática.
    __connected_threads: Dict[int, _BaseConnection] = {}
    """Diccionario de hilos que ya están conectados. Es un atributo de clase porque todas las instancias de 
    BaseService deben compartirlo, dado que los servicios asociados a los daos se llaman unos a otros. El identificador 
    es un entero con el ident del hilo actual, y el valor es un objeto de tipo BaseConnection."""

    # Constructor
    def __init__(self, table: str):
        self.__table = table

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

    @staticmethod
    def __get_current_thread() -> int:
        """
        Devuelve un identificador del hilo actual de ejecución.
        :return: int
        """
        return threading.get_ident()

    def connect(self) -> bool:
        """
        Obtiene una conexión del pool para el hilo actual.
        :return: True si ha tenido que conectarse, o False si no ha hecho falta porque el hilo ya tiene una conexión.
        """
        # Obtener id del hilo para saber si ya está conectado
        thread_id = type(self).__get_current_thread()
        # Creo un boolean para saber si me he tenido que conectar, con el fin de consignar la operación
        i_had_to_connect = False

        # Conectar (si el hilo no está ya conectado). Dado que _connected_threads es un atributo de clase, todas las
        # instancias de BaseService lo van a compartir, con lo cual si un servicio utiliza otros dentro de una
        # función el hilo seguirá registrado como conectado.
        if thread_id not in type(self).__connected_threads:
            # Guardo en el diccionario de hilos conectados una nueva conexión
            # No hace falta especificarle a __POOL.connection() el hilo, ya lo hace automáticamente.
            type(self).__connected_threads[thread_id] = _BaseConnection(connection=type(self).__POOL.connection(),
                                                                        thread_id=thread_id)
            # Activo el Boolean para saber que me tuve que conectar
            i_had_to_connect = True

        return i_had_to_connect

    def disconnect(self):
        """Desconectar de la base de datos."""
        # Obtengo el hilo actual
        thread_id = type(self).__get_current_thread()

        # Esto no cierra la conexión, sólo la devuelve al pool de conexiones para que su propio hilo la use de nuevo.
        # La conexión se cierra automáticamente cuando termina el hilo.
        if thread_id in type(self).__connected_threads:
            # Cierro el hilo, aunque técnicamente el poll no lo cerrará hasta que el hilo termine
            type(self).__connected_threads[thread_id].close()
            # Quitar hilo del diccionario
            type(self).__connected_threads.pop(thread_id, None)

    def commit(self):
        """Hace commit."""
        # Obtengo el hilo actual
        thread_id = type(self).__get_current_thread()

        if thread_id in type(self).__connected_threads:
            type(self).__connected_threads[thread_id].commit()
        else:
            raise CustomException(i18nutils.translate("i18n_base_commonError_database_connection"))

    def rollback(self):
        """Hace rollback."""
        # Obtengo el hilo actual
        thread_id = type(self).__get_current_thread()

        if thread_id in type(self).__connected_threads:
            type(self).__connected_threads[thread_id].rollback()
        else:
            raise CustomException(i18nutils.translate("i18n_base_commonError_database_connection"))

    def execute_query(self, sql, sql_operation_type: EnumSQLOperationTypes = None):
        """Crea un cursor y ejecuta una query."""
        # Obtengo el hilo actual
        thread_id = type(self).__get_current_thread()

        if thread_id in type(self).__connected_threads:
            # Obtener cursor
            cursor = type(self).__connected_threads[thread_id].cursor

            # Ejecutar query
            try:
                cursor.execute(sql)

                # Dependiendo del tipo de operación, podría ser necesario devolver algún valor
                if sql_operation_type:
                    if sql_operation_type == EnumSQLOperationTypes.INSERT:
                        return cursor.lastrowid
                    elif sql_operation_type == EnumSQLOperationTypes.SELECT_ONE:
                        return cursor.fetchone()
                    elif sql_operation_type == EnumSQLOperationTypes.SELECT_MANY:
                        return cursor.fetchall()
                    else:
                        return None
            except pymysql.Error:
                raise
        else:
            raise CustomException(i18nutils.translate("i18n_base_commonError_database_connection"))

    def insert(self, entity: BaseEntity):
        """
        Inserta un registro en la base de datos.
        :param entity: Objeto que hereda de BaseEntity.
        :return: Nada.
        """
        # Ejecutar query
        sql = f"insert into {self.__table} ({entity.get_field_names_as_str()}) " \
              f"values ({entity.get_field_values_as_str()}) "
        index = self.execute_query(sql, sql_operation_type=EnumSQLOperationTypes.INSERT)
        # A través del cursor, le setteo a la entidad el id asignado en la base de datos
        setattr(entity, entity.get_id_field_name(), index)

    def update(self, entity: BaseEntity):
        """
        Actualiza un registro en la base de datos.
        :param entity: Objeto que hereda de BaseEntity.
        :return: Nada.
        """
        # Ejecutar query
        sql = f"update {self.__table} set {entity.get_fields_with_value_as_str()} " \
              f"where id = {getattr(entity, entity.get_id_field_name())}"
        self.execute_query(sql)

    def delete_entity(self, entity: BaseEntity):
        """
        Elimina un registro en la base de datos.
        :param entity: Objeto que hereda de BaseEntity.
        :return: Nada.
        """
        sql = f"delete from {self.__table} where id = {getattr(entity, entity.get_id_field_name())}"
        self.execute_query(sql)

    def find_by_filtered_query(self, filters: List[FilterClause], order: List[OrderByClause]) -> List[BaseEntity]:
        if filters:
            # Creo un array de strings y luego lo concateno con join. Es la forma más eficiente para generar el filtro
            # desde las listas.
            filtro_arr = []

            # Para recorrer los listados, voy a usar un iterador, que es más eficiente.
            iterator = iter(filters)
            done_looping = False
            while not done_looping:
                try:
                    item = next(iterator)
                except StopIteration:
                    done_looping = True
                else:
                    # Añadir tantos paréntesis de inicio como diga el objeto
                    start_parenthesis = ''
                    if item.start_parenthesis:
                        for p in range(item.start_parenthesis):
                            start_parenthesis += '('

                    # Añadir tantos paréntesis de fin como diga el objeto
                    end_parenthesis = ''
                    if item.end_parenthesis:
                        for p in range(item.end_parenthesis):
                            end_parenthesis += ')'

                    # Objeto a comparar
                    if isinstance(item.object_to_compare, str):
                        compare = f"'{item.object_to_compare}'"
                    else:
                        compare = f"{str(item.object_to_compare)}"

                    # Crear filtro
                    filtro_arr.append(f"{start_parenthesis}{item.field_name} {item.filter_type.filter_operator} "
                                      f"{compare}{end_parenthesis}")

            # Unir los filtros
            filtro = ''.join(filtro_arr)

            # Ejecutar query
            sql = f"SELECT FROM {self.__table} WHERE {filtro}"
            return self.execute_query(sql, sql_operation_type=EnumSQLOperationTypes.SELECT_MANY)
