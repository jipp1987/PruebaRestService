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

        # Tratar el tipo de filtro
        compare = None
        if item.filter_type == EnumFilterTypes.LIKE or item.filter_type == EnumFilterTypes.NOT_LIKE:
            # Filtro LIKE: poner comodín % al principio y al final
            compare = f"%{item.object_to_compare}%"
        elif item.filter_type == EnumFilterTypes.IN or EnumFilterTypes.NOT_IN:
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
        compare = f"'{compare}'" if isinstance(item.object_to_compare, str) else compare

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


class JsonQuery(object):
    """Clase para el modelado de consultas desde JSON. Contiene distintos tipos de objetos para fabricar la query."""

    # La clase se inicializa a partir de un diccionario, este objeto está pensado para la recepción de filtros desde
    # json
    def __init__(self, d: dict):
        for a, b in d.items():
            # Comprobar si el valor es una instancia de lista o tupla
            if isinstance(b, (list, tuple)):
                # Para cada elemento de la lista o tupla, comprobar si es un diccionario. Si lo es, llamar
                # recursivamente a este constructor.
                setattr(self, a, [JsonQuery(x) if isinstance(x, dict) else x for x in b])
            else:
                # Si no lo es, igualmente comprobar si es un diccionario para llamar recursivamente a este constructor.
                setattr(self, a, JsonQuery(b) if isinstance(b, dict) else b)

    # PROPIEDADES Y SETTERS
    # Este objeto se crea desde un diccionario. En lugar de declarar los campos en el constructor, es mejor usar setters
    # para convertir las claves del diccionario en el objeto deseado. Si en el json string no viene una clave, el
    # atributo no existe en el objeto final. Por eso, luego se ha de tratar si este objeto tiene un atributo
    # determinado. NO asignar None a los atributos: si nos fijamos en el constructor, estoy usando
    # siempre un objeto JsonQuery y luego uso el atributo __dict__ del mismo para añadir objetos FilterClause,
    # JoinClause... a cada listado; si tuviese un atributo que no existe en alguno de estas clases (aunque sea None),
    # se produciría un error.
    @property
    def filters(self) -> List[FilterClause]:
        """Lista de filtros."""
        return self.__filters

    @filters.setter
    def filters(self, filters):
        if isinstance(filters, list) and filters:
            self.__filters = [] # noqa
            for f in filters:
                self.__filters.append(FilterClause(**f.__dict__))

    @property
    def order(self) -> List[OrderByClause]:
        """Lista de order by."""
        return self.__order

    @order.setter
    def order(self, order):
        if isinstance(order, list) and order:
            self.__order = [] # noqa
            for f in order:
                self.__order.append(OrderByClause(**f.__dict__))

    @property
    def joins(self) -> List[JoinClause]:
        """Lista de joins."""
        return self.__joins

    @joins.setter
    def joins(self, joins):
        if isinstance(joins, list) and joins:
            self.__joins = [] # noqa
            for f in joins:
                self.__joins.append(JoinClause(**f.__dict__))

    @property
    def group_by(self) -> List[GroupByClause]:
        """Lista de group by."""
        return self.__group_by

    @group_by.setter
    def group_by(self, group_by):
        if isinstance(group_by, list) and group_by:
            self.__group_by = [] # noqa
            for f in group_by:
                self.__group_by.append(GroupByClause(**f.__dict__))

    @property
    def fields(self) -> List[FieldClause]:
        """Lista de campos del SELECT."""
        return self.__fields

    @fields.setter
    def fields(self, fields):
        if isinstance(fields, list) and fields:
            self.__fields = [] # noqa
            for f in fields:
                self.__fields.append(FieldClause(**f.__dict__))

    @property
    def offset(self) -> int:
        """Offset del limit."""
        return self.__offset

    @offset.setter
    def offset(self, offset):
        if isinstance(offset, int):
            self.__offset = offset # noqa

    @property
    def limit(self) -> int:
        """Límite de la consulta."""
        return self.__limit

    @limit.setter
    def limit(self, limit):
        if isinstance(limit, int):
            self.__limit = limit # noqa
