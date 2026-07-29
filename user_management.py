import json
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.param_functions import Form
from typing import Annotated
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

class NewPasswordForm(OAuth2PasswordRequestForm):
    def __init__(self,
            grant_type: Annotated[
                str,
                Form(pattern="^password$")
            ],
            username: Annotated[
                str,
                Form()
            ],
            password: Annotated[
                str,
                Form(json_schema_extra={"format": "password"})
            ],
            new_password: Annotated[
                str,
                Form(json_schema_extra={"format": "password"})
            ],
            new_password_repeat: Annotated[
                str,
                Form(json_schema_extra={"format": "password"})
            ]):
        super().__init__(
            grant_type=grant_type, username=username, password=password
        )
        self.new_password = new_password
        self.new_password_repeat = new_password_repeat