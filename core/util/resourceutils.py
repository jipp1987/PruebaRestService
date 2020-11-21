from typing import List

from jproperties import Properties

configs = Properties()
"""Objeto Properties que almacenará los recursos externos de la aplicación."""


def load_resource_files(resource_list: List[str]):
    """
    Carga un fichero de recursos en atributo configs del módulo.
    :param resource_list: Lista de rutas de los ficheros de recursos.
    :return: Nada.
    """
    # Recorro la lista de ficheros y los añado.
    if resource_list:
        for path_to_file in resource_list:
            with open(path_to_file, 'rb') as config_file:
                configs.load(config_file)


# Con esto se pueden cargar varios ficheros properties
# with open('a', 'w') as a and open('b', 'w') as b:


def get_data_from_resource(key: str):
    """
    Devuelve una clave de un fichero de propiedades cargado en el objeto Properties. :param key: :return: str
    Devuelve el valor del fichero properties requerido. Si no existe, devuelve la misma clave pasada como parámetro
    pero con un prefijo/sufijo "???"
    """
    return configs.get(key).data if configs.get(key) is not None else "???_" + key + "_???"
