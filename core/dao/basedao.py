import abc
import copy
import threading
from importlib.resources import Package
from typing import Dict, Union, List

import pymysql as pymysql
from dbutils.pooled_db import PooledDB, PooledSharedDBConnection, PooledDedicatedDBConnection

from core.dao.querytools import FilterClause, OrderByClause, EnumSQLOperationTypes, resolve_filter_clause, \
    resolve_order_by_clause, JoinClause, resolve_join_clause, GroupByClause, resolve_group_by_clause, FieldClause, \
    resolve_field_clause, resolve_limit_offset
from core.exception.exceptionhandler import CustomException

from core.util.i18nutils import translate

from core.model.modeldefinition import BaseEntity, FieldDefinition
from core.util.listutils import optimized_for_loop


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
        sql = f"insert into {self.__table} ({entity.get_field_names_as_str()}) " \
              f"values ({entity.get_field_values_as_str()}) "
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
        sql = f"update {self.__table} set {entity.get_fields_with_value_as_str()} " \
              f"where id = {getattr(entity, type(entity).get_id_field_name())}"
        self.__execute_query_internal(sql)

    def delete_entity(self, entity: BaseEntity):
        """
        Elimina un registro en la base de datos.
        :param entity: Objeto que hereda de BaseEntity.
        :return: Nada.
        """
        sql = f"delete from {self.__table} where id = {getattr(entity, type(entity).get_id_field_name())}"
        self.__execute_query_internal(sql)

    def __resolve_translation_of_clauses(self, clause_type: type, clauses_list: list, is_join_clause: bool = False):
        """
        Resuelve la traducción de select, filtros, order_by y group_by.
        :param clause_type: Tipo de cláusula.
        :param clauses_list: Lista de cláusulas a traducir.
        :param is_join_clause: Si es un join, utiliza otro campo por el que hacer el split. False por defecto.
        :return: Lista de filtros, order, group o fields traducidos a mysql.
        """
        # Declaración de campos a asignar en bucle
        clauses_translated = []
        new_clause: clause_type
        field_definition: Union[FieldDefinition, None]
        new_table_alias: Union[str, None]
        field_name_array: List[str]
        field_name_array_last_index: int
        # Esto lo uso para los joins, para poder mantenerlos relacionados. La clave es el nombre del campo y el valor
        # es el nombre real de la tabla en la base de datos.
        join_parent_table_dict: Dict[str, str]

        for f in clauses_list:
            # Copio el objeto entrante
            new_clause = copy.deepcopy(f)
            field_definition = None
            new_table_alias = None

            # Si el campo viene con este formato: campo_tabla_1.campo_tabla_2.campo_tabla_3... significa que es
            # un campo de una clase anidada en el modelo.
            # Separo el nombre del campo por el punto
            field_name_array = new_clause.table_name.split(".") if is_join_clause else new_clause.field_name.split(".")

            # De lo que se trata ahora es de ir explorando los campos para resolver la clase exacta del objeto,
            # así como los atributos del mapeo relacional.
            field_name_array_last_index = len(field_name_array) - 1
            if field_name_array_last_index > 0:
                join_parent_table_dict = {}

                for idx, val in enumerate(field_name_array):
                    # Todos los índices menos el último serán campos relacionales hacia otras entidades.
                    if idx == 0:
                        # El primero será el de la propia clase del DAO actual
                        field_definition = self.entity_type.get_model_dict().get(val)
                    elif idx < field_name_array_last_index:
                        # A partir de ahí,
                        field_definition = field_definition.field_type.get_model_dict().get(val)  # noqa
                    else:
                        # En último índice, antes de volver a reasignar la definición de campo, me quedo con
                        # algunos datos de la penúltima (que este de hecho la clase a la que pertenece el campo
                        # como tal).
                        if is_join_clause:
                            # Lo que pretendo con esto es mantener una relación entre las tablas para que la cláusula
                            # join de la consulta sea correcta. Hay tres posibilidades:
                            # 1. Se ha especificado un alias para la tabla: en ese caso, se usa el alias sin más.
                            # 2. Es un join desde la tabla principal del dao a una tabla anidada: en ese caso, la tabla
                            # padre es la del propio dao.
                            # 3. Es un join a una tabla anidada dentro de otra tabla anidada. En ese caso, lo que hago
                            # es usar el diccionario de definiciones de campo y acceder al que está una posición
                            # atrás, dado que el campo referenced_table_name hará referencia al nombre en la base de
                            # datos de la tabla padre del campo final: cliente.tipo_cliente.usuario -> En este caso voy
                            # a hacer join a usuario, su tabla padre es tipo_cliente, la definición de campo que
                            # contiene el nombre de la tabla de tipos de cliente está en clientes.
                            # FIXME Esto no está probado y seguramente no esté bien, fijarse cómo está hecho más abajo.
                            new_clause.parent_table = new_clause.parent_table if new_clause.parent_table is not None \
                                else (self.__table if idx == 1 else join_parent_table_dict[field_name_array[-1]])

                        new_table_alias = new_clause.table_alias if new_clause.table_alias is not None else \
                            field_definition.referenced_table_name
                        field_definition = field_definition.field_type.get_model_dict().get(val)  # noqa

                    # Añadir al mapa de los joins una clave-valor: clave es el nombre del campo, valor es la tabla
                    # relacionada.
                    join_parent_table_dict[val] = field_definition.referenced_table_name
            else:
                # En caso de que sea un campo normal, el alias será el que venga en la entidad o bien el nombre de
                # la tabla del DAO.
                field_definition = self.entity_type.get_model_dict().get(f.table_name if is_join_clause
                                                                         else f.field_name)

                # Si es una join clause:
                if is_join_clause:
                    # La tabla padre será la del propio dao
                    new_clause.parent_table = new_clause.parent_table if new_clause.parent_table is not None \
                        else self.__table
                    # La tabla será la tabla referenciada
                    new_clause.table_name = field_definition.referenced_table_name
                    # El alias será también el nombre de la tabla
                    new_table_alias = new_clause.table_alias if new_clause.table_alias is not None else \
                        new_clause.table_name
                else:
                    new_table_alias = new_clause.table_alias if new_clause.table_alias is not None else self.__table

            # Lanzar error si no existe uno de estos objetos
            if field_definition is None or new_table_alias is None:
                raise CustomException(translate("i18n_base_commonError_query_translate", None, str(new_clause)))

            # Parte especial para cláusulas join
            if is_join_clause:
                # Nombre del campo id de la clase
                if new_clause.id_column_name is None:
                    new_clause.id_column_name = field_definition.field_type.get_id_field_name() # noqa

                # Nombre del campo referenciado en la base de datos.
                if new_clause.parent_table_referenced_column_name is None:
                    new_clause.parent_table_referenced_column_name = field_definition.name_in_db

            # Sustituyo el nombre del campo por el equivalente en la base de datos
            new_clause.field_name = field_definition.name_in_db
            # Asignar el alias de la tabla resuelto anteriormente
            # Si es una join clause, si no hay alias debe utilizar lo que especifique la definición del campo
            new_clause.table_alias = new_table_alias

            # Lo añado a la lista
            clauses_translated.append(new_clause)

        return clauses_translated

    def find_by_filtered_query(self, fields: List[FieldClause] = None, filters: List[FilterClause] = None,
                               order_by: List[OrderByClause] = None, joins: List[JoinClause] = None,
                               group_by: List[GroupByClause] = None,
                               offset: int = None, limit: int = None) -> List[BaseEntity]:
        """
        Ejecuta una consulta SELECT sobre la tabla principal del dao.
        :param fields: Campos seleccionados.
        :param filters: Filtros.
        :param order_by: Cláusulas ORDER BY.
        :param joins: Cláusulas JOIN.
        :param group_by: Cláusulas GROUP BY.
        :param offset: Offset del límite de la consulta.
        :param limit: Límite de registros.
        :return: Lista de entidades encontradas.
        """
        # declaro una serie de campos para pasar a la función interna, asumiendo primero que son null.
        fields_translated = None
        filters_translated = None
        order_by_translated = None
        joins_translated = None
        group_by_translated = None
        # limit y offset no hace falta traducirlos, los paso tal cual

        # La idea es que estas listas de cláusulas vienen con los campos de las entidades modeladas en python, se trata
        # de traducirlas al modelo de la base de datos.

        # Campos
        if fields and len(fields) > 0:
            fields_translated = self.__resolve_translation_of_clauses(FieldClause, fields)

        # Filtros
        if filters and len(filters) > 0:
            filters_translated = self.__resolve_translation_of_clauses(FilterClause, filters)

        # Order by
        if order_by and len(order_by) > 0:
            order_by_translated = self.__resolve_translation_of_clauses(OrderByClause, order_by)

        # Group by
        if group_by and len(group_by) > 0:
            group_by_translated = self.__resolve_translation_of_clauses(GroupByClause, group_by)

        # Joins
        if joins and len(joins) > 0:
            joins_translated = self.__resolve_translation_of_clauses(JoinClause, joins, True)

        # RESULTADO
        return self.__find_by_filtered_query_internal(fields=fields_translated, filters=filters_translated,
                                                      order_by=order_by_translated, joins=joins_translated,
                                                      group_by=group_by_translated, offset=offset, limit=limit)

    def __find_by_filtered_query_internal(self, fields: List[FieldClause] = None, filters: List[FilterClause] = None,
                                          order_by: List[OrderByClause] = None, joins: List[JoinClause] = None,
                                          group_by: List[GroupByClause] = None,
                                          offset: int = None, limit: int = None) -> List[BaseEntity]:
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
        :return: Lista de entidades encontradas.
        """
        # Resuelto SELECT (por defecto, asterisco para todos los campos)
        select = '*'
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
        sql = f"SELECT {select.strip()} FROM {self.__table} {join.strip()} {filtro.strip()} {group.strip()} " \
              f"{orden.strip()} {limit_offset.strip()}"
        # El resultado es una lista de  diccionarios, pero hay que transformarlo en modelo de datos
        result_as_dict: dict = self.__execute_query_internal(sql=sql,
                                                             sql_operation_type=EnumSQLOperationTypes.SELECT_MANY)

        # Recorrer lista de diccionarios e ir transformando cada valor en una entidad base
        result: List[BaseEntity] = []
        if result_as_dict:
            for v in result_as_dict:
                result.append(self.entity_type.convert_dict_to_entity(v))

        return result
