from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.responses import HTMLResponse
from langchain_core.load import dumps, loads
from .services.nlp import load_pdf, split_text, get_answer
from .models import Session, Document
from fastapi import WebSocket
import shutil

app = FastAPI()

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
        const ws = new WebSocket("ws://localhost:8000/ws");

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


@app.get("/chat/{id}")
async def get(id: int):
    new_html = html.replace('document_id": 1', f'document_id": {id}')
    new_html = new_html.replace("ws://localhost:8000/ws", f"ws://localhost:8000/ws/{id}")
    return HTMLResponse(new_html)

@app.websocket("/ws/{id}")
async def websocket_endpoint(websocket: WebSocket, id: str):
    
    await websocket.accept()
    session_context = {}

    # Retrieve document text
    document = None
    with Session() as session:
        document = session.query(Document).filter(Document.id == int(id)).first()
    
    # check if document exists
    if not document:
        await websocket.send_text('Error: Document not found')
        await websocket.close()
        return
    else:
        await websocket.send_text(f'file: {document.filename}')

    try:
        while True:
            data = await websocket.receive_json()
            question = data["question"]

            await websocket.send_text(f"You: {question}")
            
            docs = loads(document.data)
            # Generate answer
            answer = get_answer(docs, question)
            print(answer)
            await websocket.send_text(f"Bot: {answer}")
    except:
        await websocket.close()