import abc
import types
from typing import Type, Dict, Callable, List

from core.dao.basedao import BaseDao
from core.dao.querytools import FieldClause, FilterClause, JoinClause, OrderByClause, GroupByClause
from core.exception.exceptionhandler import BugBarrier
from core.model.modeldefinition import BaseEntity
from core.util.noconflict import makecls


class BaseService(object):
    """
    Clase abstract de la que han de heredar el resto de servicios del programa.
    """
    # Llamo a la factoría de metaclases para que me "fusione" las dos metaclases que me interesan.
    __metaclass__ = makecls(BugBarrier, abc.ABCMeta)

    def __init__(self, dao: BaseDao = None, entity_type: Type[BaseEntity] = None):
        """
        Constructor.
        :param dao: DAO.
        :param entity_type: Tipo de entidad.
        """
        self._dao = dao
        """Acceso a datos asociado al servicio."""

    # Sobrescribo __getattribute__ para interceptar las llamadas a las funciones con el objetivo de envolverlas
    # automáticamente en transacciones, a modo de interceptor de llamadas a funciones.
    def __getattribute__(self, name):
        # Obtengo los atributos de la clase usando la función de la superclase object
        attr = object.__getattribute__(self, name)

        # Con esto compruebo que sea un método público
        if isinstance(attr, types.MethodType) and not name.startswith('_'):
            # Creo una nueva función, que en realidad es la misma pero "envuelta" en la función de iniciar transacción
            def transaction_func(*args, **kwargs):
                result = self.__start_transaction(attr, *args, **kwargs)
                return result

            return transaction_func
        else:
            return attr

    def get_entity_type(self) -> type(BaseEntity):
        """
        Devuelve el tipo de entidad usando el dao asociado.
        :return: Tipo de entidad.
        """
        return self._dao.entity_type

    # TODO Esto no se ha probado con una función recursiva (una función que se llame a sí misma). Sí se ha probado con
    #  funciones que tienen dentro funciones del mismo service y de otros services, y funciona bien: sólo inicia
    #  transacción la función principal. Si no funcionase para una función recursiva, habría que nombrar a esas
    #  funciones de alguna manera, con un prefijo, de tal forma que se excluyan de la sobrescritura de __getattribute__,
    #  y manejar de forma manual la transacción en dicha función.
    def __start_transaction(self, function: Callable, *args, **kwargs):
        """
        Envuelve la función dentro de un contexto transaccional: se hace commit al final si no hay problemas,
        y si sucede algo se hace rollback.
        :param function: Función miembro a ejecutar. Se accede a ella poniendo primero su nombre prececido de punto
        y el nombre del objeto al que pertenece
        :param args: Argumentos de la función que no se han identificado por clave.
        :param kwargs: Argumentos de la función que se han identificado por clave.
        :return: Resultado de la función
        """
        # Creo un boolean para saber si me he tenido que conectar, con el fin de consignar la operación
        i_had_to_connect = False

        try:
            # Comprobar si el hilo necesita conectarse. Si no ha hecho falta es porque el pool de conexiones ya tiene
            # una conexión para el hilo actual.
            i_had_to_connect = self._dao.connect()

            # Realizar función
            result = function(*args, **kwargs)

            # Consignar operación (sólo si me tuve que conectar al principio). Es posible que un servicio llame a otros,
            # en ese caso no hay que hacer commit. El único que debe hacer commit es el primer método que llamó a los
            # demás, el que abrió la conexión para el hilo de ejecución actual.
            if i_had_to_connect:
                self._dao.commit()

            # Devolver resultado
            return result
        except Exception:
            # Rollback si hay error (sólo hace rollback la función original, la que inició la transacción y solicitó
            # la conexión del hilo)
            if i_had_to_connect:
                self._dao.rollback()
            raise
        finally:
            # Desconectar siempre al final (sólo desconecta la función original, la que inició la transacción y solicitó
            # la conexión del hilo)
            if i_had_to_connect:
                self._dao.disconnect()

    def insert(self, entity: BaseEntity):
        """
        Inserta un registro en la base de datos.
        :param entity: Objeto que hereda de BaseEntity.
        :return: Nada.
        """
        self._dao.insert(entity)

    def update(self, entity: BaseEntity):
        """
        Actualiza un registro en la base de datos.
        :param entity: Objeto que hereda de BaseEntity.
        :return: Nada.
        """
        self._dao.update(entity)

    def delete_entity(self, entity: BaseEntity):
        """
        Elimina un registro en la base de datos.
        :param entity: Objeto que hereda de BaseEntity.
        :return: Nada.
        """
        self._dao.delete_entity(entity)

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
        return self._dao.find_by_filtered_query(filters=filters, order_by=order_by, fields=fields, group_by=group_by,
                                                joins=joins, offset=offset, limit=limit)


class ServiceFactory(object):
    """
    Factoría de servicios, de tal modo que sólo se tendrá en el contexto de la aplicación una instancia de un servicio.
    """

    __services: Dict[str, BaseService] = {}
    """Diccionario de servicios ya instanciados. La clave es el nombre del servicio y el valor la instancia única del 
    mismo."""

    @classmethod
    def get_service(cls, class_to_instanciate: Type[BaseService]):
        """
        Devuelve una instancia de un servicio. Si no existe, la instancia y la guarda en el diccionario; si existe,
        devuelve la que tenga ya almacenada.
        :param class_to_instanciate: Clase del servicio a instanciar. Es el tipo, directamente, no el nombre.
        :return: Servicio.
        """
        # Obtengo el nombre de la clase
        class_name = class_to_instanciate.__name__

        # Si no existe, la creo y la almaceno en el diccionario
        if class_name not in cls.__services:
            cls.__services[class_name] = class_to_instanciate()

        # devuelvo la instancia del diccionario
        return cls.__services[class_name]
