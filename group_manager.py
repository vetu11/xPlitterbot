# coding=utf-8

import json
import time
from group import Group


class _GroupManager:
    # Clase de una única instancia dedicada a manejar las isntancias de los grupos.

    def __init__(self):
        self.group_dict = {}

        with open("groups.json", encoding="utf-8") as f:
            crude_group_list = json.load(f)

        for crude_group in crude_group_list:
            self.group_dict[crude_group["id"]] = Group(**dict(crude_group))

        #self.check_groups_expiration_date()

    def check_groups_expiration_date(self):
        # Elimina de la lista los grupos cuya fecha de caducidad haya expirado.

        to_be_removed = []

        for group_id in self.group_dict:
            if self.group_dict[group_id].expiration_date < time.time():
                to_be_removed.append(group_id)

        for group_id in to_be_removed:
            self.group_dict.pop(group_id)

    def get_group(self, chat, chat_data):
        # Devuelve la instacia del grupo correspondiente a la instancia de chat pasada.

        if "self" in chat_data:
            chat_data["self"].refresh_expiration_date()
            return chat_data["self"]

        if chat.id in self.group_dict:
            self.group_dict[chat.id].refresh_expiration_date()
            chat_data["self"] = self.group_dict[chat.id]
            return self.group_dict[chat.id]

        new_group = Group(**chat.__dict__)
        self.group_dict[chat.id] = new_group
        chat_data["self"] = new_group
        return new_group

    def get_group_by_id(self, group_id):
        # Devuelve la instnacia del grupo con la id que se ha pasado.

        if group_id in self.group_dict:
            self.group_dict[group_id].refresh_expiration_date()
            return self.group_dict[group_id]
        return None

    def save(self):
        list = []
        for group_id in self.group_dict:
            list.append(self.group_dict[group_id].to_dict())

        with open("groups.json", "w", encoding="utf-8") as f:
            json.dump(list, f, indent=2)

    @staticmethod
    def is_group(instance):
        # Devuelve verdadero la instnacia pasada es un grupo.

        return isinstance(instance, Group)


group_manager = _GroupManager()
