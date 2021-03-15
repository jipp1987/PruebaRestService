import sys
import traceback
import types
from functools import wraps

from core.util import i18nutils

_known_error_types = [("IntegrityError", "i18n_base_knownError_integrityError"),
                      ("OperationalError", "i18n_base_knownError_operationalError")]
"""Errores conocidos y su clave i18n de error conocido, es lo que se intenta mostrar al usuario."""


class CustomException(Exception):
    """Excepción personalizada, a modo de barrera de fallos para intepretar las excepciones y no perder su
    información. Se utiliza en los servicios.
    """

    # Constructor
    def __init__(self, message, exception: Exception = None, exception_type=None, line=None):
        Exception.__init__(self)
        self.message = message
        self.exception = exception
        self.exception_type = exception_type
        self.line = line
        self.known_error = self.handle_known_exception()

    # Implementación de toString
    def __str__(self):
        return (self.known_error if self.known_error is not None else "") + self.message

    # A partir del tipo de excepción, establece un error conocido, normalmente para mostrar al usuario
    def handle_known_exception(self):
        """
        A partir del tipo de excepción, establece un error conocido, normalmente para mostrar al usuario
        :return: Mensaje con un mensaje que mostrar al usuario a partir de una excepción conocida
        """

        string = None
        if self.exception_type is not None:
            for pair_values in _known_error_types:
                # El tipo de excepción es la clave del diccionario
                if self.exception_type == pair_values[0]:
                    # Esto es el valor, que es una clave i18n y es el error conocido
                    string = i18nutils.translate(pair_values[1])
                    break

        return string


def catch_exceptions(function):
    """
    Decorador para capturar las excepciones de las funciones y tratarlas. Lo que hace es envolverlas a CustomException
    pero guardado en ésta la excepción original, su tipo y su traza formateada.

    :param function: Función que va a ser tratada. Se encierra en un trycatch para interpretar la excepción.
    :return: Decorador
    """

    # es un wrapper para funciones
    # lo que defino es un decorador, luego se le pone a las funciones para indicar que deben hacer esta rutina
    @wraps(function)
    def decorator(*args, **kwargs):
        try:
            # Python puede devolver la ejecución de una función
            # Si se produce algún error, uso el código except... para capturarla y tratarla a modo de barrera de fallos
            return function(*args, **kwargs)
        except CustomException as c:
            # Si ya ha sido envuelta en una CustomException, que la devuelva directamente
            raise c
        except Exception:
            # De esta forma obtengo información de la excepción
            exc_type, exc_instance, exc_traceback = sys.exc_info()

            # Con esto le doy un formato legible a la traza
            formatted_traceback = ''.join(traceback.format_tb(exc_traceback))

            # Las dos primeras líneas siempre van a ser las de exceptionhandler, las dos siguientes serán las de la
            # última llamada antes de lanzar el error, me interesan porque en ellas tengo el fichero, línea y función
            # donde falló
            formatted_traceback_split = formatted_traceback.split("\n")
            error_line = None

            # por si acaso compruebo el tamaño
            if formatted_traceback_split is not None and len(formatted_traceback_split) > 3:
                error_line = formatted_traceback_split[2:4]
                error_line = error_line[0].strip()

            # Elaboro el mensaje con la traza formateada, el tipo de error y el mensaje de error como tal
            message = '\n{0}\n{1}:\n{2}'.format(
                formatted_traceback,
                exc_type.__name__,
                exc_instance
            )

            # ojo porque lo que me interesa es lanzar la excepción hacia arriba, envuelta en una CustomException
            raise CustomException(message, exc_instance, exc_type.__name__, error_line)

    return decorator


class BugBarrier(type):
    """Metaclase para añadir a funciones de clases una barrera de errores."""

    def __new__(mcs, name, bases, attrs):
        # Recorrer atributos de la clase, buscando aquéllos que sean funciones para asignarles un decorador
        # dinámicamente
        for attr_name, attr_value in attrs.items():
            # si es una función, le añado el decorador
            if isinstance(attr_value, types.FunctionType): # noqa
                # descarto las funciones heredadas de object, que empiezan y acaban en "__"
                if callable(attr_value) and not attr_name.startswith("__"):
                    # A la función le añado el decorador catch_exceptions
                    attrs[attr_name] = catch_exceptions(attr_value)

        return super(BugBarrier, mcs).__new__(mcs, name, bases, attrs)
