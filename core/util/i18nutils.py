import gettext
import glob
import locale
import pathlib
import subprocess

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


def translate(key: str, locale_iso: str = None, *args):
    """Traduce una clave i18n Parameters:
    :param: str:Clave i18n a traducir
    :param: str:Iso del locale al que se quiere traducir
    :param: args Posibles argumentos para sustituir valores que espera el valor de la clave en el fichero .po.
    Si se pasan argumentos, importante pasar siempre como segundo parámetro el iso del locale,
    o si se quiere usar el de por defecto None, pero pasar algo.
    :return: str:Clave traducida en función del locale actual
    """
    # Primero obtengo el valor de la clave en los ficheros po/mo
    # Locale es una tupla, el primer valor es el código del idioma que es lo que uso en como clave del diccionario
    result = languages[locale_iso if locale_iso is not None else locale.getlocale()[0]].gettext(key)

    # Ahora, si han llegado parámetros para sustituir los placeholders, los sustituyo en el valor obtenido
    if args:
        result = result % args

    return result


def create_mo_files(po_files: str, prefix: str):
    """
    Compila los ficheros .po en .mo.
    :param po_files: Ruta y nombre de ficheros .po a compilar. Ejemplo: 'resources/locales/*/LC_MESSAGES/base.po'.
    :param prefix: Ruta desde la que partimos a buscar los ficheros.
    :return: Ficheros .mo compilados.
    """
    mo_files = []

    for po_path in glob.glob(str(pathlib.Path(prefix) / po_files)):
        mo = pathlib.Path(po_path.replace('.po', '.mo'))
        # Ejecutar subproceso msgfmt, que compila los ficheros .po en .mo.
        # OJO!!! Necesario instalar msgfmt en el OS, sino no funciona
        subprocess.run(['msgfmt', '-o', str(mo), po_path], check=True)
        mo_files.append(str(mo.relative_to(prefix)))

    return mo_files
