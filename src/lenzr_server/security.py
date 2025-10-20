import os
import secrets


def is_logged_in(username: str, password: str) -> bool:
    correct_username = os.environ["LENZR_USERNAME"]
    correct_password = os.environ["LENZR_PASSWORD"]

    is_correct_username = secrets.compare_digest(username, correct_username)
    is_correct_password = secrets.compare_digest(password, correct_password)

    return is_correct_username and is_correct_password
