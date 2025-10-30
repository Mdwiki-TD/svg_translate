"""Unit tests for coordinators exception handling improvements."""
from __future__ import annotations

import logging
from unittest.mock import Mock, patch

from src.app.app_routes.admin.admin_routes import coordinators


def test_add_coordinator_catches_both_lookup_and_value_errors(monkeypatch, caplog):
    """Test that _add_coordinator catches both LookupError and ValueError in single except clause."""
    mock_service = Mock()
    
    # Test with ValueError
    mock_service.add_coordinator = Mock(side_effect=ValueError("Username invalid"))
    monkeypatch.setattr(coordinators, "admin_service", mock_service)
    
    with patch("src.app.app_routes.admin.admin_routes.coordinators.request") as mock_request:
        mock_request.form.get = Mock(return_value="test_user")
        
        with patch("src.app.app_routes.admin.admin_routes.coordinators.flash") as mock_flash:
            with patch("src.app.app_routes.admin.admin_routes.coordinators.redirect"):
                with caplog.at_level(logging.ERROR):
                    coordinators._add_coordinator()
                
                # Verify exception was logged
                assert "Unable to Add coordinator" in caplog.text
                
                # Verify flash was called with the error message
                mock_flash.assert_called_once_with("Username invalid", "warning")
    
    # Test with LookupError
    mock_service.add_coordinator = Mock(side_effect=LookupError("User not found"))
    
    with patch("src.app.app_routes.admin.admin_routes.coordinators.request") as mock_request:
        mock_request.form.get = Mock(return_value="test_user")
        
        with patch("src.app.app_routes.admin.admin_routes.coordinators.flash") as mock_flash:
            with patch("src.app.app_routes.admin.admin_routes.coordinators.redirect"):
                with caplog.at_level(logging.ERROR):
                    coordinators._add_coordinator()
                
                mock_flash.assert_called_once_with("User not found", "warning")


def test_logger_uses_svg_translate_name():
    """Test that the logger uses 'svg_translate' instead of __name__."""
    assert coordinators.logger.name == "svg_translate"