import pytest
import httpx
from vaultgui.server_manager import ServerManager
from unittest.mock import patch, MagicMock

def test_server_manager_init():
    sm = ServerManager()
    assert sm.process is None

@patch("httpx.get")
def test_is_running_true(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"info": {"title": "pwd-vault"}}
    mock_get.return_value = mock_response
    
    sm = ServerManager()
    assert sm.is_running() is True

@patch("httpx.get")
def test_is_running_false(mock_get):
    mock_get.side_effect = httpx.ConnectError("Connection refused")
    
    sm = ServerManager()
    assert sm.is_running() is False
