import gettext
import locale

languages = {
    # base es el nombre del fichero mo, locales es el director en donde se encuentra
    "es_ES": gettext.translation('base', 'resources/locales', languages=['es_ES'], fallback=True),
    "en_GB": gettext.translation('base', 'resources/locales', languages=['en_GB'], fallback=True)
}
"""Diccionario con traductores de gettext identificados por el código iso del locale"""


def change_locale(locale_iso: str):
    """Cambia el locale del sistema.
    :param locale_iso: Código Iso del locale al que se quiere cambiar
    """
    locale.setlocale(locale.LC_ALL, locale_iso)


def translate(key: str, locale_iso: str = None):
    """Traduce una clave i18n

    Parameters:
    :param: str:Clave i18n a traducir
    :param: str:Iso del locale al que se quiere traducir

    :return: str:Clave traducida en función del locale actual

   """
    # Locale es una tupla, el primer valor es el código del idioma que es lo que uso en como clave del diccionario
    return languages[locale_iso if locale_iso is not None else locale.getlocale()[0]].gettext(key)
