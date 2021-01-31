import abc
import copy
import gc
import threading
from collections import OrderedDict
from importlib.resources import Package
from typing import Dict, Union, List, Tuple, Type

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

    def __resolve_translation_of_clauses(self, clause_type: type, clauses_list: list,
                                         join_alias_table_name: Dict[str, Tuple[type, str, Union[str, None]]],
                                         is_join_clause: bool = False):
        """
        Resuelve la traducción de select, filtros, order_by y group_by.
        :param clause_type: Tipo de cláusula.
        :param clauses_list: Lista de cláusulas a traducir.
        :param join_alias_table_name: Diccionario empleado para mantener una relación entre los alias de las tablas y
        el nombre del campo en Python.
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
        entity_type: Union[Type[BaseEntity], None]

        join_parent_table_dict: Dict[str, str]
        """Esto lo uso para los joins, para poder mantenerlos relacionados. La clave es el nombre del campo y el valor 
        es el nombre real de la tabla en la base de datos."""

        for f in clauses_list:
            # Copio el objeto entrante
            new_clause = copy.deepcopy(f)
            field_definition = None
            new_table_alias = None
            entity_type = None

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
                        # Voy almacenando la última definición de campo para reutilizarla justo antes de resolver el
                        # último valor.
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
                            new_clause.parent_table = new_clause.parent_table if new_clause.parent_table is not None \
                                else (self.__table if idx == 1 else join_parent_table_dict[field_name_array[-1]])

                        # Si no tiene alias, el alias es la concatenación de todos los campos anidados hasta el íncidice
                        # final no incluido, reemplazando los puntos por guiones. Lo hago así para evitar errores cuando
                        # dos tablas tienen un campo que se llama igual y quiero traerme los dos. Si es una join clause,
                        # que coja todos los elementos, lo de llegar hasta el penúltimo es para el resto porque las join
                        # clauses son las distintas tablas como tal y el resto de cláusulas son campos de las mismas.
                        new_table_alias = new_clause.table_alias if new_clause.table_alias is not None else \
                            ''.join(field_name_array[0:] if is_join_clause else
                                    field_name_array[0:-1]).replace('.', '-')
                        # Lo compruebo por si acaso, pero no debería hacer falta, si llega hasta aquí el tipo debe ser
                        # BaseEntity.
                        if issubclass(field_definition.field_type, BaseEntity):
                            entity_type = field_definition.field_type
                            field_definition = entity_type.get_model_dict().get(val)  # noqa

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
                else:
                    new_table_alias = new_clause.table_alias if new_clause.table_alias is not None else self.__table
                    # Si no es una join clause y sólo hay un campo tras el split, la entidad será la del dao
                    entity_type = self.entity_type

            # Parte especial para cláusulas join
            if is_join_clause and field_definition is not None:
                # La tabla será la tabla referenciada
                new_clause.table_name = field_definition.referenced_table_name

                # El alias será también el nombre de la tabla
                new_table_alias = new_clause.table_alias if new_clause.table_alias is not None else \
                    new_clause.table_name

                # Nombre del campo id de la clase
                if new_clause.id_column_name is None:
                    if issubclass(field_definition.field_type, BaseEntity):
                        new_clause.id_column_name = field_definition.field_type.get_id_field_name()  # noqa
                    else:
                        # Esto no debería suceder.
                        raise CustomException(translate("i18n_base_commonError_query_translate", None, str(new_clause)))

                # Nombre del campo referenciado en la base de datos
                if new_clause.parent_table_referenced_column_name is None:
                    new_clause.parent_table_referenced_column_name = field_definition.name_in_db

            # Lanzar error si no existe uno de estos objetos
            if field_definition is None or new_table_alias is None or (not is_join_clause and entity_type is None):
                raise CustomException(translate("i18n_base_commonError_query_translate", None, str(new_clause)))

            # Sustituyo el nombre del campo por el equivalente en la base de datos
            new_clause.field_name = field_definition.name_in_db
            # Asignar el alias de la tabla resuelto anteriormente
            # Si es una join clause, si no hay alias debe utilizar lo que especifique la definición del campo
            new_clause.table_alias = new_table_alias

            # Añado nueva clave al mapa de alias. La clave es el alias concatenado con el campo seleccionado
            # (último elemento de la lista anterior). El valor será el tipo de entidad y el nombre del campo
            # correspondiente en el modelo de Python. Le pongo delante el último índice, así tengo más fácil luego
            # ordenar las claves e ir rellenando campos del modelo de Python en orden. Como tercer valor paso None
            # si sólo es un campo, o todos los campos hasta el último no incluido si son más: lo necesitaré para
            # convertir el diccionario resultante a objetos Python, para saber a qué campo corresponde en cada clase.
            if not is_join_clause:
                join_alias_table_name[f'{field_name_array_last_index}.{new_clause.table_alias}.'
                                      f'{field_name_array[-1]}'] = (entity_type, new_clause.field_name,
                                                                    ('.'.join(field_name_array[:-1]) if
                                                                     field_name_array_last_index > 0 else None))

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

        # Diccionario empleado para mantener una relación entre los distintos alias de las tablas que ha especificado
        # el usuario al construir los objetos de modelado de la query, y el nombre que corresponde realmente al campo
        # dentro del propio objeto en Python.
        join_alias_table_name: Dict[str, Tuple[type, str, Union[str, None]]] = {}

        # La idea es que estas listas de cláusulas vienen con los campos de las entidades modeladas en python, se trata
        # de traducirlas al modelo de la base de datos.

        # Campos
        if fields and len(fields) > 0:
            fields_translated = self.__resolve_translation_of_clauses(FieldClause, fields, join_alias_table_name)

        # Filtros
        if filters and len(filters) > 0:
            filters_translated = self.__resolve_translation_of_clauses(FilterClause, filters, join_alias_table_name)

        # Order by
        if order_by and len(order_by) > 0:
            order_by_translated = self.__resolve_translation_of_clauses(OrderByClause, order_by, join_alias_table_name)

        # Group by
        if group_by and len(group_by) > 0:
            group_by_translated = self.__resolve_translation_of_clauses(GroupByClause, group_by, join_alias_table_name)

        # Joins
        if joins and len(joins) > 0:
            joins_translated = self.__resolve_translation_of_clauses(JoinClause, joins, join_alias_table_name, True)

        # Ordeno el diccionario según la clave, así luego será más sencillo convertir el diccionario en entidades de
        # acuerdo con un orden lógico. Esto sólo me devuelve una lista con las claves ordenadas, no un diccionario
        # ordenado.
        join_alias_table_name_list: list = sorted(join_alias_table_name)

        # Vuelco el resultado en un diccionario ordenado, el primer token de la clave del diccionario que es un número
        # empleado para saber la jerarquía de los campos calculada durante la traducción. En las claves del diccionario
        # ordenado no lo quiero, sino no va a coincidir con lo que me ha devuelto la consulta.
        join_alias_table_name_ordered: OrderedDict[str, Tuple[type, str, Union[str, None]]] = OrderedDict()
        for v in join_alias_table_name_list:
            join_alias_table_name_ordered['.'.join(v.split('.')[1:])] = join_alias_table_name[v]

        # Estos dos objetos ya no los necesito, los elimino.
        del join_alias_table_name_list, join_alias_table_name

        # RESULTADO: Devuelve una lista de diccionarios
        result_as_dict = self.__find_by_filtered_query_internal(fields=fields_translated, filters=filters_translated,
                                                                order_by=order_by_translated, joins=joins_translated,
                                                                group_by=group_by_translated, offset=offset,
                                                                limit=limit)

        # Elimino las listas de cláusulas traducidas, ya no las voy a necesitar
        del fields_translated, filters_translated, order_by_translated, joins_translated, group_by_translated
        # Libero memoria llamando explícitamente al recolector de basura
        gc.collect()

        # Recorrer lista de diccionarios e ir transformando cada valor en una entidad base
        result: List[BaseEntity] = []
        if result_as_dict:
            for v in result_as_dict:
                # Teniendo en cuenta la equivalencia de campos calculada en join_alias_table_name_ordered, crearé un
                # nuevo diccionario mediante el cual se irán instanciando nuevas entidades para añadir al resultado.
                for k, w in join_alias_table_name_ordered.items():
                    if k in v:
                        # Primero sustituyo la clave en el diccionario del resultado por el campo correspondiente en el
                        # objeto. En la tupla almacenada, este valor es el tercero (índex 2). El primer valor es el tipo
                        # de entidad base, y el segundo el nombre del campo como tal en dicha entidad.
                        # FIXME No está bien
                        old_value = v[k]
                        v[w[2]] = v.pop(k)
                        v[w[2]] = w[0]()
                        setattr(v[w[2]], w[1], old_value)
                        break

                result.append(self.entity_type.convert_dict_to_entity(v))

        return result

    def __find_by_filtered_query_internal(self, fields: List[FieldClause] = None, filters: List[FilterClause] = None,
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
        sql = f"SELECT {select.strip()} FROM {self.__table} {join.strip()} {filtro.strip()} " \
              f"{group.strip()} {orden.strip()} {limit_offset.strip()}"

        print(sql)

        # El resultado es una lista de  diccionarios, pero hay que transformarlo en modelo de datos
        result_as_dict: List[dict] = self.__execute_query_internal(sql=sql,
                                                                   sql_operation_type=EnumSQLOperationTypes.SELECT_MANY)

        return result_as_dict
