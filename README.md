# PDF Processing and Question-Answering API

This project provides a FastAPI-based application that allows users to upload PDFs, extract text, and perform question-answering via WebSocket. It includes rate limiting for security and efficiency.

## Features

1. **PDF Upload**
   - Upload PDFs via `/upload-pdf/` endpoint.
   - Extracts and splits text for efficient retrieval.

2. **WebSocket Interface**
   - Supports interactive question-answering based on uploaded PDFs via `/ws/{id}/` endpoint.

3. **Rate Limiting**
   - Limits requests for both HTTP and WebSocket endpoints to prevent abuse.

4. **Test Suite**
   - Includes unit tests for upload, WebSocket communication, and rate limiting.

## Project Structure

```
.
├── app/
│   ├── routes.py          # Main application logic
│   ├── models.py          # Database models using SQLAlchemy
│   ├── services/            
│   │   ├── nlp.py         # NLP-related services for text processing and QA
├── tests/
│   ├── test_routes.py     # Unit tests for application endpoints
├── static/
│   ├── uploaded_pdfs/     # Directory to store uploaded PDFs
│   │   ├── # stored pdfs
```

## Requirements

- Python 3.10
- FastAPI
- SQLAlchemy (for database interaction)
- Pytest (for testing)
- Redis (for rate limiting)
- LangChain (for NLP services) 
    - Groq API - large language model
    - Together API - embeddings

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/AllenJonathan/pdf-chat.git
   cd pdf-chat
   ```

2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up Redis:
   - Use a cloud Redis service or set up locally.
   - Update the Redis URL in `routes.py`.

6. Set environment variables:
   Create a `.env` file in the project app/ directory and set your API keys:
     ```env
     GROQ_API_KEY=<your-groq-api-key>
     TOGETHER_API_KEY=<your-together-api-key>
     ```

## Usage

### Start the Server
Run the application:
```bash
uvicorn app.routes:app --reload
```

### Endpoints

#### 1. **Upload PDF**
- **Endpoint:** `/upload-pdf/`
- **Method:** `POST`
- **Request:**
  - Form-data with key `file` and the PDF file.
- **Response:**
  ```json
  {
    "id": <document_id>,
    "filename": <filename>
  }
  ```

#### 2. **WebSocket Chat**
- **Endpoint:** `/ws/{id}`
- **Description:** Interact with a specific document using WebSocket.
- **Example:**
  ```javascript
  const ws = new WebSocket("ws://localhost:8000/ws/1");
  ws.send(JSON.stringify({ question: "What is the content of the PDF?" }));
  ```

#### 3. **Chat UI** (Additionaly UI endpoint for frontend interaction)
- **Endpoint:** `/chat/{id}`
- **Description:** Simple HTML-based chat UI for question-answering.

## Testing

Run the test suite:
```bash
pytest
```

### Tests Included
1. **Upload Endpoint**
   - Valid PDF upload
   - Invalid file type handling

2. **WebSocket Communication**
   - Sending and receiving messages
   - Generating answers for questions

3. **Rate Limiting**
   - Validate rate limit enforcement under normal and overload conditions.

## Dependencies

- **Frameworks and Tools:**
  - FastAPI
  - SQLAlchemy
  - Redis
  - LangChain
- **Testing:**
  - Pytest
  - TestClient (from FastAPI)

## Future Improvements
- Implement support for additional file formats.
- Enhance the user interface for better usability.
- Extend rate-limiting rules for more granular control.
- Add support for more NLP models.

---

Developed with ❤️ using FastAPI and LangChain.

