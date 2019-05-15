# coding=utf-8

import json
import time
from user import User


class _UserManager:

    def __init__(self):
        self.user_dict = {}

        with open("users.json", encoding="utf-8") as f:
            crude_user_dict = json.load(f)

        for crude_user in crude_user_dict:
            self.user_dict[crude_user["id"]] = User(**crude_user)

        self.check_users_expiration_date()

    def check_users_expiration_date(self):
        for user_id in self.user_dict:
            if self.user_dict[user_id].expiration_date < time.time():
                self.user_dict.pop(user_id)
    
    def get_user(self, user, user_data=None):

        if user_data is not None and "self" in user_data:
            user_data["self"].refresh_expiration_date()
            return user_data["self"]

        if user.id in self.user_dict:
            self.user_dict[user.id].refresh_expiration_date()
            if user_data is not None:
                user_data["self"] = self.user_dict[user.id]
            return self.user_dict[user.id]

        new_group = User(**user.__dict__)
        self.user_dict[user.id] = new_group
        user_data["self"] = new_group
        return new_group

    def get_user_by_id(self, user_id):
        if user_id in self.user_dict:
            self.user_dict[user_id].refresh_expiration_date()
            return self.user_dict[user_id]
        return None

    def user_exists(self, user_id):
        if self.get_user_by_id(user_id) is None:
            return False
        return True

    def save(self):
        list = []
        for user_id in self.user_dict:
            list.append(self.user_dict[user_id].__dict__)

        with open("users.json", "w", encoding="utf-8") as f:
            json.dump(list, f)

    @staticmethod
    def is_user(instance):
        return isinstance(instance, User)


user_manager = _UserManager()
