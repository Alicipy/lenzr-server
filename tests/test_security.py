from lenzr_server.security import is_logged_in


def test_is_logged_in_correct_credentials():
    assert is_logged_in("test_user", "test_pass") is True


def test_is_logged_in_incorrect_username():
    assert is_logged_in("wrong_user", "test_pass") is False


def test_is_logged_in_incorrect_password():
    assert is_logged_in("test_user", "wrong_pass") is False


def test_is_logged_in_incorrect_credentials():
    assert is_logged_in("wrong_user", "wrong_pass") is False
