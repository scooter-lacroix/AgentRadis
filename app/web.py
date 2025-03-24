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
from app.agent.enhanced_radis import EnhancedRadis
from app.logger import logger

routes = web.RouteTableDef()

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
            logger.info("Initializing EnhancedRadis agent for web interface")
            agent = await EnhancedRadis()
            
            # Set up environment variables for tools
            os.environ['PYTHONPATH'] = os.getcwd()
            os.environ['WORKSPACE_ROOT'] = os.getcwd()
            
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
            .mode-switch {
                margin-bottom: 20px;
                padding: 10px;
                background: white;
                border-radius: 5px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                display: flex;
                align-items: center;
                gap: 10px;
            }
            
            .mode-switch label {
                font-weight: bold;
            }
            
            .mode-switch select {
                padding: 5px;
                border-radius: 3px;
                border: 1px solid #ddd;
            }
            
            .mode-indicator {
                padding: 5px 10px;
                border-radius: 3px;
                font-size: 0.9em;
                background: #e3f2fd;
                color: #1976d2;
            }
            
            .separator {
                color: #666;
                margin: 10px 0;
            }
            
            .tool-calls {
                margin: 10px 0;
            }
            
            .tool-call {
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                margin: 5px 0;
                padding: 10px;
            }
            
            .tool-name {
                font-weight: bold;
                color: #0056b3;
            }
            
            .tool-args {
                font-family: monospace;
                white-space: pre;
                margin: 5px 0;
                padding: 5px;
                background: #f1f3f5;
                border-radius: 3px;
            }
            
            .tool-result {
                margin-top: 5px;
                padding: 5px;
                border-radius: 3px;
            }
            
            .tool-result.success {
                background: #d4edda;
                color: #155724;
            }
            
            .tool-result.error {
                background: #f8d7da;
                color: #721c24;
            }
            
            .artifacts {
                margin: 10px 0;
            }
            
            .artifact {
                margin: 5px 0;
                padding: 10px;
                border-radius: 4px;
            }
            
            .artifact.code {
                background: #272822;
                color: #f8f8f2;
            }
            
            .artifact.web {
                background: #fff;
                border: 1px solid #dee2e6;
            }
            
            .artifact.project {
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                font-family: monospace;
                white-space: pre;
            }
            
            .response-box {
                margin: 10px 0;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                overflow: hidden;
            }
            
            .response-header {
                background: #f8f9fa;
                padding: 5px 10px;
                font-weight: bold;
                border-bottom: 1px solid #dee2e6;
            }
            
            .response-content {
                padding: 10px;
                background: white;
            }

            .canvas-container {
                display: none;
                margin: 20px 0;
                padding: 20px;
                background: white;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }

            .canvas-container.active {
                display: block;
            }

            .canvas-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 15px;
                padding-bottom: 10px;
                border-bottom: 1px solid #dee2e6;
            }

            .canvas-title {
                font-size: 1.2em;
                font-weight: bold;
                color: #2196f3;
            }

            .canvas-controls {
                display: flex;
                gap: 10px;
            }

            .canvas-content {
                min-height: 200px;
                padding: 15px;
                background: #f8f9fa;
                border-radius: 5px;
                border: 1px solid #dee2e6;
            }

            .artifact-container {
                margin: 15px 0;
                padding: 15px;
                background: white;
                border-radius: 5px;
                border: 1px solid #dee2e6;
            }

            .artifact-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 10px;
                padding-bottom: 5px;
                border-bottom: 1px solid #dee2e6;
            }

            .artifact-type {
                font-weight: bold;
                color: #0056b3;
                text-transform: capitalize;
            }

            .artifact-content {
                overflow-x: auto;
            }

            .artifact-content pre {
                margin: 0;
                padding: 15px;
                background: #272822;
                border-radius: 5px;
            }

            .artifact-content code {
                font-family: 'Fira Code', monospace;
                font-size: 14px;
                line-height: 1.5;
            }

            .artifact-content.code {
                background: #272822;
                color: #f8f8f2;
                padding: 15px;
                border-radius: 5px;
            }

            .artifact-content.web {
                background: white;
                padding: 15px;
                border: 1px solid #dee2e6;
                border-radius: 5px;
            }

            .artifact-content.project {
                font-family: monospace;
                white-space: pre;
                background: #f8f9fa;
                padding: 15px;
                border: 1px solid #dee2e6;
                border-radius: 5px;
            }

            .copy-button {
                padding: 5px 10px;
                background: #6c757d;
                color: white;
                border: none;
                border-radius: 3px;
                cursor: pointer;
                font-size: 0.8em;
            }

            .copy-button:hover {
                background: #5a6268;
            }

            .copy-button.copied {
                background: #28a745;
            }
        </style>
    </head>
    <body>
        <div class="chat-container">
            <h1>AgentRadis Web Interface</h1>
            
            <div class="mode-switch">
                <label for="agent-mode">Agent Mode:</label>
                <select id="agent-mode">
                    <option value="act">Action Mode</option>
                    <option value="plan">Planning Mode</option>
                </select>
                <div class="mode-indicator" id="current-mode">Current: Action Mode</div>
            </div>
            
            <div class="file-upload">
                <h3>Upload File</h3>
                <form id="upload-form">
                    <input type="file" id="file-input" multiple>
                    <button type="submit">Upload</button>
                </form>
                <div id="upload-status"></div>
            </div>
            
            <div class="canvas-container" id="canvas-container">
                <div class="canvas-header">
                    <div class="canvas-title">Artifacts Canvas</div>
                    <div class="canvas-controls">
                        <button class="copy-button" id="copy-all-button">Copy All</button>
                    </div>
                </div>
                <div class="canvas-content" id="canvas-content">
                    <!-- Artifacts will be dynamically added here -->
                </div>
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
            const agentMode = document.getElementById('agent-mode');
            const currentMode = document.getElementById('current-mode');
            
            // Update mode indicator when mode is changed
            agentMode.addEventListener('change', function() {
                const mode = this.value;
                const modeName = mode === 'act' ? 'Action Mode' : 'Planning Mode';
                currentMode.textContent = `Current: ${modeName}`;
            });
            
            function addMessage(content, isUser = false, artifacts = [], toolCalls = []) {
                const div = document.createElement('div');
                div.className = `message ${isUser ? 'user-message' : 'assistant-message'}`;
                
                // Add separator before assistant message
                if (!isUser) {
                    const separator = document.createElement('div');
                    separator.className = 'separator';
                    separator.textContent = '=' .repeat(80);
                    chatBox.appendChild(separator);
                }
                
                // Handle artifacts in canvas
                if (artifacts && artifacts.length > 0) {
                    const canvasContainer = document.getElementById('canvas-container');
                    const canvasContent = document.getElementById('canvas-content');
                    
                    // Clear previous content
                    canvasContent.innerHTML = '';
                    
                    // Add each artifact
                    artifacts.forEach((artifact, index) => {
                        const artifactDiv = document.createElement('div');
                        artifactDiv.className = 'artifact-container';
                        
                        const artifactHeader = document.createElement('div');
                        artifactHeader.className = 'artifact-header';
                        
                        const artifactType = document.createElement('div');
                        artifactType.className = 'artifact-type';
                        artifactType.textContent = `${artifact.type} ${index + 1}`;
                        
                        const copyButton = document.createElement('button');
                        copyButton.className = 'copy-button';
                        copyButton.textContent = 'Copy';
                        copyButton.onclick = () => {
                            navigator.clipboard.writeText(artifact.content).then(() => {
                                copyButton.textContent = 'Copied!';
                                copyButton.classList.add('copied');
                                setTimeout(() => {
                                    copyButton.textContent = 'Copy';
                                    copyButton.classList.remove('copied');
                                }, 2000);
                            });
                        };
                        
                        artifactHeader.appendChild(artifactType);
                        artifactHeader.appendChild(copyButton);
                        
                        const artifactContent = document.createElement('div');
                        artifactContent.className = `artifact-content ${artifact.type}`;
                        
                        switch (artifact.type) {
                            case 'code':
                                artifactContent.innerHTML = `
                                    <pre><code class="${artifact.language || 'plaintext'}">${artifact.content}</code></pre>
                                `;
                                break;
                            case 'web':
                                artifactContent.innerHTML = artifact.content;
                                break;
                            case 'project':
                                artifactContent.innerHTML = `<pre>${artifact.content}</pre>`;
                                break;
                        }
                        
                        artifactDiv.appendChild(artifactHeader);
                        artifactDiv.appendChild(artifactContent);
                        canvasContent.appendChild(artifactDiv);
                    });
                    
                    // Show the canvas container
                    canvasContainer.classList.add('active');
                    
                    // Set up copy all button
                    const copyAllButton = document.getElementById('copy-all-button');
                    copyAllButton.onclick = () => {
                        const allContent = artifacts.map(a => a.content).join('\n\n');
                        navigator.clipboard.writeText(allContent).then(() => {
                            copyAllButton.textContent = 'All Copied!';
                            copyAllButton.classList.add('copied');
                            setTimeout(() => {
                                copyAllButton.textContent = 'Copy All';
                                copyAllButton.classList.remove('copied');
                            }, 2000);
                        });
                    };
                } else {
                    // Hide the canvas container if no artifacts
                    const canvasContainer = document.getElementById('canvas-container');
                    canvasContainer.classList.remove('active');
                }
                
                // Add tool calls if present
                if (toolCalls && toolCalls.length > 0) {
                    const toolsDiv = document.createElement('div');
                    toolsDiv.className = 'tool-calls';
                    toolCalls.forEach(tool => {
                        const toolDiv = document.createElement('div');
                        toolDiv.className = 'tool-call';
                        toolDiv.innerHTML = `
                            <div class="tool-name">${tool.name}</div>
                            <div class="tool-args">${JSON.stringify(tool.args, null, 2)}</div>
                            <div class="tool-result ${tool.success ? 'success' : 'error'}">
                                ${tool.result}
                            </div>
                        `;
                        toolsDiv.appendChild(toolDiv);
                    });
                    div.appendChild(toolsDiv);
                }
                
                // Add the main response in a box format
                const responseBox = document.createElement('div');
                responseBox.className = 'response-box';
                responseBox.innerHTML = `
                    <div class="response-header">RESULT</div>
                    <div class="response-content">${content}</div>
                `;
                div.appendChild(responseBox);
                
                // Add separator after assistant message
                if (!isUser) {
                    const separator = document.createElement('div');
                    separator.className = 'separator';
                    separator.textContent = '=' .repeat(80);
                    chatBox.appendChild(separator);
                }
                
                chatBox.appendChild(div);
                chatBox.scrollTop = chatBox.scrollHeight;
            }
            
            async function sendPrompt() {
                const prompt = promptInput.value.trim();
                if (!prompt) return;
                
                addMessage(prompt, true);
                promptInput.value = '';
                sendBtn.disabled = true;
                
                try {
                    const response = await fetch('/api/chat', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            prompt: prompt,
                            mode: agentMode.value
                        })
                    });
                    
                    if (!response.ok) {
                        throw new Error(`API responded with status ${response.status}`);
                    }
                    
                    const data = await response.json();
                    addMessage(
                        data.response,
                        false,
                        data.artifacts || [],
                        data.tool_calls || []
                    );
                    
                } catch (error) {
                    addMessage(`Error: ${error.message}`, false);
                } finally {
                    sendBtn.disabled = false;
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

@routes.post('/api/chat')
async def chat(request):
    try:
        data = await request.json()
        prompt = data.get('prompt')
        mode = data.get('mode', 'plan')
        
        if not prompt:
            return web.json_response({'error': 'No prompt provided'}, status=400)
        
        # Initialize agent if needed
        if 'agent' not in request.app:
            logger.info("Initializing agent for web interface")
            request.app['agent'] = await initialize_agent()
        
        agent = request.app['agent']
        logger.info(f"Processing prompt in {mode} mode: {prompt[:100]}...")
        
        # Set the mode if specified
        agent.mode = mode
        
        try:
            # Run the agent with the prompt
            result = await agent.run(prompt)
            logger.info("Agent completed processing prompt")
            
            # Extract artifacts and tool calls
            artifacts = []
            tool_calls = []
            
            if result.get('artifacts'):
                for artifact in result['artifacts']:
                    artifacts.append({
                        'type': artifact.get('type', 'code'),
                        'content': artifact.get('content', ''),
                        'language': artifact.get('language', 'plaintext')
                    })
                logger.info(f"Processed {len(artifacts)} artifacts")
            
            if result.get('tool_calls'):
                for tool_call in result['tool_calls']:
                    # Fix file paths in tool results
                    if tool_call.get('name') in ['file_saver', 'execute_command']:
                        result = tool_call.get('result', '')
                        if isinstance(result, str):
                            result = result.replace('/home/stan/AgentRadis_Saves/', '')
                            result = result.replace('/home/stan/Dew/AgentRadis/', '')
                    
                    tool_calls.append({
                        'name': tool_call.get('name', 'unknown'),
                        'args': tool_call.get('args', {}),
                        'result': result,
                        'success': tool_call.get('success', True),
                        'error': tool_call.get('error', '')
                    })
                logger.info(f"Processed {len(tool_calls)} tool calls")
            
            response = {
                'response': result.get('response', ''),
                'artifacts': artifacts,
                'tool_calls': tool_calls,
                'status': result.get('status', 'success')
            }
            
            return web.json_response(response)
            
        except Exception as e:
            logger.error(f"Error during agent execution: {str(e)}")
            return web.json_response({
                'error': f"Agent execution error: {str(e)}",
                'status': 'error'
            }, status=500)
        
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {str(e)}")
        return web.json_response({
            'error': str(e),
            'status': 'error'
        }, status=500)

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
    cors.add(app.router.add_post('/api/chat', chat))
    cors.add(app.router.add_post('/interrupt', interrupt))
    cors.add(app.router.add_post('/upload', upload))

def create_app():
    """Create the web application"""
    app = web.Application()
    app.router.add_routes(routes)
    setup_routes(app)
    return app

async def start_server_async(host='0.0.0.0', port=5000, api_base=None):
    """Start the web server asynchronously"""
    app = create_app()
    
    # Initialize the agent
    app['agent'] = await initialize_agent(api_base)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    print(f"🌐 AgentRadis Web Interface running at http://{host}:{port}")
    try:
        await asyncio.Event().wait()  # run forever
    finally:
        await runner.cleanup()

def start_server(host='0.0.0.0', port=5000, api_base=None):
    """Start the web server"""
    asyncio.run(start_server_async(host, port, api_base))

if __name__ == '__main__':
    start_server() 