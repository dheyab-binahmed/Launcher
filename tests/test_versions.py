from core.updater import is_newer


def test_version_comparison():
    assert is_newer("0.2.0", "0.1.9")
    assert is_newer("b1.0.0-r2", "b1.0.0-r1")
    assert not is_newer("0.1.0", "0.1.0")
