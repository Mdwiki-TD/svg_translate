"""Unit tests for task routes URL fix."""
from __future__ import annotations

from unittest.mock import Mock, patch

from src.app.app_routes.tasks import routes


def test_start_redirects_to_correct_task_endpoint(monkeypatch):
    """Test that start() redirects to 'tasks.task' not 'tasks.task1'."""
    # Mock the necessary dependencies
    mock_task_store = Mock()
    mock_task_store.find_task_by_normalized_title = Mock(return_value={
        "id": "existing-task-123",
        "status": "Pending"
    })
    
    monkeypatch.setattr(routes, "_task_store", lambda: mock_task_store)
    
    with patch("src.app.app_routes.tasks.routes.request") as mock_request:
        mock_request.method = "POST"
        mock_request.form = {"title": "Test Title"}
        
        with patch("src.app.app_routes.tasks.routes.current_user") as mock_user:
            mock_user.return_value = Mock(username="testuser")
            
            with patch("src.app.app_routes.tasks.routes.flash"):
                with patch("src.app.app_routes.tasks.routes.redirect"):
                    with patch("src.app.app_routes.tasks.routes.url_for") as mock_url_for:
                        mock_url_for.return_value = "/task/existing-task-123"
                        
                        routes.start()
                        
                        # Verify url_for was called with correct endpoint name
                        mock_url_for.assert_called_with(
                            "tasks.task",  # Should be 'task' not 'task1'
                            task_id="existing-task-123",
                            title="Test Title"
                        )


def test_logger_uses_svg_translate_name():
    """Test that the logger uses 'svg_translate' instead of __name__."""
    assert routes.logger.name == "svg_translate"