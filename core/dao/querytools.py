import enum
from collections import namedtuple
from dataclasses import dataclass
from typing import List

from core.util.listutils import LoopIterationObject


class EnumSQLOperationTypes(enum.Enum):
    """Enumerado de tipos de operaciones SQL."""
    SELECT_ONE = 1
    SELECT_MANY = 2
    INSERT = 3
    DELETE = 4
    UPDATE = 5


# FILTER
FilterType = namedtuple('FilterType', ['value', 'filter_keyword'])
"""Tupla para propiedades de EnumFilterTypes. La uso para poder añadirle una propiedad al enumerado, aparte del propio
valor."""


class EnumFilterTypes(enum.Enum):
    """Enumerado de tipos de filtros."""

    @property
    def filter_keyword(self):
        return self.value.filter_keyword

    EQUALS = FilterType(1, '=')
    NOT_EQUALS = FilterType(2, '<>')
    LIKE = FilterType(3, 'LIKE')
    NOT_LIKE = FilterType(4, 'NOT LIKE')
    IN = FilterType(5, 'IN')
    NOT_IN = FilterType(6, 'NOT IN')
    LESS_THAN = FilterType(7, '<')
    LESS_THAN_OR_EQUALS = FilterType(8, '<=')
    GREATER_THAN = FilterType(9, '>')
    GREATER_THAN_OR_EQUALS = FilterType(10, '>=')
    BETWEEN = FilterType(11, 'BETWEEN')


OperatorType = namedtuple('OperatorType', ['value', 'operator_keyword'])
"""Tupla para propiedades de EnumOperatorTypes. La uso para poder añadirle una propiedad al enumerado, aparte del propio
valor."""


class EnumOperatorTypes(enum.Enum):
    """Enumerado de tipos de operadores para filtros."""

    @property
    def operator_keyword(self):
        return self.value.operator_keyword

    AND = OperatorType(1, 'AND')
    OR = OperatorType(2, 'OR')


class FilterClause(object):
    """Clase para modelado de cláusulas WHERE para MySQL."""

    def __init__(self, field_name: str, filter_type: EnumFilterTypes, object_to_compare: any, table_alias: str,
                 operator_type: EnumOperatorTypes = None, start_parenthesis: int = None, end_parenthesis: int = None):
        self.field_name = field_name
        """Nombre del campo."""
        self.filter_type = filter_type
        """Tipo de filtro."""
        self.object_to_compare = object_to_compare
        """Objeto a comparar."""
        self.table_alias = table_alias
        """Alias de la tabla."""
        self.operator_type = operator_type if operator_type is not None else EnumOperatorTypes.AND
        """Tipo de operador que conecta con el filtro inmediatamente anterior. Si null, se asume que es AND."""
        self.start_parenthesis = start_parenthesis
        """Número de paréntesis al principio."""
        self.end_parenthesis = end_parenthesis
        """Número de paréntesis al final."""


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
        is_last: bool = iteration_object.is_last

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

        # TODO Tratamiento del tipo de filtro
        # if item.filter_type == EnumFilterTypes.IN or EnumFilterTypes.NOT_IN or EnumFilterTypes.BETWEEN:

        # Crear filtro
        # Me guardo el operador para concatenar filtros en una variable, para que sea más legible el código
        operator: str = item.operator_type.operator_keyword
        filtro_arr.append(f"{'WHERE ' if not filtro_arr else (' ' if is_last else f' {operator} ')}"
                          f"{start_parenthesis}{item.table_alias}.{item.field_name} {item.filter_type.filter_keyword} "
                          f"{compare}{end_parenthesis}")


# ORDER BYs
OrderByType = namedtuple('OrderByType', ['value', 'order_by_keyword'])
"""Tupla para propiedades de EnumOrderByTypes. La uso para poder añadirle una propiedad al enumerado, aparte del propio
valor."""


class EnumOrderByTypes(enum.Enum):
    """Enumerado de tipos de OrderBy."""

    @property
    def order_by_keyword(self):
        return self.value.order_by_keyword

    ASC = OrderByType(1, 'ASC')
    DESC = OrderByType(2, 'DESC')


class OrderByClause(object):
    """Clase para modelado de cláusulas ORDER BY para MySQL."""

    def __init__(self, field_name: str, order_by_type: EnumOrderByTypes, table_alias: str):
        self.field_name = field_name
        """Nombre del campo."""
        self.order_by_type = order_by_type
        """Tipo de cláusula ORDER BY."""
        self.table_alias = table_alias
        """Alias de la tabla."""


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
        is_last: bool = iteration_object.is_last

        # Crear order by: si es el primero de la lista, añadir cláusula ORDER BY, sino añadir coma (si no es el último)
        order_by_arr.append(f"{'ORDER BY ' if not order_by_arr else (' ' if is_last else ', ')}"
                            f"{item.table_alias}.{item.field_name} {item.order_by_type.order_by_keyword}")


# JOINS
JoinType = namedtuple('JoinType', ['value', 'join_keyword'])
"""Tupla para propiedades de EnumJoinTypes. La uso para poder añadirle una propiedad al enumerado, aparte del propio
valor."""


class EnumJoinTypes(enum.Enum):
    """Enumerado de tipos de OrderBy."""

    @property
    def join_keyword(self):
        return self.value.join_keyword

    INNER_JOIN = JoinType(1, 'INNER JOIN')
    LEFT_JOIN = JoinType(2, 'LEFT JOIN')
    RIGHT_JOIN = JoinType(3, 'RIGHT JOIN')


class JoinClause(object):
    """Clase para modelado de cláusulas JOIN para MySQL."""

    def __init__(self, table_name: str, join_type: EnumJoinTypes, table_alias: str = None):
        self.table_name = table_name
        """Nombre de la tabla hacia la que se va a hacer join."""
        self.join_type = join_type
        """Tipo de cláusula JOIN."""
        self.table_alias = table_alias if table_alias is not None else self.table_name
        """Alias de la tabla. Si no se ha pasado como parámetro en el constructor, el alias de la tabla es el nombre 
        de la tabla."""


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
        join_arr.append(f"{item.join_type.join_keyword} {item.table_name} {item.table_alias} ")


# GROUP BYs
class GroupByClause(object):
    """Clase para modelado de cláusulas GROUP BY para MySQL."""

    def __init__(self, field_name: str, table_alias: str):
        self.field_name = field_name
        """Nombre del campo sobre el que se va a aplicar la cláusula group by."""
        self.table_alias = table_alias
        """Alias de la tabla."""


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
        is_last: bool = iteration_object.is_last

        # Crear group by: si es el primero de la lista, añadir cláusula GROUP BY, sino añadir coma (si no es el último)
        group_by_arr.append(f"{'GROUP BY ' if not group_by_arr else (' ' if is_last else ', ')}"
                            f"{item.table_alias}.{item.field_name} ")


# CAMPOS SELECT
class FieldClause(object):
    """Clase para modelado de campos SELECT para MySQL."""

    def __init__(self, field_name: str, table_alias: str):
        self.field_name = field_name
        """Nombre del campo SELECT."""
        self.table_alias = table_alias
        """Alias de la tabla."""


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
        select_arr.append(f"{item.table_alias}.{item.field_name} {(' ' if is_last else ', ')} ")


# OBJETO QUERY
@dataclass(init=True)
class QueryObject(object):
    """Clase para el modelado de consultas. Contiene distintos tipos de objetos para fabricar la query."""
    # Lista de filtros.
    filters: List[FilterClause]
    # Lista de order by.
    order: List[OrderByClause]
    # Lista de joins.
    joins: List[JoinClause]
    # Lista de group bys.
    group_by: List[GroupByClause]
    # Lista de campos.
    fields: List[FieldClause]
