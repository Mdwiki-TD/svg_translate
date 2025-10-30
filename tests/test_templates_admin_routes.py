"""Unit tests for templates admin routes improvements."""
from __future__ import annotations

from unittest.mock import Mock, patch

from src.app.app_routes.admin.admin_routes import templates


def test_update_template_uses_request_form_type_parameter():
    """Test that _update_template uses request.form.get with type=int parameter."""
    with patch("src.app.app_routes.admin.admin_routes.templates.request") as mock_request:
        # Set up mock to return integer directly
        mock_form = Mock()
        mock_form.get = Mock(side_effect=lambda key, default=None: {
            "id": 42,
            "title": "Test Title",
            "main_file": "test.svg"
        }.get(key, default))
        mock_request.form = mock_form
        
        mock_service = Mock()
        mock_service.update_template = Mock(return_value=Mock(title="Test Title"))
        mock_service_attr = Mock()
        mock_service_attr.template_service = mock_service
        
        with patch("src.app.app_routes.admin.admin_routes.templates.template_service", mock_service):
            with patch("src.app.app_routes.admin.admin_routes.templates.flash"):
                with patch("src.app.app_routes.admin.admin_routes.templates.redirect"):
                    templates._update_template()
        
        # Verify get was called with type parameter for id
        calls = mock_form.get.call_args_list
        id_call = next(call for call in calls if call[0][0] == "id")
        assert id_call[1].get("type") is int
        assert id_call[1].get("default") == 0


def test_update_template_correct_error_message_for_missing_title():
    """Test that _update_template shows correct error message for update (not 'add')."""
    with patch("src.app.app_routes.admin.admin_routes.templates.request") as mock_request:
        mock_form = Mock()
        mock_form.get = Mock(side_effect=lambda key, default=None: {
            "id": 1,
            "title": "",  # Empty title
            "main_file": "test.svg"
        }.get(key, default))
        mock_request.form = mock_form
        
        with patch("src.app.app_routes.admin.admin_routes.templates.flash") as mock_flash:
            with patch("src.app.app_routes.admin.admin_routes.templates.redirect"):
                templates._update_template()
        
        # Verify the correct error message (should say "update" not "add")
        mock_flash.assert_called_once()
        flash_message = mock_flash.call_args[0][0]
        assert "update" in flash_message.lower()
        assert "Title is required to update a template" in flash_message


def test_update_template_missing_id_shows_error():
    """Test that _update_template shows error when template ID is missing."""
    with patch("src.app.app_routes.admin.admin_routes.templates.request") as mock_request:
        mock_form = Mock()
        mock_form.get = Mock(side_effect=lambda key, default=None: {
            "id": 0,  # No ID
            "title": "Test",
            "main_file": "test.svg"
        }.get(key, default))
        mock_request.form = mock_form
        
        with patch("src.app.app_routes.admin.admin_routes.templates.flash") as mock_flash:
            with patch("src.app.app_routes.admin.admin_routes.templates.redirect"):
                templates._update_template()
        
        mock_flash.assert_called_once_with("Template ID is required to update a template.", "danger")


def test_logger_uses_svg_translate_name():
    """Test that the logger uses 'svg_translate' instead of __name__."""
    assert templates.logger.name == "svg_translate"