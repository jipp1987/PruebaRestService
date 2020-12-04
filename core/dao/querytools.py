import enum
from collections import namedtuple

FilterType = namedtuple('FilterType', ['value', 'filter_operator'])
"""Tupla para propiedades de EnumFilterTypes. La uso para poder añadirle una propiedad al enumerado, aparte del propio
valor."""


class EnumFilterTypes(enum.Enum):
    """Enumerado de tipos de filtros."""

    @property
    def filter_operator(self):
        return self.value.filter_operator

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


class FilterClause(object):
    """Clase para modelado de cláusular WHERE para MySQL."""

    def __init__(self, field_name: str, filter_type: EnumFilterTypes, object_to_compare: any,
                 start_parenthesis: int = None, end_parenthesis: int = None):
        self.field_name = field_name
        """Nombre del campo."""
        self.filter_type = filter_type
        """Tipo de filtro."""
        self.object_to_compare = object_to_compare
        """Objeto a comparar."""
        self.start_parenthesis = start_parenthesis
        """Número de paréntesis al principio."""
        self.end_parenthesis = end_parenthesis
        """Número de paréntesis al final."""


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
    """Clase para modelado de cláusular ORDER BY para MySQL."""

    def __init__(self, field_name: str, order_by_type: EnumOrderByTypes):
        self.field_name = field_name
        """Nombre del campo."""
        self.order_by_type = order_by_type
        """Tipo de cláusula ORDER BY."""


class EnumSQLOperationTypes(enum.Enum):
    """Enumerado de tipos de operaciones SQL."""
    SELECT_ONE = 1
    SELECT_MANY = 2
    INSERT = 3
    DELETE = 4
    UPDATE = 5
