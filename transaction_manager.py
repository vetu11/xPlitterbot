# coding=utf-8

import json
import time
from transaction import TransactionBase, Purchase, Debt, Transfer


class _TransactionManager:
    # Clase de una sona instancia que manejará y servirá las transacciónes.

    def __init__(self):
        self.transaction_dict = {}

        with open("transactions.json", encoding="utf-8") as f:
            crude_transaction_list = json.load(f)

        for crude_transaction in crude_transaction_list:
            self.transaction_dict[crude_transaction["id"]] \
                = self._create_transaction(crude_transaction["type"], **crude_transaction)

        self.check_transactions_expiration_date()

    @staticmethod
    def _create_transaction(transaction_type, **kwargs):
        # Crea una trasacción y la devuelve

        if transaction_type == "purchase":
            kwargs.update({"type": "purchase"})
            return Purchase(**kwargs)
        elif transaction_type == "debt":
            kwargs.update({"type": "debt"})
            return Debt(**kwargs)
        elif transaction_type == "transfer":
            kwargs.update({"type": "transfer"})
            return Transfer(**kwargs)
        else:
            return None

    def check_transactions_expiration_date(self):
        # Comprueba la fecha de caducidad de las transacciónes, y elimina las que estén caducadas.

        for transaction_id in self.transaction_dict:
            if self.transaction_dict[transaction_id].expiration_date < time.time():
                self.transaction_dict.pop(transaction_id)

    def get_transaction_by_id(self, transaction_id):
        # Devuelve la transacción con la id especificada.

        if transaction_id in self.transaction_dict:
            self.transaction_dict[transaction_id].refresh_expiration_date()
            return self.transaction_dict[transaction_id]
        return None

    def add_transaction(self, transaction_type, **kwargs):
        # Añade la transacción a la lista.

        new_transaction = self._create_transaction(transaction_type, **kwargs)
        self.transaction_dict[new_transaction.id] = new_transaction
        return new_transaction

    # Permanently removes the transaction from the list.
    def remove_transaction(self, transaction_id):
        self.transaction_dict.pop(transaction_id)

    def save(self):
        list = []
        for transaction_id in self.transaction_dict:
            list.append(self.transaction_dict[transaction_id].to_dict())

        with open("transactions.json", "w", encoding="utf-8") as f:
            json.dump(list, f, indent=2)

    @staticmethod
    def is_transaction(instance):
        # Comprueba si la instancia que se la ha pasado es una instancia de transacción.

        return isinstance(instance, TransactionBase)


transaction_manager = _TransactionManager()
