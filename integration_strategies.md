# Voice Agent Integration with Flask + FastAPI Portal

## Integration Approaches

### 1. **Microservice Integration** (Recommended)
Deploy your voice agent as a separate microservice that communicates with the main portal.

```python
# main_portal/services/voice_agent_client.py
import httpx
import asyncio
from typing import Optional, Dict, Any

class VoiceAgentClient:
    def __init__(self, base_url: str = "http://voice-agent-service:8001"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def upload_document(self, file_data: bytes, filename: str) -> Dict[str, Any]:
        """Upload document to voice agent service"""
        files = {"file": (filename, file_data)}
        response = await self.client.post(f"{self.base_url}/api/upload/", files=files)
        return response.json()
    
    async def process_message(self, document_id: int, message: str, agent_config: Dict) -> Dict[str, Any]:
        """Send message to voice agent for processing"""
        payload = {
            "document_id": document_id,
            "message": message,
            "agent_config": agent_config
        }
        response = await self.client.post(f"{self.base_url}/api/process-message/", json=payload)
        return response.json()
    
    async def generate_podcast(self, document_id: int, agents: list) -> Dict[str, Any]:
        """Generate podcast from document"""
        payload = {"document_id": document_id, "agents": agents}
        response = await self.client.post(f"{self.base_url}/api/podcast/generate/", json=payload)
        return response.json()

# main_portal/api/voice_routes.py (FastAPI)
from fastapi import APIRouter, UploadFile, File, HTTPException
from .services.voice_agent_client import VoiceAgentClient

router = APIRouter(prefix="/voice-agent", tags=["voice-agent"])
voice_client = VoiceAgentClient()

@router.post("/upload-document/")
async def upload_document(file: UploadFile = File(...)):
    try:
        file_data = await file.read()
        result = await voice_client.upload_document(file_data, file.filename)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat/")
async def chat_with_document(
    document_id: int,
    message: str,
    agent_type: str = "analytical"
):
    try:
        agent_config = {"type": agent_type, "model": "llama3"}
        result = await voice_client.process_message(document_id, message, agent_config)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### 2. **Direct Integration** (If you want everything in one codebase)
Convert your Django components to Flask/FastAPI modules.

```python
# voice_agent_service/app.py (FastAPI)
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .services import DocumentService, LLMService, VoiceService
from .models import Document, ChatMessage
import asyncio

app = FastAPI(title="Voice Agent Service")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
doc_service = DocumentService()
llm_service = LLMService()
voice_service = VoiceService()

@app.post("/api/upload/")
async def upload_document(file: UploadFile = File(...)):
    """Upload and process document"""
    try:
        # Save file to local filesystem
        file_path = await doc_service.save_file(file)
        
        # Extract text content
        processed_text = await doc_service.extract_text(file_path)
        
        # Create document record
        document = Document(
            filename=file.filename,
            file_path=file_path,
            processed_text=processed_text,
            content_type=file.content_type
        )
        
        doc_id = await doc_service.save_document(document)
        
        return {
            "document_id": doc_id,
            "filename": file.filename,
            "status": "processed",
            "text_length": len(processed_text)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/process-message/")
async def process_message(request: dict):
    """Process chat message with document context"""
    try:
        document_id = request["document_id"]
        message = request["message"]
        agent_config = request.get("agent_config", {})
        
        # Get document context
        document = await doc_service.get_document(document_id)
        
        # Generate response using LLM
        response = await llm_service.generate_response(
            message=message,
            context=document.processed_text,
            agent_config=agent_config
        )
        
        # Save chat message
        chat_message = ChatMessage(
            document_id=document_id,
            message=message,
            response=response,
            agent_id=agent_config.get("type", "default")
        )
        
        await doc_service.save_chat_message(chat_message)
        
        return {
            "response": response,
            "agent_type": agent_config.get("type", "default"),
            "timestamp": chat_message.timestamp
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# voice_agent_service/services/document_service.py
import aiofiles
import os
from pathlib import Path
from typing import Optional
import PyPDF2
import docx
import json
from datetime import datetime

class DocumentService:
    def __init__(self, upload_dir: str = "uploads"):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(exist_ok=True)
        self.metadata_dir = self.upload_dir / "metadata"
        self.metadata_dir.mkdir(exist_ok=True)
    
    async def save_file(self, file: UploadFile) -> str:
        """Save uploaded file to filesystem"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{file.filename}"
        file_path = self.upload_dir / filename
        
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        return str(file_path)
    
    async def extract_text(self, file_path: str) -> str:
        """Extract text from various file formats"""
        file_path = Path(file_path)
        
        if file_path.suffix.lower() == '.pdf':
            return await self._extract_pdf_text(file_path)
        elif file_path.suffix.lower() in ['.docx', '.doc']:
            return await self._extract_docx_text(file_path)
        elif file_path.suffix.lower() == '.txt':
            return await self._extract_txt_text(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")
    
    async def _extract_pdf_text(self, file_path: Path) -> str:
        """Extract text from PDF"""
        text = ""
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text()
        return text
    
    async def _extract_docx_text(self, file_path: Path) -> str:
        """Extract text from DOCX"""
        doc = docx.Document(file_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text
    
    async def _extract_txt_text(self, file_path: Path) -> str:
        """Extract text from TXT"""
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            return await f.read()
    
    async def save_document(self, document) -> str:
        """Save document metadata to JSON file"""
        doc_id = f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        metadata = {
            "id": doc_id,
            "filename": document.filename,
            "file_path": document.file_path,
            "processed_text": document.processed_text,
            "content_type": document.content_type,
            "created_at": datetime.now().isoformat()
        }
        
        metadata_file = self.metadata_dir / f"{doc_id}.json"
        async with aiofiles.open(metadata_file, 'w') as f:
            await f.write(json.dumps(metadata, indent=2))
        
        return doc_id
    
    async def get_document(self, doc_id: str):
        """Retrieve document metadata"""
        metadata_file = self.metadata_dir / f"{doc_id}.json"
        
        if not metadata_file.exists():
            raise FileNotFoundError(f"Document {doc_id} not found")
        
        async with aiofiles.open(metadata_file, 'r') as f:
            content = await f.read()
            metadata = json.loads(content)
        
        return type('Document', (), metadata)()
```

### 3. **Portal Integration Points**

```python
# main_portal/app.py (Flask main app)
from flask import Flask, render_template, request, jsonify
from .voice_agent_integration import VoiceAgentIntegration

app = Flask(__name__)
voice_agent = VoiceAgentIntegration()

@app.route('/dashboard')
def dashboard():
    """Main portal dashboard with voice agent widget"""
    return render_template('dashboard.html')

@app.route('/voice-agent')
def voice_agent_page():
    """Dedicated voice agent page"""
    return render_template('voice_agent.html')

@app.route('/api/voice-agent/embed')
def voice_agent_embed():
    """Embed voice agent in existing pages"""
    return render_template('voice_agent_embed.html')

# main_portal/templates/dashboard.html
<!DOCTYPE html>
<html>
<head>
    <title>Portal Dashboard</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/dashboard.css') }}">
</head>
<body>
    <div class="dashboard-container">
        <header class="dashboard-header">
            <h1>Portal Dashboard</h1>
            <nav>
                <a href="/voice-agent">Voice Agent</a>
                <a href="/documents">Documents</a>
                <a href="/reports">Reports</a>
            </nav>
        </header>
        
        <main class="dashboard-main">
            <div class="dashboard-widgets">
                <!-- Existing portal widgets -->
                <div class="widget">
                    <h3>Recent Activity</h3>
                    <!-- Content -->
                </div>
                
                <!-- Voice Agent Widget -->
                <div class="widget voice-agent-widget">
                    <h3>AI Document Assistant</h3>
                    <div id="voice-agent-embed"></div>
                </div>
            </div>
        </main>
    </div>
    
    <!-- Load Voice Agent as Widget -->
    <script>
        // Load voice agent React component
        const voiceAgentContainer = document.getElementById('voice-agent-embed');
        
        // Option 1: Load as iframe
        const iframe = document.createElement('iframe');
        iframe.src = '/voice-agent/embed';
        iframe.style.width = '100%';
        iframe.style.height = '400px';
        iframe.style.border = 'none';
        voiceAgentContainer.appendChild(iframe);
        
        // Option 2: Load React component directly (if using same build system)
        // ReactDOM.render(React.createElement(VoiceAgentWidget), voiceAgentContainer);
    </script>
</body>
</html>
```

### 4. **React Component Integration**

```javascript
// main_portal/static/js/VoiceAgentWidget.js
class VoiceAgentWidget {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.apiBase = options.apiBase || '/api/voice-agent';
        this.init();
    }
    
    init() {
        this.render();
        this.attachEventListeners();
    }
    
    render() {
        this.container.innerHTML = `
            <div class="voice-agent-widget">
                <div class="upload-section">
                    <input type="file" id="document-upload" accept=".pdf,.docx,.txt">
                    <button id="upload-btn">Upload Document</button>
                </div>
                
                <div class="chat-section" style="display: none;">
                    <div id="chat-messages"></div>
                    <div class="input-section">
                        <input type="text" id="message-input" placeholder="Ask about your document...">
                        <button id="send-btn">Send</button>
                        <button id="voice-btn">🎤</button>
                    </div>
                </div>
                
                <div class="podcast-section" style="display: none;">
                    <button id="generate-podcast">Generate Podcast</button>
                    <audio id="podcast-player" controls style="display: none;"></audio>
                </div>
            </div>
        `;
    }
    
    attachEventListeners() {
        const uploadBtn = this.container.querySelector('#upload-btn');
        const sendBtn = this.container.querySelector('#send-btn');
        const voiceBtn = this.container.querySelector('#voice-btn');
        const podcastBtn = this.container.querySelector('#generate-podcast');
        
        uploadBtn.addEventListener('click', () => this.uploadDocument());
        sendBtn.addEventListener('click', () => this.sendMessage());
        voiceBtn.addEventListener('click', () => this.toggleVoiceInput());
        podcastBtn.addEventListener('click', () => this.generatePodcast());
    }
    
    async uploadDocument() {
        const fileInput = this.container.querySelector('#document-upload');
        const file = fileInput.files[0];
        
        if (!file) return;
        
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            const response = await fetch(`${this.apiBase}/upload/`, {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            this.documentId = result.document_id;
            
            // Show chat section
            this.container.querySelector('.chat-section').style.display = 'block';
            this.container.querySelector('.podcast-section').style.display = 'block';
            
            this.addMessage('system', `Document "${result.filename}" uploaded successfully!`);
        } catch (error) {
            console.error('Upload failed:', error);
            this.addMessage('error', 'Failed to upload document');
        }
    }
    
    async sendMessage() {
        const messageInput = this.container.querySelector('#message-input');
        const message = messageInput.value.trim();
        
        if (!message || !this.documentId) return;
        
        this.addMessage('user', message);
        messageInput.value = '';
        
        try {
            const response = await fetch(`${this.apiBase}/chat/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    document_id: this.documentId,
                    message: message,
                    agent_type: 'analytical'
                })
            });
            
            const result = await response.json();
            this.addMessage('agent', result.response);
        } catch (error) {
            console.error('Message failed:', error);
            this.addMessage('error', 'Failed to process message');
        }
    }
    
    addMessage(type, content) {
        const messagesContainer = this.container.querySelector('#chat-messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        messageDiv.textContent = content;
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
}

// Usage in portal pages
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('voice-agent-widget')) {
        new VoiceAgentWidget('voice-agent-widget', {
            apiBase: '/api/voice-agent'
        });
    }
});
```

### 5. **Docker Compose Setup for Portal + Voice Agent**

```yaml
# docker-compose.yml
version: '3.8'

services:
  # Main Portal (Flask)
  portal:
    build: ./main_portal
    ports:
      - "5000:5000"
    environment:
      - VOICE_AGENT_URL=http://voice-agent:8001
    depends_on:
      - voice-agent
      - redis
    volumes:
      - ./main_portal:/app
    
  # Voice Agent Service (FastAPI)
  voice-agent:
    build: ./voice_agent_service
    ports:
      - "8001:8001"
    environment:
      - OLLAMA_URL=http://ollama:11434
    depends_on:
      - ollama
    volumes:
      - voice_agent_uploads:/app/uploads
      - voice_agent_audio:/app/audio
    
  # Ollama LLM Service
  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    
  # Redis for caching
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    
  # Nginx reverse proxy
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - portal
      - voice-agent

volumes:
  voice_agent_uploads:
  voice_agent_audio:
  ollama_data:
```

### 6. **Nginx Configuration**

```nginx
# nginx.conf
events {
    worker_connections 1024;
}

http {
    upstream portal {
        server portal:5000;
    }
    
    upstream voice_agent {
        server voice-agent:8001;
    }
    
    server {
        listen 80;
        
        # Main portal routes
        location / {
            proxy_pass http://portal;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
        
        # Voice agent API routes
        location /api/voice-agent/ {
            proxy_pass http://voice_agent/api/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
        
        # Voice agent static files
        location /voice-agent/static/ {
            proxy_pass http://voice_agent/static/;
        }
    }
}
```

## Integration Recommendations:

### **For Existing Portal:**
1. **Microservice Approach**: Keep voice agent as separate service
2. **API Gateway**: Use nginx or similar for routing
3. **Widget Integration**: Embed as iframe or React component
4. **Shared Authentication**: Use JWT tokens or session sharing

### **For New Portal:**
1. **Monolithic Approach**: Integrate directly into Flask/FastAPI
2. **Modular Structure**: Keep voice agent as separate module
3. **Shared Database**: Use same database for all components
4. **Unified Frontend**: Single React app with multiple features

### **Key Considerations:**
- **Authentication**: How will users authenticate across services?
- **Data Sharing**: How will documents/conversations be shared?
- **Deployment**: Container orchestration vs single deployment
- **Scaling**: Independent scaling vs unified scaling
- **Monitoring**: Centralized logging and monitoring

Would you like me to elaborate on any of these approaches or help you implement a specific integration strategy?