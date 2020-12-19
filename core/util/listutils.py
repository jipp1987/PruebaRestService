from dataclasses import dataclass
from typing import List, Callable


# init=True me va a generar automáticamente un contructor con los atributos de la clase; frozen=True hará el objeto
# inmutable y si se intenta cambiar alguno de los campos lanzará excepción, sería un objeto de sólo lectura
@dataclass(init=True, frozen=True)
class LoopIterationObject(object):
    """Clase para modelado de items de iteración en bucles optimizados."""
    # Objeto del iterable.
    item: any
    # Es el primer objeto de la lista.
    is_first: bool
    # Es el último objeto de la lista.
    is_last: bool


def optimized_for_loop(list_to_loop: List[any], function: Callable, *args, **kwargs):
    """
    Optimización de for loop para listas. Se utiliza un iterator, que es más eficiente.
    :param list_to_loop: Lista a recorrer.
    :param function: Función a ejecutar. El primer parámetro de dicha función debe ser un elemento del tipo
    LoopIterationObject.
    :param args: Argumentos sin clave identificadora para la función a ejecutar.
    :param kwargs: Argumentos con clave identificadora para la función a ejecutar.
    :return: Lo que devuelva la función.
    """
    # Si está vacía, fin del proceso
    if not list_to_loop:
        pass

    # Para recorrer los listados, voy a usar un iterador, que es más eficiente.
    iterator: any = iter(list_to_loop)
    done_looping: bool = False
    return_object: any = None
    loop_object: LoopIterationObject

    while not done_looping:
        try:
            item = next(iterator)
        except StopIteration:
            done_looping = True
        else:
            # El primer parámetro de la función pasada como argumento ha de ser de tipo LoopIterationObject: el primer
            # valor es el item de la iteración, el segundo un bool que indica si es el primer elemento de la lista y
            # el tercero otro bool que indica si es el último elemento de la lista.
            loop_object = LoopIterationObject(item=item, is_first=item is list_to_loop[0],
                                              is_last=item is list_to_loop[-1])
            return_object = function(loop_object, *args, **kwargs)

    return return_object
