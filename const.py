# coding=utf-8
# Descripcion: aquí se declaran variables constantes y otras variables útiles compartidas.

VETU_ID = 254234845

# Constantes de caducidad de los grupos
CADUCIDAD_GRUPO = 7776000  # 3 meses en segundos
REFRESH_RATE_GRUPO = 86400  # 1 día en segundos
MINIMUN_REFRESH_RATE_GRUPO = 2552000  # 1 mes en segundos

# Constantes de caducidad de los usuarios
CADUCIDAD_USER = 31536000  # 1 año en segundos
REFRESH_RATE_USER = 86400  # 1 día en segundos
MINIMUN_REFRESH_RATE_USER = 15768000  # 6 meses en segundos

# Constantes de caducidad de las transacciones
CADUCIDAD_TRANSACTION = 15768000  # 6 meses en segundos
REFRESH_RATE_TRANSACTION = 604800  # 1 semana en segundos
MINIMUN_REFRESH_RATE_TRANSACTION = 7776000  # 3 meses en segundos

# Patrones de expresiones regulares
RE_AMOUNT_COMMENT_PATTERN = r"\d+((\.|,)\d+)? (\w *)+"  # <amount> <comment>

USERS_PER_PAGE_NEW_TRANSACTION = 10

TRANSACTIONS_PER_PAGE_HISTORY = 5


class _Aux:
    # Clase de una sola instancia donde se guardarán variables que sean compartidas entre varios archivos con intención
    # de evitar importaciones circulares.

    def __init__(self):
        self.bot_username = None
        self.bot_id = None
        self.bot = None
        pass


aux = _Aux()
