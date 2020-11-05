from core.rest.apitools import create_app
from rest.restcontroller import TipoClienteRestController

if __name__ == "__main__":
    # Lista de pares de valores: primero valor la ruta de la api, segundo valor el controlador de dicha ruta
    pairs = [(TipoClienteRestController, "/TipoCliente")]

    app = create_app("api", pairs)
    app.run(debug=True)

