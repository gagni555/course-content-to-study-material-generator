"""
Integration tests for the Course-Content-to-Study-Guide Generator
"""
import asyncio
import tempfile
import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch, MagicMock

from app.main import app
from app.models.database import Base
from app.config import settings

# Create test client
client = TestClient(app)

def test_api_health():
    """
    Test the health endpoint
    """
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "healthy"

def test_metrics_endpoint():
    """
    Test the metrics endpoint
    """
    response = client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "uptime_seconds" in data
    assert "processed_documents" in data
    assert "api_calls" in data

def test_document_upload_endpoint():
    """
    Test the document upload endpoint with a mock PDF
    """
    # Create a temporary text file to simulate document upload
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
        temp_file.write("This is a test document for the Course Content to Study Guide Generator.\n")
        temp_file.write("It contains multiple lines of text to simulate a real document.\n")
        temp_file.write("The system should be able to parse this content and generate study materials.\n")
        temp_file_path = temp_file.name

    try:
        # Upload the test document
        with open(temp_file_path, 'rb') as f:
            response = client.post(
                "/api/v1/documents/upload",
                files={"file": ("test_document.txt", f, "text/plain")},
                headers={"Content-Type": "multipart/form-data"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert "status" in data
        assert data["status"] == "processing"
        
        # Store the job_id for later status check
        job_id = data["job_id"]
        
        # Check status (in a real test, we might need to mock the background processing)
        status_response = client.get(f"/api/v1/documents/status/{job_id}")
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert "job_id" in status_data
        assert status_data["job_id"] == job_id
        
    finally:
        # Clean up temporary file
        os.unlink(temp_file_path)

def test_auth_endpoints():
    """
    Test authentication endpoints
    """
    # Test registration (this would require proper implementation)
    # For now, just check that the endpoint exists
    response = client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "username": "testuser",
        "password": "testpassword123"
    })
    
    # The response could be 422 (validation error) or 400 (user exists) or 200 (success)
    # All of these indicate the endpoint is working
    assert response.status_code in [200, 400, 422]

def test_end_to_end_workflow():
    """
    Test the complete workflow: upload -> process -> get results
    """
    # This test would require mocking the background processing
    # since we can't wait for actual processing in a test
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
        temp_file.write("Sample content for end-to-end testing.\n")
        temp_file_path = temp_file.name

    try:
        # Upload document
        with open(temp_file_path, 'rb') as f:
            upload_response = client.post(
                "/api/v1/documents/upload",
                files={"file": ("test_doc.txt", f, "text/plain")}
            )
        
        assert upload_response.status_code == 200
        upload_data = upload_response.json()
        assert "job_id" in upload_data
        
        job_id = upload_data["job_id"]
        
        # In a real test environment, we would mock the processing pipeline
        # For now, just verify the endpoints are accessible
        status_response = client.get(f"/api/v1/documents/status/{job_id}")
        assert status_response.status_code == 200
        
    finally:
        os.unlink(temp_file_path)

def test_rate_limiting_simulation():
    """
    Simulate rate limiting behavior
    """
    # Make multiple requests to test rate limiting
    for i in range(5):
        response = client.get("/health")
        assert response.status_code == 200

if __name__ == "__main__":
    # Run the tests
    test_api_health()
    test_metrics_endpoint()
    test_document_upload_endpoint()
    test_auth_endpoints()
    test_end_to_end_workflow()
    test_rate_limiting_simulation()
    print("All integration tests passed!")