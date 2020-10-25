from flask import Flask, request

# Defino la app de Flask a partir del nombre del este módulo. Es la representación de la aplicación web.
from core.exception.exceptionhandler import CustomException
from core.service.service import ServiceFactory
from model.tipocliente import TipoCliente
from service.tipoclienteservice import TipoClienteService

app = Flask(__name__)


# Esto es la ruta del servicio web dentro del servidor en que se haya desplegado
@app.route("/insert_tipo_cliente", methods=['POST'])
def insert_tipo_cliente():
    """
    Rest service para insertar nuevos tipos de cliente.
    :return: Cadena con mensaje formateado para devolver al solicitante.
    """
    # Obtengo datos json de la petición
    req_data = request.get_json()
    codigo = req_data['codigo']
    descripcion = req_data['descripcion']

    try:
        # Inserto el tipo de cliente
        tipo_cliente = TipoCliente(None, codigo, descripcion)
        tipo_cliente_service = ServiceFactory.get_service(TipoClienteService)
        tipo_cliente_service.insert(tipo_cliente)
        return '''<h1>Se ha insertado: {}</h1>'''.format(str(tipo_cliente))
    except CustomException as e:
        return f'Se ha producido un error insertando el registro: {str(e)}'


if __name__ == "__main__":
    # Con esta línea arranco la aplicación, y le activo el modo debug para visualizar errores en la propia web
    app.run(debug=True, port=5000)

