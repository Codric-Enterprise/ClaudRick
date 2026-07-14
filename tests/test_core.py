from claudrick.core import greet


def test_greet_default():
    assert greet() == "Hello, world!"


def test_greet_name():
    assert greet("Rick") == "Hello, Rick!"
