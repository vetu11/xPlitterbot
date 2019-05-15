# coding=utf-8

import time
import const
from uuid import uuid4


class TransactionBase:
    # Clase base para las transacciones.

    def __init__(self, **kwargs):
        self.id = kwargs.get("id", str(uuid4()))
        self.group_id = kwargs.get("group_id")
        self.amount = kwargs.get("amount", 0)
        self.comment = kwargs.get("comment", "")
        self.type = kwargs.get("type") if self.type is None else self.type
        self.expiration_date = kwargs.get("expiration_date", time.time() + const.CADUCIDAD_TRANSACTION)

        if self.type is None or self.group_id is None:
            raise TypeError

    def __repr__(self):
        return self.id

    def set_amount(self, new_amount):
        # Fija la cantidad de monedos de la transacción.

        past = self.amount
        self.amount = new_amount
        return past

    def set_comment(self, new_comment):
        # Fija el comentario de la transacción.

        past = self.comment
        self.comment = new_comment
        return past

    def refresh_expiration_date(self):
        # Aumenta la fecha de caducidad a las transacción cada vez se esta se usa.

        self.expiration_date += const.REFRESH_RATE_USER

        if self.expiration_date < time.time() + const.MINIMUN_REFRESH_RATE_USER:
            self.expiration_date = time.time() + const.MINIMUN_REFRESH_RATE_USER


class Purchase(TransactionBase):
    # Transacción compra, donde habrá un comprador y una lista de participantes entre los que se resptarten los gastos.

    def __init__(self, **kwargs):
        self.type = "purchase"
        TransactionBase.__init__(self, **kwargs)
        self.buyer = kwargs.get("buyer")
        self.participants = kwargs.get("participants", [])

        if self.buyer is None:
            raise TypeError

    def set_buyer(self, id):
        # Fija la id del nuevo comprador y devuelve la id del anterior.

        past = self.buyer
        self.buyer = id
        return past

    def add_remove_paticipant(self, id):
        # Añade o elimina la id que se ha pasado, dependiendo de si está o no en el grupo.

        if id in self.participants:
            self.remove_participant(id)
        else:
            self.add_participant(id)

    def add_participant(self, id):
        # Añade la id del participate al grupo, ¡Sin comprobar si ya está!

        self.participants.append(id)

    def remove_participant(self, id):
        # Elimina la id del participante, sin comprobar si realemten está en la transacción.

        self.participants.remove(id)


class Debt(TransactionBase):
    # Transacción deuda, para anotar deudas entre los integrantes del grupo. Se puede asiganr un solo deudor y
    # acreedor.

    def __init__(self, **kwargs):
        self.type = "debt"
        TransactionBase.__init__(self, **kwargs)
        self.lender = kwargs.get("lender")
        self.debtor = kwargs.get("debtor")

        if self.lender is None or self.debtor is None:
            raise TypeError

    def set_lender(self, id):
        # Fija la id del nuevo prestador y devuelve la del antiguo.

        past = self.lender
        self.lender = id
        return past

    def set_debtor(self, id):
        # Fija la id del nuevo deudor y devuelve la del antiguo.

        past = self.debtor
        self.debtor = id
        return past


class Transfer(TransactionBase):
    # Transacción en la que se anota un traspase de dinero, desde un pagador a un cobrador.

    def __init__(self, **kwargs):
        self.type = "transfer"
        TransactionBase.__init__(self, **kwargs)
        self.payer = kwargs.get("payer")
        self.receiver = kwargs.get("receiver")

        if self.payer is None or self.receiver is None:
            raise TypeError

    def set_payer(self, id):
        # Fija la id del nuevo pagador y devuelve la del antiguo.

        past = self.payer
        self.payer = id
        return past

    def set_receiver(self, id):
        # Fija la id del nuevo acreedor y devuelve la del antiguo.

        past = self.receiver
        self.receiver = id
        return past
