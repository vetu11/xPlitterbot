# coding=utf-8
# Descripción: define la clase grupo.

import time
import const
from user_manager import user_manager
from transaction_manager import transaction_manager


class Group:
    # Clase para cada grupo de Telegram, donde gudardar las transacciones y usuarios.

    def __init__(self, **kwargs):
        self.id = kwargs.get("id")  # ID numerica del grupo, dada por Telegram.
        self.title = kwargs.get("title")
        self.user_list = kwargs.get("user_list", [])  # Lista de los participantes del grupo. Debe contener instantcias de
                                                  # usuarios, si son strings se interpretarán como sus IDs.
        self.transaction_list = kwargs.get("transaction_list", [])  # Lo mismo de arriba pero con trasacciones.
        self.ledger = kwargs.get("ledger", {})  # Suma total de las deudas de cada usuario.
        self.expiration_date = kwargs.get("expiration_date", time.time() + const.CADUCIDAD_GRUPO)  # fecha de caducidad.
        self.lang = kwargs.get("lang", "EN-en")  # Idioma del grupo.

        # Conversión de ids a instancias de los usuarios.
        if self.user_list and isinstance(self.user_list[0], int):
            new_user_list = []
            for user_id in self.user_list:
                new_user_list.append(user_manager.get_user_by_id(user_id))
            self.user_list = new_user_list

        # Conversión de ids a instancias de transacciones.
        if self.transaction_list and isinstance(self.transaction_list[0], str):
            new_transaction_list = []
            for transaction_id in self.transaction_list:
                new_transaction_list.append(transaction_manager.get_transaction_by_id(transaction_id))
            self.transaction_list = new_transaction_list

    def to_dict(self):
        d = dict(self.__dict__)
        d["user_list"] = [int(x.__repr__()) for x in self.user_list]
        d["transaction_list"] = [x.__repr__() for x in self.transaction_list]
        return d

    def refresh_expiration_date(self):
        # Aumenta la fecha de caducidad de un grupo cuando se usa.
        self.expiration_date += const.REFRESH_RATE_GRUPO

        if self.expiration_date < time.time() + const.MINIMUN_REFRESH_RATE_GRUPO:
            self.expiration_date = time.time() + const.MINIMUN_REFRESH_RATE_GRUPO

    def calculate_ledger(self):
        # Calcula el estado actual de la suma de las deudas de cada usuario a partir de la lista de transacciones.

        new_ledger = {}

        for transaction in self.transaction_list:
            if transaction.group_id == self.id:
                if transaction.type == "purchase":
                    n_participants = float(len(transaction.participants))

                    new_ledger[transaction.buyer] = new_ledger.get(transaction.buyer, 0) + transaction.amount
                    for participant in transaction.participants:
                        new_ledger[participant] = new_ledger.get(participant, 0) - transaction.amount / n_participants
                elif transaction.type == "debt":
                    new_ledger[transaction.lender] = new_ledger.get(transaction.lender, 0) + transaction.amount
                    new_ledger[transaction.debtor] = new_ledger.get(transaction.debtor, 0) - transaction.amount
                elif transaction.type == "transfer":
                    new_ledger[transaction.payer] = new_ledger.get(transaction.payer, 0) + transaction.amount
                    new_ledger[transaction.receiver] = new_ledger.get(transaction.receiver, 0) - transaction.amount
            else:
                self.transaction_list.remove(transaction)

        self.ledger = new_ledger

    def calculate_best_movements(self):
        # Crea una lista de trasacciones sugeridas para resolver las deudas del grupo lo más simple posible.
        # @pre: ledger has been recently calculated.

        positive = []  # (amount, user_id)
        negative = []  # (amount, user_id)
        suggested_transfers = []  # (from_id, to_id, amount)

        for user_id in self.ledger:
            if self.ledger[user_id] > 0:
                positive.append((self.ledger[user_id], user_id))
            elif self.ledger[user_id] < 0:
                negative.append((self.ledger[user_id], user_id))

        positive.sort(reverse=True)
        negative.sort()

        while len(positive) and len(negative):
            i = 0

            while True:
                if positive[0][0] >= -negative[i][0]:
                    suggested_transfers.append((negative[i][1], positive[0][1], negative[i][0]))
                    tranfered = negative[i][0]
                    balance = positive[0][0] + tranfered
                    if balance > 0.00:  # It was != 0, but floats are not enough precise sometimes...
                        positive.append((balance, positive[0][1]))
                    positive.pop(0)
                    negative.pop(i)
                    break
                elif i + 1 >= len(negative):
                    amount_to_trasfer = positive[0][0]
                    rest = negative[-1][0] + amount_to_trasfer
                    negative.append((rest, negative[-1][1]))
                    suggested_transfers.append((negative[-1][1], positive[0][1], amount_to_trasfer))
                    positive.pop(0)
                    negative.pop(-2)
                    break
                else:
                    i += 1

            positive.sort(reverse=True)
            negative.sort()

        return suggested_transfers

    def add_transaction(self, transaction):
        # Añade una transacción a la lista del grupo, devuelve True lo ha hecho; si la trnsacción ya estaba False.

        if transaction in self.transaction_list:
            return False
        self.transaction_list.append(transaction)
        return True

    def remove_transaction(self, transaction_id):
        # Elimina de la lista de trnsacciónes la transacción de la ID dada, devuelve True si estaba, False si no.
        # Da error si no se le ha dado una id.

        if not isinstance(transaction_id, str):
            raise TypeError

        for transaction in self.transaction_list:
            if transaction.id == transaction_id:
                self.transaction_list.remove(transaction)
                return True

        return False

    def add_telegram_user(self, telegram_user):
        # Añade unusuario a la lista de participantes del grupo. Se le debe da una instancia de Telegram.

        user = user_manager.get_user(telegram_user)
        if user in self.user_list:
            return user
        self.user_list.append(user)
        return user

    def remove_telegram_user(self, telegram_user):
        user = user_manager.get_user(telegram_user)

        if user in self.user_list:
            self.user_list.remove(user)

    def find_most_expensive_purchase(self):
        """Returns a dict with the comment and amount of the most expensive purchase of the group."""

        most_expensive = None

        for purchase in self.transaction_list:
            if purchase.type == "purchase":
                if most_expensive is None:
                    most_expensive = purchase
                else:
                    if most_expensive.amount < purchase.amount:
                        most_expensive = purchase

        if most_expensive is None:
            return False
        return {"amount": most_expensive.amount, "comment": most_expensive.comment}

    def find_user_in_most_purchases_as_participant(self):
        """Returns the full_name_simple of the user in purchases as participant."""

        pre_ranking = {}

        for transaction in self.transaction_list:
            if transaction.type == "purchase":
                for user_id in transaction.participants:
                    pre_ranking[user_id] = pre_ranking.get(user_id, 0) + 1

        ranking = []

        for user_id in pre_ranking:
            ranking.append((pre_ranking[user_id], user_id))

        ranking.sort()

        if not ranking:
            return False
        return user_manager.get_user_by_id(ranking[-1][1]).full_name_simple

    def find_user_in_most_purchases_as_buyer(self):
        """Returns the full_name_simple of the user in purchases as buyer."""

        pre_ranking = {}

        for transaction in self.transaction_list:
            if transaction.type == "purchase":
                pre_ranking[transaction.buyer] = pre_ranking.get(transaction.buyer, 0) + 1

        ranking = []

        for user_id in pre_ranking:
            ranking.append((pre_ranking[user_id], user_id))

        ranking.sort()

        if not ranking:
            return False
        return user_manager.get_user_by_id(ranking[-1][1]).full_name_simple

    def total_spent(self):
        """Returns the amount spent on all the purchases of the group."""

        amount = 0
        for purchase in self.transaction_list:
            if purchase.type == "purchase":
                amount += purchase.amount

        return amount

    def total_transferred(self):
        """Returns the amount transferred on all the transfers of the group."""

        amount = 0
        for transfer in self.transaction_list:
            if transfer.type == "transfer":
                amount += transfer.amount

        return amount
