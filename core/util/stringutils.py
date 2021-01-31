def auto_str(cls):
    """Decorador para generar automáticamente una función to_string a clases."""

    def __str__(self):
        # Iterar por el diccionario de campos de la clase e ir concatenando en un string.
        return '%s(%s)' % (
            type(self).__name__,
            ', '.join('%s=%s' % item for item in vars(self).items())
        )
    cls.__str__ = __str__
    return cls
