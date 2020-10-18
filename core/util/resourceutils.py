from jproperties import Properties

configs = Properties()
"""Objeto Properties que almacenará los recursos externos de la aplicación."""

# Cargar fichero de propiedades en objeto Properties
with open('resources/db.properties', 'rb') as config_file:
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
