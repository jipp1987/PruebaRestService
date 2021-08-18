import enum
from collections import namedtuple
from typing import List

from core.util.stringutils import auto_str


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


AggregateFunction = namedtuple('AggregateFunction', ['value', 'function_keyword'])
"""Tupla para propiedades de EnumAggregateFunctions. La uso para poder añadirle una propiedad al enumerado, 
aparte del propio valor."""


class EnumAggregateFunctions(enum.Enum):
    """Enumerado de funciones de agregado."""

    @property
    def function_keyword(self):
        return self.value.function_keyword

    COUNT = AggregateFunction(1, 'COUNT')
    MIN = AggregateFunction(2, 'MIN')
    MAX = AggregateFunction(3, 'MAX')


@auto_str
class FilterClause(object):
    """Clase para modelado de cláusulas WHERE para MySQL."""

    def __init__(self, field_name: str, filter_type: (EnumFilterTypes, str), object_to_compare: any,
                 table_alias: str = None, operator_type: (EnumOperatorTypes, str) = None, start_parenthesis: int = None,
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


@auto_str
class OrderByClause(object):
    """Clase para modelado de cláusulas ORDER BY para MySQL."""

    def __init__(self, field_name: str, order_by_type: (EnumOrderByTypes, str), table_alias: str = None):
        self.field_name = field_name
        """Nombre del campo."""
        self.order_by_type = order_by_type if isinstance(order_by_type, EnumOrderByTypes) \
            else EnumOrderByTypes[order_by_type]
        """Tipo de cláusula ORDER BY."""
        self.table_alias = table_alias
        """Alias de la tabla."""


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


@auto_str
class JoinClause(object):
    """Clase para modelado de cláusulas JOIN para MySQL."""

    def __init__(self, table_name: str, join_type: (EnumJoinTypes, str), parent_table: str = None,
                 parent_table_referenced_column_name: str = None, table_alias: str = None, id_column_name: str = "id"):
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


# GROUP BYs
@auto_str
class GroupByClause(object):
    """Clase para modelado de cláusulas GROUP BY para MySQL."""

    def __init__(self, field_name: str, table_alias: str = None):
        self.field_name = field_name
        """Nombre del campo sobre el que se va a aplicar la cláusula group by."""
        self.table_alias = table_alias
        """Alias de la tabla."""


# CAMPOS SELECT
@auto_str
class FieldClause(object):
    """Clase para modelado de campos SELECT para MySQL."""

    def __init__(self, field_name: str, table_alias: str = None, field_alias: str = None, is_lazy_load: bool = False,
                 aggregate_function: (EnumAggregateFunctions, str) = None):
        self.field_name = field_name
        """Nombre del campo SELECT."""
        self.table_alias = table_alias
        """Alias de la tabla."""
        self.field_alias = field_alias
        """Alias del campo."""
        self.is_lazy_load = is_lazy_load
        """Se utiliza para saber si un campo del SELECT es un lazyload, es decir, se refiere a una entidad anidada 
        pero sólo trae el id, no toda la entidad."""
        self.aggregate_function = None if aggregate_function is None \
            else (aggregate_function if isinstance(aggregate_function, EnumAggregateFunctions)
                  else EnumAggregateFunctions[aggregate_function])
        """Función de agregado opcional."""


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
