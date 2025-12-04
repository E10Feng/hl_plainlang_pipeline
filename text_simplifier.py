"""
Text simplification module using OpenAI API.
Simplifies complex text to 7th grade reading level while preserving structure.
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

# Token limits (approximate, leaving room for prompt and response)
# Using conservative estimates to avoid token limit errors
MAX_TOKENS_PER_CHUNK = 300  # Input tokens per chunk
MAX_OUTPUT_TOKENS = 4000  # Max tokens for response


def _estimate_tokens(text: str) -> int:
    """
    Rough estimate of token count (OpenAI uses ~4 chars per token on average).
    This is a conservative estimate.
    """
    return len(text) // 4


def _split_text_into_chunks(text: str, max_tokens: int = MAX_TOKENS_PER_CHUNK) -> list[str]:
    """
    Split text into chunks that fit within token limits.
    Tries to split at paragraph boundaries to preserve structure.
    
    Args:
        text: Text to split
        max_tokens: Maximum tokens per chunk
        
    Returns:
        List of text chunks
    """
    estimated_tokens = _estimate_tokens(text)
    
    # If text fits in one chunk, return as-is
    if estimated_tokens <= max_tokens:
        return [text]
    
    # Split by double newlines (paragraph breaks) first
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = []
    current_size = 0
    
    for paragraph in paragraphs:
        para_tokens = _estimate_tokens(paragraph)
        
        # If single paragraph is too large, split by sentences
        if para_tokens > max_tokens:
            # Flush current chunk if it has content
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
            # Check if adding this paragraph would exceed limit
            if current_size + para_tokens > max_tokens:
                if current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                current_chunk = [paragraph]
                current_size = para_tokens
            else:
                current_chunk.append(paragraph)
                current_size += para_tokens
    
    # Add remaining chunk
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))
    
    return chunks


def simplify_text(text: str) -> str:
    """
    Simplify text to 7th grade reading level using OpenAI API.
    Preserves document structure (headings, paragraphs, formatting).
    
    Args:
        text: Text to simplify
        
    Returns:
        Simplified text at 7th grade reading level
        
    Raises:
        ValueError: If API key is not set
        Exception: If API call fails
    """
    if not OPENAI_API_KEY:
        raise ValueError(
            "OpenAI API key not found. Please set OPENAI_API_KEY in your .env file."
        )
    
    # System prompt for 7th grade simplification
    system_prompt = """
    You are an expert in health literacy and health-related communication. 
    
    *** Task ***
    Your task is to convert the given document containing complex health and medical information into plain language that can be understood at a 7th grade reading level. 

    *** Guidelines ***
    Make sure the output follows the guidelines in the following four areas:

        *** Vocabulary ***
        - simplify medical jargon and technical terms to everyday language
        - examples: "contagious" -> "can get", "innoculation" -> "shots", "exacerbate" -> "make it worse"

        *** Sentences ***
        - keep sentences betwee 7 and 15 words
        - always use active voice when possible
        - minimize distance between main nouns and verbs

        *** Cohesion ***
        - minimize ambigous pronouns and references between sentences
        - example: "wash and peel 6 carrots. then put them in the bowl." -> "wash and peel 6 carrots. then put the carrots in the bowl."

        *** Relevance and context ***
        - users of this tool will often be low English proficiency, immigrant, or low socioeconomic status, so make sure the output is easy to understand and follow.
    
    *** Output format ***
    - output in header and bullet point format for easy readability
    - output in txt format
 
    """
    
    # Split text into chunks if needed
    chunks = _split_text_into_chunks(text)
    
    def process_chunk(chunk_data):
        """Process a single chunk and return (index, simplified_chunk)."""
        index, chunk = chunk_data
        max_retries = 3
        
        # Create a new client for this thread (OpenAI client is not thread-safe)
        # Set longer timeout for slow networks (300 seconds = 5 minutes)
        thread_client = OpenAI(
            api_key=OPENAI_API_KEY,
            timeout=300.0  # 5 minute timeout for slow networks
        )
        
        for attempt in range(max_retries):
            try:
                if attempt == 0:
                    print(f"[Chunk {index+1}/{len(chunks)}] Starting API call...", file=sys.stderr)
                else:
                    print(f"[Chunk {index+1}/{len(chunks)}] Retry attempt {attempt + 1}/{max_retries}...", file=sys.stderr)
                
                print(f"[Chunk {index+1}/{len(chunks)}] Sending request to OpenAI (chunk size: {len(chunk)} chars)...", file=sys.stderr)
                response = thread_client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Simplify the following text to 7th grade reading level while preserving structure:\n\n{chunk}"}
                    ],
                    #temperature=0.3,  # Lower temperature for more consistent, focused output
                    max_completion_tokens=MAX_OUTPUT_TOKENS,
                    timeout=300.0  # 5 minute timeout
                )
                
                print(f"[Chunk {index+1}/{len(chunks)}] Received response from OpenAI", file=sys.stderr)
                simplified_chunk = response.choices[0].message.content
                
                # Check if response is empty
                if not simplified_chunk or len(simplified_chunk.strip()) == 0:
                    if attempt < max_retries - 1:
                        print(f"[Chunk {index+1}/{len(chunks)}] WARNING: Returned empty content! Retrying...", file=sys.stderr)
                        continue  # Retry
                    else:
                        # Last attempt failed, fallback to original
                        print(f"[Chunk {index+1}/{len(chunks)}] ERROR: Returned empty content after {max_retries} attempts! Using original chunk.", file=sys.stderr)
                        simplified_chunk = chunk  # Fallback to original
                else:
                    print(f"[Chunk {index+1}/{len(chunks)}] Success: {len(chunk)} -> {len(simplified_chunk)} characters", file=sys.stderr)
                
                return (index, simplified_chunk)
                
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"[Chunk {index+1}/{len(chunks)}] ERROR on attempt {attempt + 1}: {e}. Retrying...", file=sys.stderr)
                    continue  # Retry on exception
                else:
                    # Last attempt failed, re-raise exception
                    print(f"[Chunk {index+1}/{len(chunks)}] ERROR: Failed after {max_retries} attempts: {e}", file=sys.stderr)
                    raise Exception(f"Error calling OpenAI API for chunk {index+1} after {max_retries} attempts: {e}")
    
    # Process chunks in parallel
    simplified_chunks = [None] * len(chunks)  # Pre-allocate list to maintain order
    
    if len(chunks) == 1:
        # Single chunk, no need for parallelization
        print(f"Processing 1 chunk...", file=sys.stderr)
        _, simplified_chunk = process_chunk((0, chunks[0]))
        simplified_chunks[0] = simplified_chunk
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
                    index, simplified_chunk = future.result()
                    simplified_chunks[index] = simplified_chunk
                    completed += 1
                    print(f"Chunk {index+1} completed ({completed}/{len(chunks)} total)", file=sys.stderr)
                except Exception as e:
                    # If one chunk fails, re-raise the exception
                    print(f"Chunk {future_to_index[future]+1} failed: {e}", file=sys.stderr)
                    raise e
    
    # Join chunks back together in order
    simplified_text = "\n\n".join(simplified_chunks)
    
    # Final validation - if simplified text is empty, return original
    if len(simplified_text.strip()) == 0:
        print(f"ERROR: Simplified text is empty! Returning original text.", file=sys.stderr)
        return text
    
    return simplified_text

