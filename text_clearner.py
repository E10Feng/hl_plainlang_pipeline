"""
Text cleaning module using OpenAI API.
Removes extraneous content like ads, navigation, newsletter signups from web-extracted text.
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
MAX_TOKENS_PER_CHUNK = 3000
MAX_OUTPUT_TOKENS = 4000


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


def clean_text(text: str, is_from_url: bool = False) -> str:
    """
    Clean text by removing extraneous content like ads, navigation, etc.
    
    Args:
        text: Text to clean
        is_from_url: Whether text was extracted from a URL (more aggressive cleaning)
        
    Returns:
        Cleaned text with only main content
        
    Raises:
        ValueError: If API key is not set
        Exception: If API call fails
    """
    if not OPENAI_API_KEY:
        raise ValueError(
            "OpenAI API key not found. Please set OPENAI_API_KEY in your .env file."
        )
    
    # Skip cleaning if not from URL (PDFs usually don't have these issues)
    if not is_from_url:
        return text
    
    # System prompt for cleaning
    system_prompt = """You are a content extraction expert. Your task is to extract the main article/content from text that was scraped from a webpage.

IMPORTANT: You must preserve ALL substantive content. Only remove clearly extraneous elements.

Remove ONLY these clearly extraneous elements:
- Navigation menus (Home, About, Contact, etc.)
- Footer copyright notices and legal links
- Cookie consent banners
- Newsletter signup prompts ("Subscribe to our newsletter", "Sign up for updates")
- Social media share buttons ("Share on Facebook", "Tweet this")
- Related article recommendation sections
- Comment sections
- Site navigation breadcrumbs

Keep ALL of the following:
- The main article title
- The entire main article body/content
- All headings and subheadings within the article
- All paragraphs of substantive content
- Any lists, bullet points, or structured information
- Any important details or explanations

If you're unsure whether something should be removed, KEEP IT. It's better to include extra content than to remove important information.

Preserve the structure (paragraphs, headings) of the main content. Output the cleaned content."""
    
    # Split text into chunks if needed
    chunks = _split_text_into_chunks(text)
    
    def process_chunk(chunk_data):
        """Process a single chunk and return (index, cleaned_chunk)."""
        index, chunk = chunk_data
        try:
            print(f"[Chunk {index+1}/{len(chunks)}] Starting API call...", file=sys.stderr)
            
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
                    {"role": "user", "content": f"Extract only the main article content from the following text, removing all navigation, ads, and extraneous elements:\n\n{chunk}"}
                ],
                #temperature=0.2,  # Low temperature for consistent extraction
                max_completion_tokens=MAX_OUTPUT_TOKENS,
                timeout=300.0  # 5 minute timeout
            )
            
            print(f"[Chunk {index+1}/{len(chunks)}] Received response from OpenAI", file=sys.stderr)
            cleaned_chunk = response.choices[0].message.content
            
            # Add validation to prevent over-aggressive cleaning
            if not cleaned_chunk or len(cleaned_chunk.strip()) == 0:
                print(f"[Chunk {index+1}/{len(chunks)}] Warning: Returned empty content, using original chunk", file=sys.stderr)
                cleaned_chunk = chunk  # Fallback to original
            elif len(cleaned_chunk.strip()) < len(chunk.strip()) * 0.1:  # If cleaned is <10% of original
                print(f"[Chunk {index+1}/{len(chunks)}] Warning: Removed too much content ({len(cleaned_chunk)} vs {len(chunk)} chars), using original", file=sys.stderr)
                cleaned_chunk = chunk  # Fallback to original
            else:
                print(f"[Chunk {index+1}/{len(chunks)}] Success: {len(chunk)} -> {len(cleaned_chunk)} characters", file=sys.stderr)
            
            return (index, cleaned_chunk)
            
        except Exception as e:
            print(f"[Chunk {index+1}/{len(chunks)}] ERROR: {e}", file=sys.stderr)
            raise Exception(f"Error calling OpenAI API for cleaning chunk {index+1}: {e}")
    
    # Process chunks in parallel
    cleaned_chunks = [None] * len(chunks)  # Pre-allocate list to maintain order
    
    if len(chunks) == 1:
        # Single chunk, no need for parallelization
        print(f"Processing 1 chunk...", file=sys.stderr)
        _, cleaned_chunk = process_chunk((0, chunks[0]))
        cleaned_chunks[0] = cleaned_chunk
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
                    index, cleaned_chunk = future.result()
                    cleaned_chunks[index] = cleaned_chunk
                    completed += 1
                    print(f"Chunk {index+1} completed ({completed}/{len(chunks)} total)", file=sys.stderr)
                except Exception as e:
                    # If one chunk fails, re-raise the exception
                    print(f"Chunk {future_to_index[future]+1} failed: {e}", file=sys.stderr)
                    raise e
    
    # Join chunks back together in order
    cleaned_text = "\n\n".join(cleaned_chunks)
    
    # Final validation - if cleaned text is too short, return original
    if len(cleaned_text.strip()) < 0:
        print(f"Warning: Cleaning removed too much content overall ({len(cleaned_text)} vs {len(text)} chars), returning original text", file=sys.stderr)
        return text
    
    return cleaned_text