from core.rest.apitools import create_and_run_app
from impl.rest.restcontrollerimpl import TipoClienteRestController, ClienteRestController

if __name__ == "__main__":
    # cargar en resourceutils el fichero db.properties
    # OJO!!! db.properties está ignorado en git. Hay que crear una carpeta resources en la raíz del proyecto con los
    # datos de conexión: host, user, password, database.
    resource_list = ['./resources/db.properties']

    # Lista de pares de valores: primer valor la ruta de la api, segundo valor el controlador de dicha ruta
    controllers = [(TipoClienteRestController, "/TipoCliente"), (ClienteRestController, "/Cliente")]

    # Crear y ejecutar app
    create_and_run_app(api_name="api", controllers=controllers, resource_list=resource_list, debug=True)
