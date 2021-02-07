import bcrypt

_bcrypt_salt: bytes = bcrypt.gensalt()
"""Salt de bcrypt para primera parte del hash de passwords."""


def hash_password_using_bcrypt(passwd: str) -> bytes:
    """
    Crea un bcrypt hash para un password.
    :param passwd:
    :return: bytes
    """
    # gensalt genera un salt, que es la primera parte del hash.
    return bcrypt.hashpw(passwd.encode(), _bcrypt_salt)


def check_password_using_bcrypt(passwd: str, hashed: bytes) -> bool:
    """
    Comprueba si un password equivale a un hash usando bcrypt.
    :param passwd:
    :param hashed:
    :return: bool
    """
    return bcrypt.checkpw(passwd.encode(), hashed)
