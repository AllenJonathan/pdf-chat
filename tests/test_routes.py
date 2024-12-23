
import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException, status
from app.routes import app
import os
from time import sleep

test_client = TestClient(app)

# Constants
TEST_FILE_PATH = "test_files/dummy.pdf"
INVALID_FILE_PATH = "test_files/dummy.txt"
UPLOAD_ENDPOINT = "/upload-pdf/"
WEBSOCKET_ENDPOINT = "/ws/"


def test_upload_valid_pdf():
    """Test uploading a valid PDF."""
    test_file = TEST_FILE_PATH
    print("Uploading file:", test_file)
    with open(test_file, "rb") as f:
        response = test_client.post(UPLOAD_ENDPOINT, files={"file": (os.path.basename(test_file), f, "application/pdf")})
    
    assert response.status_code == 200
    assert "id" in response.json()
    assert "filename" in response.json()

def test_upload_invalid_file():
    invalid_file = INVALID_FILE_PATH
    """Test uploading an invalid file type."""
    with open(invalid_file, "rb") as f:
        response = test_client.post(UPLOAD_ENDPOINT, files={"file": (os.path.basename(invalid_file), f, "text/plain")})
    
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid file type. Please upload a PDF."

def test_websocket_question_answer():
    
    """Test WebSocket question-answering functionality."""
    with open(TEST_FILE_PATH, "rb") as f:
        upload_response = test_client.post(UPLOAD_ENDPOINT, files={"file": (os.path.basename(TEST_FILE_PATH), f, "application/pdf")})
    
    document_id = upload_response.json()["id"]

    with TestClient(app) as tc:
        with tc.websocket_connect(f"{WEBSOCKET_ENDPOINT}{document_id}") as websocket: 
            data = websocket.receive_text()
            assert data.startswith("file:")
            
            # Test sending a question
            question_data = {"document_id": document_id, "question": "What is the content of the PDF?"}
            websocket.send_json(question_data)

            client_input = websocket.receive_text()
            bot_output = websocket.receive_text()
            print("OUTPUT GOD")
            assert "You: What is the content of the PDF?" in client_input
            assert "Bot:" in bot_output

            # question 2 - follow up questions
            question_data = {"document_id": document_id, "question": "What is the last word?"}
            websocket.send_json(question_data)

            client_input = websocket.receive_text()
            bot_output = websocket.receive_text()
        
            assert "You: What is the last word?" in client_input
            assert "Bot:" in bot_output

def test_rate_limiting_overload():
    """Test the rate limiting for WebSocket and upload endpoints."""
    with open(TEST_FILE_PATH, "rb") as f:
        upload_response = test_client.post(UPLOAD_ENDPOINT, files={"file": (os.path.basename(TEST_FILE_PATH), f, "application/pdf")})
    
    document_id = upload_response.json()["id"]

    with TestClient(app) as tc:
        with tc.websocket_connect(f"{WEBSOCKET_ENDPOINT}{document_id}") as websocket:
            data = websocket.receive_text()
            assert data.startswith("file:")

            for _ in range(2):
                question_data = {"document_id": document_id, "question": "Rate limit test."}
                websocket.send_json(question_data)
                response = websocket.receive_text()
                response = websocket.receive_text()
                print(_,response)
                assert response.startswith("You:") or response.startswith("Bot:")
            
            # Exceed the rate limit
            for _ in range(2):  # Assuming the limit is 2 requests per 60 seconds
                question_data = {"document_id": document_id, "question": "Exceed limit."}
                websocket.send_json(question_data) 
            
                rate_limit_response = websocket.receive_text()
                assert "429: Too Many Requests" in rate_limit_response

def test_rate_limiting_normal_load():
    """Test the rate limiting for WebSocket and upload endpoints."""
    with open(TEST_FILE_PATH, "rb") as f:
        upload_response = test_client.post(UPLOAD_ENDPOINT, files={"file": (os.path.basename(TEST_FILE_PATH), f, "application/pdf")})

    # assert upload_response.status_code == 200
    document_id = upload_response.json()["id"]

    with TestClient(app) as tc:
        with tc.websocket_connect(f"{WEBSOCKET_ENDPOINT}{document_id}") as websocket:
            data = websocket.receive_text()
            assert data.startswith("file:")

            for _ in range(2):
                question_data = {"document_id": document_id, "question": "Rate limit test."}
                websocket.send_json(question_data)
                client = websocket.receive_text()
                bot = websocket.receive_text()
                
                assert client.startswith("You:") 
                assert bot.startswith("Bot:")
