"""
Web interface for AgentRadis
"""

import os
import json
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
from aiohttp import web
import aiohttp_cors
from app.agent.radis import create_radis_agent
from app.logger import logger

# Global state
agent = None
current_task = None
interrupt_event = asyncio.Event()
user_input_queue = asyncio.Queue()

async def initialize_agent(api_base: Optional[str] = None):
    """Initialize the agent instance"""
    global agent
    try:
        if agent is None:
            logger.info("Initializing Radis agent for web interface")
            agent = create_radis_agent(api_base=api_base)
            # Verify that basic tools are loaded
            tools = agent.get_tools()
            logger.info(f"Agent initialized with {len(tools)} tools")
            
            # Preload the LLM to establish connection
            from app.llm import LLM
            llm = LLM()
            try:
                connection_test = await llm.test_llm_connection()
                if connection_test.get("success", False):
                    logger.info("LLM connection established successfully")
                else:
                    logger.warning(f"LLM connection test failed: {connection_test.get('error', 'Unknown error')}")
            except Exception as e:
                logger.error(f"Error testing LLM connection: {str(e)}")
        return agent
    except Exception as e:
        logger.error(f"Error initializing agent: {str(e)}")
        import traceback
        traceback.print_exc()
        # Return a minimal agent that can still function in the web interface
        if agent is None:
            from app.agent.base import BaseAgent
            agent = BaseAgent()
        return agent

async def index(request):
    """Serve the main page"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AgentRadis Web Interface</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background: #f5f5f5;
            }
            .chat-container {
                background: white;
                border-radius: 10px;
                padding: 20px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            #chat-box {
                height: 400px;
                overflow-y: auto;
                border: 1px solid #ddd;
                padding: 10px;
                margin-bottom: 20px;
                border-radius: 5px;
            }
            .message {
                margin: 10px 0;
                padding: 10px;
                border-radius: 5px;
            }
            .user-message {
                background: #e3f2fd;
                margin-left: 20%;
            }
            .assistant-message {
                background: #f5f5f5;
                margin-right: 20%;
            }
            .input-container {
                display: flex;
                gap: 10px;
                margin-bottom: 20px;
            }
            #prompt-input {
                flex-grow: 1;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 5px;
            }
            button {
                padding: 10px 20px;
                background: #2196f3;
                color: white;
                border: none;
                border-radius: 5px;
                cursor: pointer;
            }
            button:hover {
                background: #1976d2;
            }
            .file-upload {
                margin-bottom: 20px;
                padding: 10px;
                background: white;
                border-radius: 5px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }
            .controls {
                display: flex;
                gap: 10px;
                margin-bottom: 10px;
            }
            #interrupt-btn {
                background: #ff5722;
            }
            #interrupt-btn:hover {
                background: #f4511e;
            }
            .interrupt-input {
                display: none;
                margin-top: 10px;
            }
            .interrupt-input.active {
                display: block;
            }
            .status {
                color: #666;
                font-style: italic;
                margin: 5px 0;
            }
        </style>
    </head>
    <body>
        <div class="chat-container">
            <h1>AgentRadis Web Interface</h1>
            
            <div class="file-upload">
                <h3>Upload File</h3>
                <form id="upload-form">
                    <input type="file" id="file-input" multiple>
                    <button type="submit">Upload</button>
                </form>
                <div id="upload-status"></div>
            </div>
            
            <div id="chat-box"></div>
            
            <div class="controls">
                <button id="interrupt-btn">Interrupt</button>
                <div class="interrupt-input" id="interrupt-container">
                    <input type="text" id="interrupt-input" placeholder="Add context or update task...">
                    <button id="send-interrupt">Send</button>
                </div>
            </div>
            
            <div class="input-container">
                <input type="text" id="prompt-input" placeholder="Enter your prompt...">
                <button id="send-btn">Send</button>
            </div>
            
            <div id="status" class="status"></div>
        </div>

        <script>
            const chatBox = document.getElementById('chat-box');
            const promptInput = document.getElementById('prompt-input');
            const sendBtn = document.getElementById('send-btn');
            const interruptBtn = document.getElementById('interrupt-btn');
            const interruptContainer = document.getElementById('interrupt-container');
            const interruptInput = document.getElementById('interrupt-input');
            const sendInterruptBtn = document.getElementById('send-interrupt');
            const uploadForm = document.getElementById('upload-form');
            const uploadStatus = document.getElementById('upload-status');
            const status = document.getElementById('status');
            
            function addMessage(content, isUser = false) {
                const div = document.createElement('div');
                div.className = `message ${isUser ? 'user-message' : 'assistant-message'}`;
                div.textContent = content;
                chatBox.appendChild(div);
                chatBox.scrollTop = chatBox.scrollHeight;
            }
            
            async function sendPrompt() {
                const prompt = promptInput.value.trim();
                if (!prompt) return;
                
                addMessage(prompt, true);
                promptInput.value = '';
                status.textContent = 'Processing...';
                
                try {
                    const response = await fetch('/chat', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({prompt})
                    });
                    
                    const data = await response.json();
                    addMessage(data.response);
                    status.textContent = '';
                } catch (error) {
                    status.textContent = 'Error: ' + error.message;
                }
            }
            
            async function handleInterrupt() {
                interruptContainer.classList.toggle('active');
                if (interruptContainer.classList.contains('active')) {
                    interruptInput.focus();
                }
            }
            
            async function sendInterrupt() {
                const content = interruptInput.value.trim();
                if (!content) return;
                
                try {
                    const response = await fetch('/interrupt', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({content})
                    });
                    
                    const data = await response.json();
                    addMessage('(Interrupt) ' + content, true);
                    if (data.response) {
                        addMessage(data.response);
                    }
                    
                    interruptInput.value = '';
                    interruptContainer.classList.remove('active');
                } catch (error) {
                    status.textContent = 'Error sending interrupt: ' + error.message;
                }
            }
            
            async function handleFileUpload(event) {
                event.preventDefault();
                const fileInput = document.getElementById('file-input');
                const files = fileInput.files;
                
                if (files.length === 0) {
                    uploadStatus.textContent = 'Please select files to upload';
                    return;
                }
                
                const formData = new FormData();
                for (let file of files) {
                    formData.append('files', file);
                }
                
                uploadStatus.textContent = 'Uploading...';
                
                try {
                    const response = await fetch('/upload', {
                        method: 'POST',
                        body: formData
                    });
                    
                    const data = await response.json();
                    uploadStatus.textContent = data.message;
                    
                    if (data.files) {
                        const fileList = data.files.map(f => f.name).join(', ');
                        addMessage(`Files uploaded: ${fileList}`);
                    }
                    
                    fileInput.value = '';
                } catch (error) {
                    uploadStatus.textContent = 'Error uploading files: ' + error.message;
                }
            }
            
            // Event listeners
            sendBtn.addEventListener('click', sendPrompt);
            promptInput.addEventListener('keypress', e => {
                if (e.key === 'Enter') sendPrompt();
            });
            
            interruptBtn.addEventListener('click', handleInterrupt);
            sendInterruptBtn.addEventListener('click', sendInterrupt);
            interruptInput.addEventListener('keypress', e => {
                if (e.key === 'Enter') sendInterrupt();
            });
            
            uploadForm.addEventListener('submit', handleFileUpload);
        </script>
    </body>
    </html>
    """
    return web.Response(text=html, content_type='text/html')

async def chat(request):
    """Handle chat requests"""
    global agent, current_task
    
    try:
        # Initialize agent if needed
        if agent is None:
            agent = await initialize_agent()
            
        # Get the prompt from the request
        data = await request.json()
        prompt = data.get('prompt', '')
        
        if not prompt:
            return web.json_response({
                'status': 'error',
                'response': 'No prompt provided'
            })
            
        # Run the agent
        current_task = asyncio.create_task(agent.run(prompt))
        response = await current_task
        current_task = None
        
        return web.json_response(response)
        
    except Exception as e:
        logger.error(f"Error in chat handler: {str(e)}")
        return web.json_response({
            'status': 'error',
            'response': f"Error processing request: {str(e)}"
        })

async def interrupt(request):
    """Handle interrupt requests"""
    global agent, current_task, interrupt_event
    
    try:
        data = await request.json()
        content = data.get('content', '')
        
        if current_task:
            # Signal interruption
            interrupt_event.set()
            # Cancel the current task
            current_task.cancel()
            
            try:
                await current_task
            except asyncio.CancelledError:
                pass
                
            current_task = None
            
            # Put the interrupt content in the queue
            if content:
                await user_input_queue.put(content)
            
            return web.json_response({
                'status': 'success',
                'response': 'Task interrupted'
            })
        else:
            return web.json_response({
                'status': 'error',
                'response': 'No task running'
            })
            
    except Exception as e:
        logger.error(f"Error in interrupt handler: {str(e)}")
        return web.json_response({
            'status': 'error',
            'response': f"Error interrupting task: {str(e)}"
        })

async def upload(request):
    """Handle file uploads"""
    global agent
    
    try:
        # Initialize agent if needed
        if agent is None:
            agent = await initialize_agent()
            
        reader = await request.multipart()
        files = []
        
        while True:
            part = await reader.next()
            if part is None:
                break
                
            if part.filename:
                # Save the file
                file_path = Path('uploads') / part.filename
                file_path.parent.mkdir(exist_ok=True)
                
                with open(file_path, 'wb') as f:
                    while True:
                        chunk = await part.read_chunk()
                        if not chunk:
                            break
                        f.write(chunk)
                        
                files.append({
                    'name': part.filename,
                    'path': str(file_path)
                })
                
        return web.json_response({
            'status': 'success',
            'message': f'Successfully uploaded {len(files)} files',
            'files': files
        })
        
    except Exception as e:
        logger.error(f"Error in upload handler: {str(e)}")
        return web.json_response({
            'status': 'error',
            'message': f'Error uploading files: {str(e)}'
        })

def setup_routes(app):
    """Set up routes and CORS configuration"""
    # Set up CORS
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        )
    })
    
    # Add routes
    cors.add(app.router.add_get('/', index))
    cors.add(app.router.add_post('/chat', chat))
    cors.add(app.router.add_post('/interrupt', interrupt))
    cors.add(app.router.add_post('/upload', upload))

def create_app():
    """Create the web application"""
    app = web.Application()
    setup_routes(app)
    return app

async def start_server_async(host='0.0.0.0', port=5001, api_base=None):
    """Start the web server asynchronously"""
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    print(f"🌐 AgentRadis Web Interface running at http://{host}:{port}")
    try:
        await asyncio.Event().wait()  # run forever
    finally:
        await runner.cleanup()

def start_server(host='0.0.0.0', port=5001, api_base=None):
    """Start the web server"""
    asyncio.run(start_server_async(host, port, api_base))

if __name__ == '__main__':
    start_server() 