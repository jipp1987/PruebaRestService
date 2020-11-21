from core.rest.apitools import create_and_run_app
from core.util import resourceutils
from impl.rest.restcontrollerimpl import TipoClienteRestController, ClienteRestController

if __name__ == "__main__":
    # Establecer valores para BaseDao: datos de conexión con la base de datos y pool de conexiones.
    db_config = {
        'host': resourceutils.get_data_from_resource("host"),
        'user': resourceutils.get_data_from_resource("username"),
        'password': resourceutils.get_data_from_resource("password"),
        'database': resourceutils.get_data_from_resource("dbname")
    }

    # Lista de pares de valores: primero valor la ruta de la api, segundo valor el controlador de dicha ruta
    controllers = [(TipoClienteRestController, "/TipoCliente"), (ClienteRestController, "/Cliente")]
    create_and_run_app(api_name="api", controllers=controllers, db_config=db_config, debug=True)