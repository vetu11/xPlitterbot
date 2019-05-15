# coding=utf-8
# Archivo: user
# Autor: vetu11
# Fecha última edición: 1/10/2018
# Descripción: Se define la clase User, que contiene las descripciónes minimas por parte de Telegram, y los datos
# adicionales generados por el bot.

import time
import const
from transaction_manager import transaction_manager


class User:
    # Usuario de Telegram.

    def __init__(self, **kwargs):

        self.first_name = kwargs.get("first_name")
        self.last_name = kwargs.get("last_name")
        self.username = kwargs.get("username")
        self.id = kwargs.get("id")
        self.language_code = kwargs.get("language_code", "ES-es")
        self.full_name = kwargs.get("full_name")
        self.full_name_simple = kwargs.get("full_name_simple")
        self.expiration_date = kwargs.get("expiration_date", time.time() + const.CADUCIDAD_USER)
        self.transaction_list = kwargs.get("transaction_list", [])

        assert self.first_name is not None, "Error al crear el usuario: first_name es None"
        assert self.id is not None, "Error al crear el usuario: id es None"

        # Check types
        if not isinstance(self.first_name, str) and isinstance(id, int):
            raise TypeError

        if self.full_name is None:
            self.create_full_name()

        if self.transaction_list and isinstance(self.transaction_list, (str, unicode)):
            new_transaction_list = []
            for transaction_id in self.transaction_list:
                new_transaction_list.append(transaction_manager.get_transaction_by_id(transaction_id))
            self.transaction_list = new_transaction_list

    def __repr__(self):
        return str(self.id)

    def create_full_name(self):
        # crea las variables self.full_name y self.full_name_simple

        assert self.first_name is not None, "self.first_name es None"

        if self.last_name is None:
            self.full_name_simple = self.first_name
        else:
            self.full_name_simple = self.first_name + " " + self.last_name

        if self.username is None:
            self.full_name = self.full_name_simple
        else:
            self.full_name = "[%s](t.me/%s)" % (self.full_name_simple, self.username)

    def refresh_expiration_date(self):
        self.expiration_date += const.REFRESH_RATE_USER

        if self.expiration_date < time.time() + const.MINIMUN_REFRESH_RATE_USER:
            self.expiration_date = time.time() + const.MINIMUN_REFRESH_RATE_USER

    def add_transaction(self, transaction):
        self.transaction_list.append(transaction)

    def remove_transaction(self, transaction_id):
        if not isinstance(transaction_id, str):
            raise TypeError

        for transaction in self.transaction_list:
            if transaction.id == transaction_id:
                self.transaction_list.remove(transaction)
                return True

        return False
