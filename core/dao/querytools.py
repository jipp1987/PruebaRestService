import enum
from collections import namedtuple
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

    def __init__(self, field_name: str, filter_type: (EnumFilterTypes, str), object_to_compare: any, table_alias: str,
                 operator_type: (EnumOperatorTypes, str) = None, start_parenthesis: int = None,
                 end_parenthesis: int = None):
        self.field_name = field_name
        """Nombre del campo."""
        self.filter_type = filter_type if isinstance(filter_type, EnumFilterTypes) else EnumFilterTypes[filter_type]
        """Tipo de filtro."""
        self.object_to_compare = object_to_compare
        """Objeto a comparar."""
        self.table_alias = table_alias
        """Alias de la tabla."""
        self.operator_type = (operator_type if isinstance(operator_type, EnumOperatorTypes)
                              else EnumOperatorTypes[operator_type]) if operator_type is not None \
            else EnumOperatorTypes.AND
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

    def __init__(self, field_name: str, order_by_type: (EnumOrderByTypes, str), table_alias: str):
        self.field_name = field_name
        """Nombre del campo."""
        self.order_by_type = order_by_type if isinstance(order_by_type, EnumOrderByTypes) \
            else EnumOrderByTypes[order_by_type]
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
        is_first: bool = iteration_object.is_first

        # Crear order by: si es el primero de la lista, añadir cláusula ORDER BY, sino añadir coma (si no es el último)
        order_by_arr.append(f"{'ORDER BY ' if is_first else ', '}"
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

    def __init__(self, table_name: str, join_type: (EnumJoinTypes, str), parent_table: str,
                 parent_table_referenced_column_name: str, table_alias: str = None, id_column_name: str = "id"):
        self.table_name = table_name
        """Nombre de la tabla hacia la que se va a hacer join."""
        self.join_type = join_type if isinstance(join_type, EnumJoinTypes) else EnumJoinTypes[join_type]
        """Tipo de cláusula JOIN."""
        self.table_alias = table_alias
        """Alias de la tabla."""
        self.parent_table = parent_table
        """Tabla padre."""
        self.parent_table_referenced_column_name = parent_table_referenced_column_name
        """Nombre de la columna referenciada en la tabla padre."""
        self.id_column_name = id_column_name
        """Nombre de la columna id de la tabla a enlazar."""


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
        join_arr.append(f"{item.join_type.join_keyword} {item.table_name} {item.table_alias} "
                        f"ON {item.table_alias}.{item.id_column_name} = "
                        f"{item.parent_table}.{item.parent_table_referenced_column_name}")


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
        is_first: bool = iteration_object.is_first

        # Crear group by: si es el primero de la lista, añadir cláusula GROUP BY, sino añadir coma (si no es el último)
        group_by_arr.append(f"{'GROUP BY ' if is_first else ', '}"
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
        select_arr.append(f"{item.table_alias}.{item.field_name} {('' if is_last else ', ')} ")


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


class JsonQuery(object):
    """Clase para el modelado de consultas desde JSON. Contiene distintos tipos de objetos para fabricar la query."""

    # La clase se inicializa a partir de un diccionario, este objeto está pensado para la recepción de filtros desde
    # json
    def __init__(self, d: dict):
        # Declaro los campos como None
        self.__filters = None
        self.__order = None
        self.__joins = None
        self.__group_by = None
        self.__fields = None
        self.__offset = None
        self.__limit = None

        # Recorrer diccionario estableciendo valores
        for a, b in d.items():
            setattr(self, a, b)

    # PROPIEDADES Y SETTERS
    # Este objeto se crea desde un json: por ello, en el constructor sólo se pasa un diccionario. Uso getters y setters
    # para establecer el valor desde éste y que las propiedades salgan con los tipos que necesito. Lo que hago es usar
    # el operador ** para descomponer cada elemento del listado (que python lo interpreta de json como un diccionario)
    # para que usar pares clave/valor para los argumentos del constructor de cada clase.
    @property
    def filters(self) -> List[FilterClause]:
        """Lista de filtros."""
        return self.__filters

    @filters.setter
    def filters(self, filters):
        if isinstance(filters, list) and filters:
            self.__filters = []
            for f in filters:
                self.__filters.append(FilterClause(**f))

    @property
    def order(self) -> List[OrderByClause]:
        """Lista de order by."""
        return self.__order

    @order.setter
    def order(self, order):
        if isinstance(order, list) and order:
            self.__order = []
            for f in order:
                self.__order.append(OrderByClause(**f))

    @property
    def joins(self) -> List[JoinClause]:
        """Lista de joins."""
        return self.__joins

    @joins.setter
    def joins(self, joins):
        if isinstance(joins, list) and joins:
            self.__joins = []
            for f in joins:
                self.__joins.append(JoinClause(**f))

    @property
    def group_by(self) -> List[GroupByClause]:
        """Lista de group by."""
        return self.__group_by

    @group_by.setter
    def group_by(self, group_by):
        if isinstance(group_by, list) and group_by:
            self.__group_by = []
            for f in group_by:
                self.__group_by.append(GroupByClause(**f))

    @property
    def fields(self) -> List[FieldClause]:
        """Lista de campos del SELECT."""
        return self.__fields

    @fields.setter
    def fields(self, fields):
        if isinstance(fields, list) and fields:
            self.__fields = []
            for f in fields:
                self.__fields.append(FieldClause(**f))

    @property
    def offset(self) -> int:
        """Offset del limit."""
        return self.__offset

    @offset.setter
    def offset(self, offset):
        if isinstance(offset, int):
            self.__offset = offset

    @property
    def limit(self) -> int:
        """Límite de la consulta."""
        return self.__limit

    @limit.setter
    def limit(self, limit):
        if isinstance(limit, int):
            self.__limit = limit
