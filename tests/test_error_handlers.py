import pytest
from unittest.mock import patch, MagicMock
from flask import Flask
import app


class TestErrorHandlers:
    @pytest.fixture
    def client(self):
        app.app.config["TESTING"] = True
        return app.app.test_client()
    
    def test_404_route(self, client):
        # Call a route that doesn't exist
        response = client.get("/this_route_does_not_exist")
        
        # Check that we get a 404
        assert response.status_code == 404
    
    @patch("app.render_template")
    def test_custom_404_handler(self, mock_render, client):
        # Setup custom 404 handler
        @app.app.errorhandler(404)
        def custom_404(error):
            return mock_render("404.html"), 404
        
        # Call a route that doesn't exist
        client.get("/this_route_does_not_exist")
        
        # Check that our handler was called
        mock_render.assert_called_once_with("404.html")