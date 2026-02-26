"""
Unit tests for LOGx dashboard
"""

import pytest


class TestIndexRoute:
    """Tests for the index route"""

    def test_index_get(self, client):
        """Test GET request to index page"""
        response = client.get('/')
        assert response.status_code == 200
        assert b'<!DOCTYPE html>' in response.data or b'<html' in response.data

    def test_index_post_empty_input(self, client):
        """Test POST with empty log input"""
        response = client.post('/', data={'log_input': ''})
        # Should either redirect or show error message
        assert response.status_code in [200, 302]

    def test_index_post_valid_input(self, client):
        """Test POST with valid log input"""
        response = client.post('/', data={
            'log_input': 'ERROR: Database connection failed'
        })
        # Should process and return analysis
        assert response.status_code == 200


class TestReportRoute:
    """Tests for the report route"""

    def test_report_get(self, client):
        """Test GET request to report page"""
        response = client.get('/report')
        assert response.status_code == 200

    def test_report_post_empty_input(self, client):
        """Test POST with empty logs"""
        response = client.post('/report', data={'log_input': ''})
        assert response.status_code in [200, 302]

    def test_report_post_valid_input(self, client):
        """Test POST with valid multiple logs"""
        logs = """
        [ERROR] Connection timeout at 10:23:45
        [ERROR] Retried 3 times, giving up
        [WARN] Service memory at 85%
        """
        response = client.post('/report', data={'log_input': logs})
        assert response.status_code == 200


class TestVisualizationRoute:
    """Tests for the visualization route"""

    def test_visual_get(self, client):
        """Test GET request to visualization page"""
        response = client.get('/visual')
        assert response.status_code == 200

    def test_visual_post_no_file(self, client):
        """Test POST without file upload"""
        response = client.post('/visual')
        assert response.status_code == 200


class TestAboutRoute:
    """Tests for the about route"""

    def test_about_page(self, client):
        """Test about page loads"""
        response = client.get('/about')
        assert response.status_code == 200


class TestPDFExport:
    """Tests for PDF export functionality"""

    def test_report_pdf_no_report(self, client):
        """Test PDF export without generating report"""
        response = client.get('/report/pdf')
        # Should work but return empty/template report
        assert response.status_code == 200
        assert response.content_type == 'application/pdf'


class TestErrorHandling:
    """Tests for error handling"""

    def test_nonexistent_route(self, client):
        """Test 404 error"""
        response = client.get('/nonexistent')
        assert response.status_code == 404

    def test_method_not_allowed(self, client):
        """Test method not allowed"""
        response = client.delete('/')
        assert response.status_code == 405


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
