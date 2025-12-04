"""
Text summarization module using OpenAI API.
Summarizes text to extract core ideas and main points before simplification.
"""

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI
from dotenv import load_dotenv
import sys

# Load environment variables
load_dotenv()

# OpenAI configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")

# Token limits
MAX_TOKENS_PER_CHUNK = 100000  # Input tokens per chunk
MAX_OUTPUT_TOKENS = 16000  # Max tokens for response


def _estimate_tokens(text: str) -> int:
    """Rough estimate of token count."""
    return len(text) // 4


def _split_text_into_chunks(text: str, max_tokens: int = MAX_TOKENS_PER_CHUNK) -> list[str]:
    """Split text into chunks that fit within token limits."""
    estimated_tokens = _estimate_tokens(text)
    
    if estimated_tokens <= max_tokens:
        return [text]
    
    # Split by paragraphs
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = []
    current_size = 0
    
    for paragraph in paragraphs:
        para_tokens = _estimate_tokens(paragraph)
        
        if para_tokens > max_tokens:
            # Flush current chunk
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_size = 0
            
            # Split large paragraph by sentences
            sentences = paragraph.split(". ")
            for sentence in sentences:
                sent_tokens = _estimate_tokens(sentence)
                if current_size + sent_tokens > max_tokens:
                    if current_chunk:
                        chunks.append("\n\n".join(current_chunk))
                    current_chunk = [sentence]
                    current_size = sent_tokens
                else:
                    current_chunk.append(sentence)
                    current_size += sent_tokens
        else:
            if current_size + para_tokens > max_tokens:
                if current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                current_chunk = [paragraph]
                current_size = para_tokens
            else:
                current_chunk.append(paragraph)
                current_size += para_tokens
    
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))
    
    return chunks


def summarize_text(text: str) -> str:
    """
    Summarize text to extract core ideas and main points.
    Reduces text length while preserving essential information.
    
    Args:
        text: Text to summarize
        
    Returns:
        Summarized text with core ideas
        
    Raises:
        ValueError: If API key is not set
        Exception: If API call fails
    """
    if not OPENAI_API_KEY:
        raise ValueError(
            "OpenAI API key not found. Please set OPENAI_API_KEY in your .env file."
        )
    
    # System prompt for summarization
    system_prompt = """You are an expert at extracting and summarizing core ideas from health and medical content.

*** Task ***
Your task is to create a concise summary that captures the essential information, main ideas, and key points from the given text.

*** Guidelines ***
- Extract the main ideas and core concepts
- Preserve all important health/medical information (symptoms, treatments, recommendations, warnings)
- Remove redundant information, examples, and less critical details
- Maintain logical structure and flow
- Keep headings and section organization when present
- Focus on actionable information and key takeaways
- Target a summary that is 20-30% of the original length while retaining all essential information

*** Output format ***
- Preserve document structure (headings, paragraphs) when present
- put all headings in ALL CAPS
- Use clear, concise language
- Output in txt format
"""
    
    # Split text into chunks if needed
    chunks = _split_text_into_chunks(text)
    
    def process_chunk(chunk_data):
        """Process a single chunk and return (index, summarized_chunk)."""
        index, chunk = chunk_data
        try:
            print(f"[Chunk {index+1}/{len(chunks)}] Starting summarization API call...", file=sys.stderr)
            
            # Create a new client for this thread (OpenAI client is not thread-safe)
            # Set longer timeout for slow networks (300 seconds = 5 minutes)
            thread_client = OpenAI(
                api_key=OPENAI_API_KEY,
                timeout=300.0  # 5 minute timeout for slow networks
            )
            
            print(f"[Chunk {index+1}/{len(chunks)}] Sending request to OpenAI (chunk size: {len(chunk)} chars)...", file=sys.stderr)
            response = thread_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Summarize the following text, extracting the core ideas and main points:\n\n{chunk}"}
                ],
                max_completion_tokens=MAX_OUTPUT_TOKENS,
                timeout=300.0  # 5 minute timeout
            )
            
            print(f"[Chunk {index+1}/{len(chunks)}] Received response from OpenAI", file=sys.stderr)
            summarized_chunk = response.choices[0].message.content
            
            # Add validation to prevent empty responses
            if not summarized_chunk or len(summarized_chunk.strip()) == 0:
                print(f"[Chunk {index+1}/{len(chunks)}] ERROR: Returned empty content! Using original chunk.", file=sys.stderr)
                summarized_chunk = chunk  # Fallback to original
            else:
                print(f"[Chunk {index+1}/{len(chunks)}] Success: {len(chunk)} -> {len(summarized_chunk)} characters", file=sys.stderr)
            
            return (index, summarized_chunk)
            
        except Exception as e:
            print(f"[Chunk {index+1}/{len(chunks)}] ERROR: {e}", file=sys.stderr)
            raise Exception(f"Error calling OpenAI API for summarization chunk {index+1}: {e}")
    
    # Process chunks in parallel
    summarized_chunks = [None] * len(chunks)  # Pre-allocate list to maintain order
    
    if len(chunks) == 1:
        # Single chunk, no need for parallelization
        print(f"Processing 1 chunk...", file=sys.stderr)
        _, summarized_chunk = process_chunk((0, chunks[0]))
        summarized_chunks[0] = summarized_chunk
        print(f"Chunk 1 completed", file=sys.stderr)
    else:
        # Process multiple chunks in parallel
        print(f"Processing {len(chunks)} chunks in parallel...", file=sys.stderr)
        with ThreadPoolExecutor(max_workers=min(len(chunks), 5)) as executor:
            # Submit all tasks
            print(f"Submitted {len(chunks)} chunk processing tasks", file=sys.stderr)
            future_to_index = {
                executor.submit(process_chunk, (i, chunk)): i 
                for i, chunk in enumerate(chunks)
            }
            
            # Collect results as they complete
            completed = 0
            for future in as_completed(future_to_index):
                try:
                    index, summarized_chunk = future.result()
                    summarized_chunks[index] = summarized_chunk
                    completed += 1
                    print(f"Chunk {index+1} completed ({completed}/{len(chunks)} total)", file=sys.stderr)
                except Exception as e:
                    # If one chunk fails, re-raise the exception
                    print(f"Chunk {future_to_index[future]+1} failed: {e}", file=sys.stderr)
                    raise e
    
    # Join chunks back together in order
    summarized_text = "\n\n".join(summarized_chunks)
    
    # Final validation - if summarized text is empty, return original
    if len(summarized_text.strip()) == 0:
        print(f"ERROR: Summarized text is empty! Returning original text.", file=sys.stderr)
        return text
    
    return summarized_text

