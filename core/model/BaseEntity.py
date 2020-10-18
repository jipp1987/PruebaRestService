class BaseEntity:
    """Entidad base de la que han de extender todos los objetos persistidos en la base de datos."""

    def __init__(self, idfieldname: str = "id"):
        """
        Constructor
        :param idfieldname: Nombre del campo que contiene el id. Por defecto es "id".
        """
        super().__init__()
        self.idfieldname = idfieldname

    def get_field_names_as_str(self):
        """
        Devuelve una cadena con los nombres de los campos separados por comas
        :return: Una cadena de los campos de la entidad cuyo primer valor será el campo del id
        """
        cadena = self.idfieldname
        # Recorrer los nombres de los campos del objeto e ir concatenándolos separados por comas
        for key in self.__dict__.keys():
            # Descartar el campo que almacena el nombre del campo "id"
            if str(key) != "idfieldname" and str(key) != self.idfieldname:
                cadena = cadena + ", " + str(key)

        return cadena

    def get_field_values_as_str(self, is_id_included: bool = False):
        """
        Devuelve una cadena con los valores de los campos de la entidad encadenados por comas :param is_id_included:
        Si True, empieza por el valor del campo id; si False, empieza con "null". False por defecto. :return: str
        """
        # Si 'is_id_included', incluyo el valor del campo id, sino pongo null. Útil pasarlo como False para inserts
        cadena = getattr(self, self.idfieldname) if is_id_included else "null"
        # Recorrer el resto de campos e ir encadenando su valor
        for key in self.__dict__.keys():
            # Descartar el campo que almacena el nombre del campo "id"
            if str(key) != "idfieldname" and str(key) != self.idfieldname:
                cadena = cadena + ", '" + str(getattr(self, str(key))) + "'"

        return cadena
