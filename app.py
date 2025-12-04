"""
FastAPI web application for the Health Literacy Pipeline.
Provides a simple web UI for processing URLs through the pipeline.
"""

import json
import asyncio
from pathlib import Path
from queue import Queue, Empty
from threading import Thread
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, HTMLResponse
from jinja2 import Environment, FileSystemLoader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from main import process_pipeline, is_valid_url

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup templates
template_dir = Path(__file__).parent / "templates"
env = Environment(loader=FileSystemLoader(str(template_dir)))


class URLRequest(BaseModel):
    url: str


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the main UI page."""
    template = env.get_template("index.html")
    return HTMLResponse(content=template.render())


@app.post("/api/process")
async def process_url(request: URLRequest):
    """
    Process a URL through the pipeline and stream progress updates.
    Returns a streaming response with JSON lines containing progress messages.
    """
    url = request.url.strip()
    
    # Validate URL
    if not url:
        async def error_generator():
            yield json.dumps({"type": "error", "message": "URL cannot be empty"}) + "\n"
        return StreamingResponse(error_generator(), media_type="text/plain")
    
    if not is_valid_url(url):
        async def error_generator():
            yield json.dumps({"type": "error", "message": f"Invalid URL: {url}"}) + "\n"
        return StreamingResponse(error_generator(), media_type="text/plain")
    
    # Process pipeline with progress updates
    # Use a queue to stream results from the sync generator running in a thread
    async def generate():
        queue = Queue()
        done = False
        error = None
        
        def run_pipeline():
            """Run the sync pipeline in a separate thread and put results in queue."""
            nonlocal done, error
            try:
                generator = process_pipeline(url, yield_progress=True)
                for msg_type, message in generator:
                    # Put all messages in queue (dicts will be serialized by json.dumps)
                    queue.put((msg_type, message))
                queue.put(None)  # Signal completion
            except Exception as e:
                error = str(e)
                queue.put(None)  # Signal completion even on error
            finally:
                done = True
        
        # Start the pipeline in a separate thread
        thread = Thread(target=run_pipeline, daemon=True)
        thread.start()
        
        # Stream results from the queue
        try:
            while not done or not queue.empty():
                try:
                    # Wait for items with a timeout to allow checking if done
                    item = queue.get(timeout=0.1)
                    if item is None:
                        break
                    msg_type, message = item
                    yield json.dumps({"type": msg_type, "message": message}) + "\n"
                except Empty:
                    # Queue is empty, check if thread is done
                    if done:
                        break
                    # Small sleep to avoid busy waiting
                    await asyncio.sleep(0.05)
            
            # If there was an error, yield it
            if error:
                yield json.dumps({"type": "error", "message": f"Pipeline error: {error}"}) + "\n"
        except Exception as e:
            yield json.dumps({"type": "error", "message": f"Streaming error: {str(e)}"}) + "\n"
    
    return StreamingResponse(generate(), media_type="text/plain")

