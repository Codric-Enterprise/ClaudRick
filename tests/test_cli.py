from claudrick.cli import main


def test_main_default(capsys):
    exit_code = main([])
    assert exit_code == 0
    assert capsys.readouterr().out.strip() == "Hello, world!"


def test_main_with_name(capsys):
    exit_code = main(["Rick"])
    assert exit_code == 0
    assert capsys.readouterr().out.strip() == "Hello, Rick!"
