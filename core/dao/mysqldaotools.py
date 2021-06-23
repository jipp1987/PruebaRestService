import copy
from typing import List, Union, Type, Dict, Tuple

from core.dao.querytools import EnumFilterTypes, FilterClause, OrderByClause, JoinClause, GroupByClause, FieldClause
from core.exception.exceptionhandler import CustomException
from core.model.modeldefinition import BaseEntity, FieldDefinition
from core.util.i18nutils import translate
from core.util.listutils import LoopIterationObject

"""

La idea es tener una clase que, según el motor de base de datos elegido, transforme listas de cláusulas-objectos 
FilterClause, OrderByClause, JoinClause, GroupByClause y FieldClause enviadas desde BaseDao y que están formadas no 
según el modelo de la base de datos, sino según los objetos que representan dicho modelo en Python: de ese modo, cuando 
desde un cliente tengan que modelar los objetos de acuerdo a la api no tienen porqué conocer el modelo exacto en la 
base de datos, sólo el modelo según Python. 

Esta clase traducirá las cláusulas según Python a cláusulas según la base 
de datos utilizando el mapa proporcionado por las entidades modeladas (get_model_dict, un mapa cuya clave es un string 
con el nombre de cada campo en el modelo de Python y el valor un objeto FieldDefinition que contiene el nombre del campo 
en la base de datos, el tipo de campo, si es obligatorio...). Al final se devuelve otro listado con las cláusulas para 
que se transformen en una cláusula MySQL inteligible para el motor; las cláusulas originales pasadas como parámetro no 
se modifican, se clonan y sobre ese clonado se van haciendo cambios para no modificar lo que el llamante ha pasado como 
parámetro.

La traducción como tal la realiza la función resolve_translation_of_clauses, pero depende del tipo de cláusula del 
listado pasado como parámetro:
- FieldClause: Campos de la cláusula SELECT. Si fuesen campos de otras entidades anidadas sobre la entidad principal, 
vendrían con el formato campo1.campo2.campo3... Se hace un split por el punto, y se va buscando cada campo dentro del 
mapa de relación con la base de datos. Lo que se intenta es generar un alias de tabla (usando el separador 
_join_alias_separator) para identificar al campo en la query: por ejemplo, imaginemos que la entidad base es clientes, 
y queremos acceder al campo username del usuario_creacion del tipo de cliente asociado a un cliente. En la FieldClause 
según Python vendría tipo_cliente.usuario_creacion.username; lo que se hace es ir buscando poco a poco en las 
FieldDefinitions de las clases implicadas, partiendo de la principal y navegando hasta el penúltimo campo del split, de 
tal modo que al final el alias de la tabla para ese campo en la consulta final sería algo así como 
tipo_cliente$456$usuario_creacion (observad que se utilizan los mismos nombres que los campos según Python, eso es 
porque durante la traducción de las JoinClauses a cada tabla implicada se le pone como alias el nombre del campo según 
Python, aunque el nombre de la tabla en sí es obviamente el auténtico de la base de datos). Durante la traducción de 
estas cláusulas, además, se pasa como parámetro un mapa join_alias_table_name cuya clave es cada alias de campo y su 
valor es una tupla con ciertos valores: este mapa se utiliza para que, tras ejecutar la consulta, se pueda transformar 
el  resultado obtenido a una lista de objetos de Python (en lugar de un mapa que es lo que devuelve el conector de 
MySQL). Para los alias de los campos se utiliza _field_alias_separator, para que la query se entienda mejor.
- FilterClause: Muy parecido a los FieldClause, pero no hace falta pasarle el mapa de relación de alias de campos. 
Traduce las cláusulas de filtrado.
- OrderByClause: Muy parecido a los FieldClause, pero no hace falta pasarle el mapa de relación de alias de campos. 
Traduce las cláusulas para ordenación de resultados.
- GroupByClause: Muy parecido a los FieldClause, pero no hace falta pasarle el mapa de relación de alias de campos. 
Traduce las cláusulas de agrupado.
- JoinClause: Éste es un caso especial, para empezar la traducción de estas cláusulas parte de la función 
resolve_translation_of_joins (que internamente llama a resolve_translation_of_clauses). El motivo de utilizar una 
función a modo de "envoltura" es porque hay que ir rellenando un mapa join_alias_dict que se utiliza para saber si ya 
se ha hecho Join a una tabla previamente, para utilizar el mismo alias que se le hubiere dado en su momento. En lo que 
respecta a resolve_translation_of_clauses, también se hace split por el punto con la idea de poder ir resolviendo 
posibles entidades anidadas desde la principal, pero el objetivo aquí es identificar las tablas que van a formar parte 
del Join y asignarles un alias que será el nombre del campo según el modelo de Python (se utiliza _join_alias_separator 
y cuando se forma el alias se utilizan todos los campos del split a diferencia de los casos anteriores, que llegan 
hasta el penúltimo), de tal como que la traducción de tipo_cliente.usuario_creacion se traduciría como 
tipo_cliente$456$usuario_creacion.

"""

_field_alias_separator: str = "$123$"
"""Separador de los alias de los campos, para la traducción del resultado de la consulta al modelo de Python."""
_join_alias_separator: str = "$456$"
"""Separador de los alias de los joins, para la traducción del resultado de la consulta al modelo de Python."""


def resolve_filter_clause(iteration_object: LoopIterationObject, filtro_arr: List[str]):
    """
    Resuelve un filtro, creando un string y añadiéndolo al listado pasado como parámetro.
    :param iteration_object: Objecto de iteración del bucle optimizado.
    :param filtro_arr: Listado de strings para almacenar filtros ya resueltos.
    :return: None.
    """
    if filtro_arr is not None:
        # Desde el objeto de iteración obtengo los valores para operar en la función
        item: FilterClause = iteration_object.item
        is_first: bool = iteration_object.is_first

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

        # Tratar el tipo de filtro
        compare = None
        if item.filter_type == EnumFilterTypes.LIKE or item.filter_type == EnumFilterTypes.NOT_LIKE:
            # Filtro LIKE: poner comodín % al principio y al final
            compare = f"%{item.object_to_compare}%"
        elif item.filter_type == EnumFilterTypes.IN or item.filter_type == EnumFilterTypes.NOT_IN:
            # Filtro IN y NOT IN: el objeto a comparar es una lista, concatenar los elementos por comas
            if len(item.object_to_compare) > 1:
                for idx, i in enumerate(item.object_to_compare):
                    # Si el objeto es string, encerrarlo entre comillas simples
                    element = f"'{i}'" if isinstance(i, str) else str(i)

                    # Según sea el primer elemento, el último o del medio, tratarlo
                    if idx == 0:
                        # Primer elemento
                        compare = f"({element}"
                    elif idx == len(item.object_to_compare) - 1:
                        # Último elemento
                        compare = f", {element})"
                    else:
                        compare = f", {element}"
            else:
                compare = f"({str(item.object_to_compare[0])})"
        else:
            # En cualquier otro caso, forma de string
            compare = str(item.object_to_compare)

        # Si el objeto a comparar es un string, encerrarlo entre comillas simples
        compare = f'\'{compare}\'' if isinstance(item.object_to_compare, str) else compare

        # Crear filtro
        # Me guardo el operador para concatenar filtros en una variable, para que sea más legible el código
        operator: str = item.operator_type.operator_keyword
        filter_too_add = (f"{'WHERE ' if is_first else f' {operator} '}"
                          f"{start_parenthesis}{item.table_alias}.{item.field_name} {item.filter_type.filter_keyword} "
                          f"{compare}{end_parenthesis}")
        filtro_arr.append(filter_too_add)


def resolve_order_by_clause(iteration_object: LoopIterationObject, order_by_arr: List[str]):
    """
    Resuelve un order by, creando un string y añadiéndolo al listado pasado como parámetro.
    :param iteration_object: Objecto de iteración del bucle optimizado.
    :param order_by_arr: Listado de strings para almacenar order bys ya resueltos.
    :return: None.
    """
    # Sólo hacer proceso si la lista es no nula
    if order_by_arr is not None:
        # Desde el objeto de iteración obtengo los valores para operar en la función
        item: OrderByClause = iteration_object.item
        is_first: bool = iteration_object.is_first

        # Crear order by: si es el primero de la lista, añadir cláusula ORDER BY, sino añadir coma (si no es el último)
        order_by_arr.append(f"{'ORDER BY ' if is_first else ', '}"
                            f"{item.table_alias}.{item.field_name} {item.order_by_type.order_by_keyword}")


def resolve_join_clause(iteration_object: LoopIterationObject, join_arr: List[str]):
    """
    Resuelve un join, creando un string y añadiéndolo al listado pasado como parámetro.
    :param iteration_object: Objecto de iteración del bucle optimizado.
    :param join_arr: Listado de strings para almacenar joins ya resueltos.
    :return: None.
    """
    # Sólo hacer proceso si la lista es no nula
    if join_arr is not None:
        # Desde el objeto de iteración obtengo los valores para operar en la función
        item: JoinClause = iteration_object.item
        # Crear join
        join_arr.append(f" {item.join_type.join_keyword} {item.table_name} {item.table_alias} "
                        f"ON {item.table_alias}.{item.id_column_name} = "
                        f"{item.parent_table}.{item.parent_table_referenced_column_name}")


def resolve_group_by_clause(iteration_object: LoopIterationObject, group_by_arr: List[str]):
    """
    Resuelve un order by, creando un string y añadiéndolo al listado pasado como parámetro.
    :param iteration_object: Objecto de iteración del bucle optimizado.
    :param group_by_arr: Listado de strings para almacenar group bys ya resueltos.
    :return: None.
    """
    # Sólo hacer proceso si la lista es no nula
    if group_by_arr is not None:
        # Desde el objeto de iteración obtengo los valores para operar en la función
        item: GroupByClause = iteration_object.item
        is_first: bool = iteration_object.is_first

        # Crear group by: si es el primero de la lista, añadir cláusula GROUP BY, sino añadir coma (si no es el último)
        group_by_arr.append(f"{'GROUP BY ' if is_first else ', '}"
                            f"{item.table_alias}.{item.field_name} ")


def resolve_field_clause(iteration_object: LoopIterationObject, select_arr: List[str]):
    """
    Resuelve un order by, creando un string y añadiéndolo al listado pasado como parámetro.
    :param iteration_object: Objecto de iteración del bucle optimizado.
    :param select_arr: Listado de strings para almacenar campos SELECT ya resueltos.
    :return: None.
    """
    # Sólo hacer proceso si la lista es no nula
    if select_arr is not None:
        # Desde el objeto de iteración obtengo los valores para operar en la función
        item: FieldClause = iteration_object.item
        is_last: bool = iteration_object.is_last

        # Añadir campo a la SELECT, si no es el último añadir comas
        select_arr.append(f"{item.table_alias}.{item.field_name} "
                          f"{item.field_alias if item.field_alias is not None else ''} {('' if is_last else ', ')} ")


def resolve_limit_offset(limit: int, offset: int = None) -> str:
    """
    Devuelve un string con la cláusula limit (con offset opcional.)
    :param limit: Límite de registros de la consulta.
    :param offset: Índice inferior desde el que comenzar la consulta.
    :return: Cláusula LIMIT.
    """
    if offset is not None:
        limit_offset = f'LIMIT {str(offset)}, {str(limit)}'
    else:
        limit_offset = f'LIMIT {str(limit)}'

    return limit_offset


def resolve_translation_of_joins(clauses_list: list, base_entity_type: Type[BaseEntity], table_db_name: str):
    """
    Resuelve la traducción de select, filtros, order_by y group_by.
    :param clauses_list: Lista de cláusulas a traducir.
    :param table_db_name: Nombre de la tabla principal de la consulta.
    :param base_entity_type: Tipo de la entidad base de la tabla principal de la consulta.
    el nombre del campo en Python.
    :return: Lista de filtros, order, group o fields traducidos a mysql.
    """
    join_alias_dict: Dict[str, str] = {}
    """Lo utilizo para guardar una correlación entre los nombres de las tablas en la base de datos y el alias que le 
    doy en la consulta."""

    # Resolver la lista de joins
    clauses_translated: list = resolve_translation_of_clauses(clause_type=JoinClause, clauses_list=clauses_list,
                                                              base_entity_type=base_entity_type,
                                                              table_db_name=table_db_name,
                                                              join_alias_table_name=None,
                                                              join_alias_dict=join_alias_dict)
    # Si se ha hecho un join a un campo anidado de un campo anidado, tengo que resolver el nombre de la tabla padre de
    # tal manera que coincida con el alias de dicha tabla resuelto en un paso anterior: por ejemplo, hago join de
    # clientes a tipos de cliente (alias tipo_cliente), y luego join de tipos de cliente al usuario de creación, con
    # lo cual el alias es el mismo resuelto en el paso anterior, tipo_cliente.
    for c in clauses_translated:
        if c.parent_table in join_alias_dict:
            c.parent_table = join_alias_dict[c.parent_table]

    return clauses_translated


def resolve_translation_of_clauses(clause_type: type, clauses_list: list, base_entity_type: Type[BaseEntity],
                                   table_db_name: str,
                                   join_alias_table_name: Dict[str, Tuple[str, Union[str, None],
                                                                          Type[BaseEntity]]] = None,
                                   join_alias_dict: Dict[str, str] = None):
    """
    Resuelve la traducción de select, filtros, order_by y group_by.
    :param clause_type: Tipo de cláusula.
    :param clauses_list: Lista de cláusulas a traducir.
    :param base_entity_type: Tipo de la entidad base de la tabla principal de la consulta.
    :param table_db_name: Nombre de la tabla principal de la consulta.
    :param join_alias_table_name: Diccionario empleado para mantener una relación entre los alias de las tablas y
    el nombre del campo en Python. Sólo es necesario pasarlo como parámetro para la traducción de los FieldClauses.
    :param join_alias_dict: Lo utilizo para guardar una correlación entre los nombres de las tablas en la base de datos
    y el alias que le doy en la consulta. Sólo es necesario pasarlo como parámetro para la traducción de los
    JoinClauses.
    :return: Listado de cláusulas traducidos a mysql.
    """
    # Declaración de campos a asignar en bucle
    clauses_translated = []
    new_clause: clause_type
    field_definition: Union[FieldDefinition, None]
    new_table_alias: Union[str, None]
    field_name_array: List[str]
    field_name_array_last_index: int
    entity_type: Union[Type[BaseEntity], None]

    is_join_clause: bool = clause_type == JoinClause
    """Indica si es una JoinClause para hacer operaciones especiales."""

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
                    field_definition = base_entity_type.get_model_dict().get(val)
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
                        field_definition = field_definition.field_type.get_model_dict().get(val)
                        new_clause.parent_table = new_clause.parent_table if new_clause.parent_table is not None \
                            else join_parent_table_dict[field_name_array[field_name_array_last_index - idx]]

                    # Si no tiene alias, el alias es la concatenación de todos los campos anidados hasta el íncidice
                    # final no incluido, reemplazando los puntos por guiones. Lo hago así para evitar errores cuando
                    # dos tablas tienen un campo que se llama igual y quiero traerme los dos. Si es una join clause,
                    # que coja todos los elementos, lo de llegar hasta el penúltimo es para el resto porque las join
                    # clauses son las distintas tablas como tal y el resto de cláusulas son campos de las mismas.
                    new_table_alias = new_clause.table_alias if new_clause.table_alias is not None else \
                        _join_alias_separator.join(field_name_array if is_join_clause else field_name_array[0:-1])

                    # Lo compruebo por si acaso, pero no debería hacer falta, si llega hasta aquí el tipo debe ser
                    # BaseEntity.
                    if not is_join_clause and issubclass(field_definition.field_type, BaseEntity):
                        entity_type = field_definition.field_type
                        field_definition = entity_type.get_model_dict().get(val)  # noqa

                # Añadir al mapa de los joins una clave-valor: clave es el nombre del campo, valor es la tabla
                # relacionada.
                try:
                    join_parent_table_dict[val] = field_definition.referenced_table_name
                except AttributeError:
                    # Si se produce esta excepción, es que se ha enviado un campo que no existe
                    raise CustomException(
                        translate("i18n_base_commonError_unknown_field", None, val, field_name_array[idx - 1]))
        else:
            # En caso de que sea un campo normal, el alias será el que venga en la entidad o bien el nombre de
            # la tabla del DAO.
            field_definition = base_entity_type.get_model_dict().get(f.table_name if is_join_clause else f.field_name)

            if is_join_clause:
                # La tabla padre será la del propio dao
                new_clause.parent_table = new_clause.parent_table if new_clause.parent_table is not None \
                    else table_db_name
            else:
                # Si no es una join clause y sólo hay un campo tras el split, la entidad será la del dao
                new_table_alias = new_clause.table_alias if new_clause.table_alias is not None else table_db_name
                entity_type = base_entity_type

                # Si en este punto fuese null la definición de campo, es que dicho campo no existe.
                if field_definition is None:
                    raise CustomException(
                        translate("i18n_base_commonError_unknown_field", None, f.field_name, base_entity_type.__name__))

        # Parte especial para cláusulas join
        if is_join_clause and field_definition is not None:
            # La tabla será la tabla referenciada
            new_clause.table_name = field_definition.referenced_table_name

            # El alias será también el nombre de la tabla
            if new_table_alias is None:
                new_table_alias = new_clause.table_alias if new_clause.table_alias is not None else \
                    field_name_array[-1]

            # Nombre del campo id de la clase
            if new_clause.id_column_name is None:
                if issubclass(field_definition.field_type, BaseEntity):
                    new_clause.id_column_name = field_definition.field_type.get_id_field_name_in_db()  # noqa
                else:
                    # Esto no debería suceder.
                    raise CustomException(
                        translate("i18n_base_commonError_query_translate", None, str(new_clause)))

            # Nombre del campo referenciado en la base de datos
            if new_clause.parent_table_referenced_column_name is None:
                new_clause.parent_table_referenced_column_name = field_definition.name_in_db

        # Lanzar error si no existe uno de estos objetos
        if field_definition is None or new_table_alias is None or (clause_type == FieldClause
                                                                   and entity_type is None):
            raise CustomException(translate("i18n_base_commonError_query_translate", None, str(new_clause)))

        # Sustituyo el nombre del campo por el equivalente en la base de datos
        new_clause.field_name = field_definition.name_in_db
        # Asignar el alias de la tabla resuelto anteriormente
        # Si es una join clause, si no hay alias debe utilizar lo que especifique la definición del campo
        new_clause.table_alias = new_table_alias

        if is_join_clause:
            # Añadir al mapa de joins y alias una nueva clave-valor: la clave es el nombre de la tabla referenciada y el
            # valor es el nombre del join
            if new_clause.table_name not in join_alias_dict:
                join_alias_dict[new_clause.table_name] = new_clause.table_alias
        else:
            # Establecer alias de los campos seleccionados, lo necesito para transformar el resultado de la consulta
            # en objetos Python. En este caso el alias lo establezco yo, ignorando lo que me pueda haber llegado.
            if clause_type == FieldClause:
                f_alias = _field_alias_separator.join(new_clause.table_alias.split('.'))
                f_alias = f'{f_alias}{_field_alias_separator}{field_name_array[-1]}'
                new_clause.field_alias = f_alias

                # Añado nueva clave al mapa de alias. La clave es el alias concatenado con el campo seleccionado
                # (último elemento de la lista anterior). El valor será el tipo de entidad y el nombre del campo
                # correspondiente en el modelo de Python. Como tercer valor paso None si sólo es un campo, o todos los
                # campos hasta el último no incluido si son más: lo necesitaré para convertir el diccionario resultante
                # a objetos Python, para saber a qué campo corresponde en cada clase. El cuarto valor es el último
                # índice, que me indica el nivel de anidación de entidades partiendo de la base del dao.
                join_alias_table_name[new_clause.field_alias] = \
                    (new_clause.field_name, ('.'.join(field_name_array[:-1]) if field_name_array_last_index > 0
                                             else None), entity_type)

        # Lo añado a la lista
        clauses_translated.append(new_clause)

    return clauses_translated


def get_field_names_as_str_for_insert(base_entity: BaseEntity):
    """
    Devuelve una cadena con los nombres de los campos separados por comas.
    :param base_entity: Entidad base.
    :return: Una cadena de los campos de la entidad cuyo primer valor será el campo del id.
    """
    base_entity_type = type(base_entity)
    cadena: str = base_entity_type.get_id_field_name_in_db()

    # Recorrer los nombres de los campos del objeto e ir concatenándolos separados por comas
    d = base_entity_type.get_model_dict()
    for key, value in d.items():
        # key es un string con el nombre del campo dentro del objeto.
        # Value es una objeto de tipo FieldDefinition
        if key != base_entity_type.get_id_field_name():
            cadena += ", " + value.name_in_db

    return cadena


def get_field_values_as_str_for_insert(base_entity: BaseEntity, is_id_included: bool = False):
    """
    Devuelve una cadena con los valores de los campos de la entidad encadenados por comas
    :param base_entity: Entidad base.
    :param is_id_included: Si True, empieza por el valor del campo id; si False, empieza con "null". False
    por defecto.
    :return: str
    """
    # Si 'is_id_included', incluyo el valor del campo id, sino pongo null. Útil pasarlo como False para inserts
    base_entity_type = type(base_entity)
    cadena = getattr(base_entity, base_entity_type.get_id_field_name_in_db()) if is_id_included else "null"

    # Recorrer los nombres de los campos del objeto e ir concatenándolos separados por comas
    d = base_entity_type.get_model_dict()

    for key, value in d.items():
        # key es un string con el nombre del campo dentro del objeto.
        # Value es un objeto de tipo FieldDefinition
        if key != base_entity_type.get_id_field_name():
            v = getattr(base_entity, key)

            # Hay que comprobar si el campo es de tipo BaseEntity, en ese caso habrá que usar el campo id de éste
            # como valor
            if issubclass(value.field_type, BaseEntity) and v is not None:
                # Con esto obtengo el valor del id del campo referenciado
                v = getattr(v, type(v).get_id_field_name())

            # Si es un str, encerrarlo entre comillas simples
            if isinstance(v, str):
                cadena += ", '" + str(v) + "'"
            elif isinstance(v, bytes):
                # Si son bytes, decodificarlos como latin1
                cadena += ", '" + v.decode("latin1") + "'"
            elif v is None:
                cadena += f", null"
            else:
                cadena += ", " + str(v)

    return cadena


def get_fields_with_value_as_str_for_update(base_entity: BaseEntity):
    """
    Devuelve una cadena con los valores del objeto a modo de "atributo = valor" separados por ", ".
    :param base_entity: Entidad base.
    :return: str
    """
    base_entity_type = type(base_entity)
    d = base_entity_type.get_model_dict()

    # Empiezo por el id (el nombre en el modelo de python y en la bd no tiene porqué coincidir)
    cadena = f'{base_entity_type.get_id_field_name_in_db()} = ' \
             f'{getattr(base_entity, base_entity_type.get_id_field_name())}'

    # Recorrer los nombres de los campos del objeto e ir concatenándolos separados por comas
    for key, value in d.items():
        # key es un string con el nombre del campo dentro del objeto.
        # Value es un objeto de tipo FieldDefinition
        if key != base_entity_type.get_id_field_name():
            v = getattr(base_entity, key)

            # Hay que comprobar si el campo es de tipo BaseEntity, en ese caso habrá que usar el campo id de éste
            # como valor
            if issubclass(value.field_type, BaseEntity) and v is not None:
                # Con esto obtengo el valor del id del campo referenciado
                v = getattr(v, value.field_type.get_id_field_name())

            # Si es un str, encerrarlo entre comillas simples
            if isinstance(v, str):
                cadena = f"{cadena} , {value.name_in_db} = '{v}'"
            elif isinstance(v, bytes):
                # Si son bytes, decodificarlos como latin1
                cadena = f"{cadena} , {value.name_in_db} = '{v.decode('latin1')}'"
            elif v is None:
                cadena = f"{cadena} , {value.name_in_db} = null"
            else:
                cadena = f"{cadena} , {value.name_in_db} = {v}"

    return cadena
