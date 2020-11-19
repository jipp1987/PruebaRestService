from core.rest.apitools import create_app
from impl.rest.restcontrollerimpl import TipoClienteRestController, ClienteRestController

if __name__ == "__main__":
    # Lista de pares de valores: primero valor la ruta de la api, segundo valor el controlador de dicha ruta
    pairs = [(TipoClienteRestController, "/TipoCliente")]
    pairs = [(ClienteRestController, "/Cliente")]

    app = create_app("api", pairs)
    # Multihilo. Pero al ser un servidor para debug, es posible que sólo haya un hilo en ejecución.
    app.run(debug=True, threaded=True)

