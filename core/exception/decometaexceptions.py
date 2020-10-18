import types

from core.exception.exceptionhandler import catch_exceptions


class DecoMetaExceptions(type):
    """Metaclase para añadir a funciones una barrera de errores."""

    def __new__(mcs, name, bases, attrs):
        # Recorrer atributos de la clase, buscando aquéllos que sean funciones para asignarles un decorador
        # dinámicamente
        for attr_name, attr_value in attrs.items():
            # si es una función, le añado el decorador
            if isinstance(attr_value, types.FunctionType):
                # descarto las funciones heredadas de object, que empiezan y acaban en "__"
                if callable(attr_value) and not attr_name.startswith("__"):
                    attrs[attr_name] = catch_exceptions(attr_value)

        return super(DecoMetaExceptions, mcs).__new__(mcs, name, bases, attrs)

