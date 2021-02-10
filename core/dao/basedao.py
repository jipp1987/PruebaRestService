import abc
import enum
import threading
from collections import namedtuple
from importlib.resources import Package
from typing import Dict, Union, List, Tuple, Type

import pymysql as pymysql
from dbutils.pooled_db import PooledDB, PooledSharedDBConnection, PooledDedicatedDBConnection

from core.dao.mysqldaotools import resolve_field_clause, resolve_filter_clause, resolve_join_clause, \
    resolve_group_by_clause, resolve_order_by_clause, resolve_limit_offset, resolve_translation_of_clauses, \
    get_field_names_as_str_for_insert, get_field_values_as_str_for_insert, get_fields_with_value_as_str_for_update
from core.dao.querytools import FilterClause, OrderByClause, EnumSQLOperationTypes, JoinClause, FieldClause, \
    GroupByClause
from core.exception.exceptionhandler import CustomException

from core.util.i18nutils import translate

from core.model.modeldefinition import BaseEntity
from core.util.listutils import optimized_for_loop

_SQLEngineTypes = namedtuple('SQLEngineTypes', ['value', 'engine_name'])
"""Tupla para propiedades de EnumSQLEngineTypes. La uso para poder añadirle una propiedad al enumerado, aparte del 
propio valor."""


class EnumSQLEngineTypes(enum.Enum):
    """Enumerado de tipos de OrderBy."""

    @property
    def engine_name(self):
        return self.value.engine_name

    MYSQL = _SQLEngineTypes(1, 'mysql')
    POSTGRESQL = _SQLEngineTypes(2, 'postgresql')
    SQL_SERVER = _SQLEngineTypes(3, 'sqlserver')
    ORACLE = _SQLEngineTypes(4, 'oracle')


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
    __db_engine: str = None
    """Motor de la base de datos."""

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
    def __init__(self, table: str, entity_type: type(BaseEntity)):
        self.__table = table
        """Nombre de la tabla principal."""
        self.entity_type = entity_type
        """Tipo de entidad."""

    # Funciones
    @classmethod
    def set_db_config_values(cls, host: str, user: str, password: str, database: str, autocommit: bool = False,
                             charset: str = 'utf8', cursorclass: any = pymysql.cursors.DictCursor,
                             creator: Package = pymysql, maxconnections: int = 5, mincached: int = 3,
                             maxcached: int = 8, maxshared: int = 5, blocking: bool = True, setsession: list = None,
                             ping: int = 0, db_engine: str = EnumSQLEngineTypes.MYSQL.engine_name):
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
        :param ping: El servidor de sql comprueba si el servicio está disponible.
        :param db_engine: Motor de la base de datos.
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

        # Esto va aparte, para evitar problemas con la conexión del cursor.
        cls.__db_engine = db_engine

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
                # Descompongo el diccionario con datos para la conexión con la BD.
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
            raise CustomException(translate("i18n_base_commonError_database_connection"))

    def rollback(self):
        """Hace rollback."""
        # Obtengo el hilo actual
        thread_id = type(self).__get_current_thread()

        if thread_id in type(self).__connected_threads:
            type(self).__connected_threads[thread_id].rollback()
        else:
            raise CustomException(translate("i18n_base_commonError_database_connection"))

    def __execute_query_internal(self, sql, sql_operation_type: EnumSQLOperationTypes = None):
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
            raise CustomException(translate("i18n_base_commonError_database_connection"))

    def insert(self, entity: BaseEntity):
        """
        Inserta un registro en la base de datos.
        :param entity: Objeto que hereda de BaseEntity.
        :return: Nada.
        """
        # Ejecutar query
        sql = f"insert into {self.__table} ({get_field_names_as_str_for_insert(entity)}) " \
              f"values ({get_field_values_as_str_for_insert(entity)}) "
        index = self.__execute_query_internal(sql, sql_operation_type=EnumSQLOperationTypes.INSERT)
        # A través del cursor, le setteo a la entidad el id asignado en la base de datos
        setattr(entity, type(entity).get_id_field_name(), index)

    def update(self, entity: BaseEntity):
        """
        Actualiza un registro en la base de datos.
        :param entity: Objeto que hereda de BaseEntity.
        :return: Nada.
        """
        # Ejecutar query
        sql = f"update {self.__table} set {get_fields_with_value_as_str_for_update(entity)} " \
              f"where id = {getattr(entity, type(entity).get_id_field_name())}"
        self.__execute_query_internal(sql)

    def delete_entity(self, entity: BaseEntity):
        """
        Elimina un registro en la base de datos.
        :param entity: Objeto que hereda de BaseEntity.
        :return: Nada.
        """
        sql = f"delete from {self.__table} where {type(entity).get_id_field_name_in_db()} = " \
              f"{getattr(entity, type(entity).get_id_field_name())}"
        self.__execute_query_internal(sql)

    def __from_query_result_dict_to_entity(self, result_as_dict: List[dict],
                                           join_alias_table_name: Dict[str, Tuple[str, Union[str, None],
                                                                                  Type[BaseEntity]]]) -> \
            List[BaseEntity]:
        """
        Método interno para convertir una lista de diccionarios resultado de una consulta al modelo de entidades
        en Python.
        :param result_as_dict: Resultado de la query como una lista de diccionarios.
        :param join_alias_table_name: Relación de campos durante la fase de traducción respecto a los alias de la
        consulta.
        :return: List[BaseEntity]
        """
        # Resultado
        result: List[BaseEntity] = []

        # Declaración de variables
        field_value: any
        field_name: str
        entity_type: Type[BaseEntity]
        nested_field: str
        key_name: str

        # Estas dos variables las necesito para resolver el caso de entidades anidadas, para añadir dinámicamente
        # diccionarios.
        nested_field_array: list
        last_dict: dict

        # Cada resultado es un diccionario, como una fila del resultado de la consulta.
        for row in result_as_dict:
            # Buscar equivalencia de campos de consulta / definición de campos.
            for k, v in join_alias_table_name.items():
                # Busco la coincidencia y modifico "al vuelo" el diccionario de la fila.
                field_value = row[k]
                field_name = v[0]
                nested_field = v[1]
                entity_type = v[2]
                key_name = entity_type.get_field_name_from_db_field(field_name)

                # Si esta variable es distinta de null, significa que es un campo de una entidad anidada.
                if nested_field is not None:
                    # Divido el nombre del campo anidado por el separador del punto
                    nested_field_array = nested_field.split(".")

                    # Si el primer valor no está en el diccionario original, lo introduzco
                    if nested_field_array[0] not in row:
                        # Importante modificar el nombre de la clave original de la consulta por el primer valor
                        # del array, que es el primer campo anidado partiendo de la entidad original del dao
                        row[nested_field_array[0]] = row.pop(k)
                        row[nested_field_array[0]] = {}

                    # Modifico esta variable, que es la que va guardando la última referencia del diccionario a
                    # actualizar
                    last_dict = row[nested_field_array[0]]

                    # Si tiene más de un elemento, significa que hay elementos anidados dentro del elemento
                    # anidado
                    if len(nested_field_array) > 1:
                        for f in nested_field_array[1:]:
                            # Si no existe el diccionario, lo añado
                            if f not in last_dict:
                                last_dict[f] = {}

                            # Actualizo la referencia al último diccionario
                            last_dict = last_dict[f]

                    # Finalmente introduzco el valor de la clave correspondiente
                    last_dict[key_name] = field_value
                    # Importante eliminar la clave original del diccionario de la fila, al haberla tratado y metido
                    # en un diccionario anidado ya no es necesaria
                    row.pop(k, None)
                else:
                    # Sustituyo el alias de la tabla durante la consulta por el nombre de la clave en el
                    # diccionario
                    row[key_name] = row.pop(k)
                    row[key_name] = field_value

            result.append(self.entity_type.convert_dict_to_entity(row))

        return result

    def select(self, fields: List[FieldClause] = None, filters: List[FilterClause] = None,
               order_by: List[OrderByClause] = None, joins: List[JoinClause] = None,
               group_by: List[GroupByClause] = None,
               offset: int = None, limit: int = None) -> List[BaseEntity]:
        """
        Ejecuta una consulta SELECT sobre la tabla principal del dao. En importante tener en cuenta que aquellos campos
        que no se hayan seleccionado llegarán invariablemente como null en los objetos resultantes, independientemente
        de qué valor tengan en la base de datos; evidentemente, un campo que se haya seleccionado y llegue como null en
        el objeto resultante significa que en la base de datos es null.
        :param fields: Campos seleccionados. Para seleccionar todos los campos de una de las entidades, pasar asterisco.
        No se traerán los campos de entidades anidadas: para ello, habrá que poner otro FieldClause con el
        nombre del campo a traer (partiendo de la entidad base) seguido de asterisco: 'entidad_anidada_1.*',
        'entidad_anidada_1.entidad_anidada_1_1.*...'.
        :param filters: Filtros.
        :param order_by: Cláusulas ORDER BY.
        :param joins: Cláusulas JOIN.
        :param group_by: Cláusulas GROUP BY.
        :param offset: Offset del límite de la consulta.
        :param limit: Límite de registros.
        :return: Lista de entidades encontradas.
        """
        # declaro una serie de campos para pasar a la función interna, asumiendo primero que son null.
        filters_translated = None
        order_by_translated = None
        joins_translated = None
        group_by_translated = None
        # limit y offset no hace falta traducirlos, los paso tal cual

        # Diccionario empleado para mantener una relación entre los distintos alias de las tablas que ha especificado
        # el usuario al construir los objetos de modelado de la query, y el nombre que corresponde realmente al campo
        # dentro del propio objeto en Python.
        join_alias_table_name: Dict[str, Tuple[str, Union[str, None], Type[BaseEntity]]] = {}

        # La idea es que estas listas de cláusulas vienen con los campos de las entidades modeladas en python, se trata
        # de traducirlas al modelo de la base de datos.

        # Campos. Debe hacer algo para seleccionar, si no es el caso se seleccionan todos los campos de
        # la entidad principal.
        if not fields or len(fields) <= 0:
            fields = [FieldClause(field_name='*')]

        fields_translated = resolve_translation_of_clauses(FieldClause, fields, self.entity_type, self.__table,
                                                           join_alias_table_name)

        # Filtros
        if filters and len(filters) > 0:
            filters_translated = resolve_translation_of_clauses(FilterClause, filters, self.entity_type, self.__table,
                                                                join_alias_table_name)

        # Order by
        if order_by and len(order_by) > 0:
            order_by_translated = resolve_translation_of_clauses(OrderByClause, order_by, self.entity_type,
                                                                 self.__table, join_alias_table_name)

        # Group by
        if group_by and len(group_by) > 0:
            group_by_translated = resolve_translation_of_clauses(GroupByClause, group_by, self.entity_type,
                                                                 self.__table, join_alias_table_name)

        # Joins
        if joins and len(joins) > 0:
            joins_translated = resolve_translation_of_clauses(JoinClause, joins, self.entity_type,
                                                              self.__table, join_alias_table_name)

        # RESULTADO: Devuelve una lista de diccionarios
        result_as_dict = self.__select_internal(fields=fields_translated, filters=filters_translated,
                                                order_by=order_by_translated, joins=joins_translated,
                                                group_by=group_by_translated, offset=offset,
                                                limit=limit)

        result: List[BaseEntity]
        if result_as_dict is not None and len(result_as_dict) > 0:
            # Recorrer lista de diccionarios e ir transformando cada valor en una entidad base
            result = self.__from_query_result_dict_to_entity(result_as_dict=result_as_dict,
                                                             join_alias_table_name=join_alias_table_name)
        else:
            result = []

        return result

    def __select_internal(self, fields: List[FieldClause] = None, filters: List[FilterClause] = None,
                          order_by: List[OrderByClause] = None, joins: List[JoinClause] = None,
                          group_by: List[GroupByClause] = None,
                          offset: int = None, limit: int = None) -> List[dict]:
        """
        Ejecuta una consulta SELECT sobre la tabla principal del dao. Función interna con los campos ya traducidos al
        modelo de datos.
        :param fields: Campos seleccionados.
        :param filters: Filtros.
        :param order_by: Cláusulas ORDER BY.
        :param joins: Cláusulas JOIN.
        :param group_by: Cláusulas GROUP BY.
        :param offset: Offset del límite de la consulta.
        :param limit: Límite de registros.
        :return: Diccionario.
        """
        # Resuelto SELECT (por defecto, asterisco para todos los campos)
        select = ''
        if fields:
            # Creo un array de strings y luego lo concateno con join. Es la forma más eficiente para generar el filtro
            # desde las listas.
            fields_arr = []
            # Uso una función para bucle for optimizado.
            optimized_for_loop(fields, resolve_field_clause, fields_arr)
            # Unir los fields
            select = ''.join(fields_arr)

        # Resuelvo filtros
        filtro = ''
        if filters:
            # Creo un array de strings y luego lo concateno con join. Es la forma más eficiente para generar el filtro
            # desde las listas.
            filtro_arr = []
            # Uso una función para bucle for optimizado.
            optimized_for_loop(filters, resolve_filter_clause, filtro_arr)
            # Unir los filtros
            filtro = ''.join(filtro_arr)

        # Resuelvo joins
        join = ''
        if joins:
            # Creo un array de strings y luego lo concateno con join. Es la forma más eficiente para generar el filtro
            # desde las listas.
            join_arr = []
            # Uso una función para bucle for optimizado.
            optimized_for_loop(joins, resolve_join_clause, join_arr)
            # Unir los joins
            join = ''.join(join_arr)

        # Resuelvo group
        group = ''
        if group_by:
            # Creo un array de strings y luego lo concateno con join. Es la forma más eficiente para generar el filtro
            # desde las listas.
            group_by_arr = []
            # Uso una función para bucle for optimizado.
            optimized_for_loop(group_by, resolve_group_by_clause, group_by_arr)
            # Unir los groups
            group = ''.join(group_by_arr)

        # Resuelvo order bys
        orden = ''
        if order_by:
            # Creo un array de strings y luego lo concateno con join. Es la forma más eficiente para generar el filtro
            # desde las listas.
            order_by_arr = []
            # Uso una función para bucle for optimizado.
            optimized_for_loop(order_by, resolve_order_by_clause, order_by_arr)
            # Unir los ordenby
            orden = ''.join(order_by_arr)

        # Resuelvo offset y limit
        limit_offset = ''
        if limit is not None:
            limit_offset = resolve_limit_offset(limit=limit, offset=offset)

        # Ejecutar query
        sql = f"SELECT {select.strip()} FROM {self.__table} {join.strip()} {filtro.strip()} " \
              f"{group.strip()} {orden.strip()} {limit_offset.strip()}"

        # El resultado es una lista de  diccionarios, pero hay que transformarlo en modelo de datos
        result_as_dict: List[dict] = self.__execute_query_internal(sql=sql,
                                                                   sql_operation_type=EnumSQLOperationTypes.SELECT_MANY)

        return result_as_dict
