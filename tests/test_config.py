from vaultgui import config

def test_config_values():
    assert config.HOST == "127.0.0.1"
    assert config.PORT == 8000
    assert "pwd-vault" in config.BACKEND_DIR
    assert config.AUTO_LOCK_TIMEOUT == 300
