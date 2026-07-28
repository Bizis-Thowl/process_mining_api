

from langchain_text_splitters import json


class UserManager():

    def __init__(self):
        with open("database.json", "r") as f:
            self.user_db = json.load(f)

    def get_user_db(self):
        return self.user_db

    def update_user_db(self, user_db):
        self.user_db = user_db
        with open("database.json", "w") as f:
            json.dump(self.user_db, f, indent=4)