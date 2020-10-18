# This is a sample Python script.

# Press Mayús+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.


# Press the green button in the gutter to run the script.
from core.util import i18n
from dao.tipoclientedao import TipoClienteDao
from core.exception.exceptionhandler import CustomException
from model.tipocliente import TipoCliente

if __name__ == '__main__':
    i18n.change_locale("es_ES")

    tipocliente = TipoCliente(None, "0003", "Contado")
    tipoclienteDao = TipoClienteDao()

    try:
        tipoclienteDao.insert(tipocliente)
        print(f'Se ha insertado {str(tipocliente)}')
    except CustomException as e:
        print(str(e))

