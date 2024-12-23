from fastapi import FastAPI, UploadFile, HTTPException, WebSocket, Depends
from fastapi.responses import HTMLResponse
from langchain_core.load import dumps, loads
from starlette.websockets import WebSocketDisconnect
from .services.nlp import load_pdf, split_text, get_answer
from .models import Document, Session
import shutil
import os
from dotenv import load_dotenv
import getpass
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter, WebSocketRateLimiter
import redis.asyncio as redis
from math import ceil
import sys


app = FastAPI()

port =  os.getenv("PORT")
if not port:
    port = '8000'

@app.on_event("startup")
async def startup():
    
    redis_connection = redis.from_url("redis://default:jA2tUyt3zU55CArqB8GupKs2WeWdSutz@redis-12000.c62.us-east-1-4.ec2.redns.redis-cloud.com:12000", encoding="utf-8", decode_responses=True)
    await FastAPILimiter.init(redis_connection)

    BASEDIR = os.path.abspath(os.path.dirname(__file__))
    load_dotenv(os.path.join(BASEDIR, '.env'))

    if not os.getenv("GROQ_API_KEY"):
        os.environ['GROQ_API_KEY'] = getpass.getpass("Enter your Groq API key: ")
    if not os.getenv("TOGETHER_API_KEY"):
        os.environ['TOGETHER_API_KEY'] = getpass.getpass("Enter your Together API key: ")


@app.post("/upload-pdf/")
async def upload_pdf(file: UploadFile):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a PDF.")

    # Save file to local storage
    file_path = f"static/uploaded_pdfs/{file.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    print("PDF saved")

    # Extract text and save metadata
    pages = load_pdf(file_path)
    docs = split_text(pages)
    docs = dumps(docs)
    print(docs)

    with Session() as db:
        document = Document(filename=file.filename, data=docs)
        db.add(document)
        db.commit()
        db.refresh(document)
    return {"id": document.id, "filename": document.filename}


html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WebSocket Chat</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            display: flex;
            flex-direction: column;
            align-items: center;
            background-color: #f4f4f9;
            color: #333;
        }

        h1 {
            margin-top: 20px;
            color: #444;
        }

        form {
            margin: 20px 0;
            display: flex;
        }

        input[type="text"] {
            width: 300px;
            padding: 10px;
            border: 1px solid #ccc;
            border-radius: 4px;
            margin-right: 10px;
        }

        button {
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            background-color: #5cb85c;
            color: white;
            font-size: 16px;
            cursor: pointer;
        }

        button:hover {
            background-color: #4cae4c;
        }

        ul {
            list-style: none;
            padding: 0;
            width: 80%;
            max-width: 600px;
            margin: 0 auto;
        }

        li {
            background-color: #fff;
            padding: 10px;
            margin: 10px 0;
            border: 1px solid #ddd;
            border-radius: 4px;
            word-wrap: break-word;
        }
    </style>
</head>
<body>
    <h1>WebSocket Chat</h1>
    <form action="" onsubmit="sendMessage(event)">
        <input type="text" id="messageText" placeholder="Type your question..." autocomplete="off" />
        <button type="submit">Send</button>
    </form>
    <ul id="messages"></ul>
    <script>
        const ws = new WebSocket("ws://localhost:port/ws");

        ws.onmessage = function (event) {
            const messages = document.getElementById("messages");
            const message = document.createElement("li");
            const content = document.createTextNode(event.data);
            message.appendChild(content);
            messages.appendChild(message);
        };

        function sendMessage(event) {
            event.preventDefault(); // Prevent default form submission
            const input = document.getElementById("messageText");
            const message = {
                document_id: 1, // Replace with actual document ID
                question: input.value,
            };
            ws.send(JSON.stringify(message));
            input.value = ""; // Clear input field after sending
        }
    </script>
</body>
</html>

"""


@app.get("/chat/{id}", dependencies=[Depends(RateLimiter(times=8, seconds=10))])
async def get(id: int):
    with Session() as session:
        print(session.query(Document).all())
    new_html = html.replace('document_id": 1', f'document_id": {id}')
    new_html = new_html.replace("ws://localhost:port/ws", f"ws://localhost/ws/{id}")
    print(html)
    return HTMLResponse(new_html)


@app.websocket("/ws/{id}")
async def websocket_endpoint(websocket: WebSocket, id: str):
    
    await websocket.accept()
    session_context = {}

    # Retrieve document text
    document = None
    with Session() as session:
        print(session.query(Document).all())
        document = session.query(Document).filter(Document.id == int(id)).first()
    
    # check if document exists
    if not document:
        await websocket.send_text('Error: Document not found')
        await websocket.close()
        return
    else:
        await websocket.send_text(f'file: {document.filename}')
    
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Message text was: {data}")
    
    ratelimit = WebSocketRateLimiter(times=2, seconds=60)

    try: 
        while True:
            try:
                data = await websocket.receive_json()
                await ratelimit(websocket)
                question = data["question"]
                await websocket.send_text(f"You: {question}")
                docs = loads(document.data)

                # Generate answer
                answer = get_answer(docs, question)
                await websocket.send_text(f"Bot: {answer}")
            except WebSocketDisconnect as e:
                print("web socket disconnected")
                break
            except HTTPException as e:
                print(e)
                await websocket.send_text(str(e))
            except Exception as e:
                print(f"Error processing request: {e}")
                await websocket.send_text(f"Error: {str(e)}")
                await websocket.close()
    except Exception as e:
        print(f"Connection error: {e}")
    finally:
        await websocket.close()
            