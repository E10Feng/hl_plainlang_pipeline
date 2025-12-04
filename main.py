"""
Main entry point for the Health Literacy Pipeline.
Processes PDF files or URLs and simplifies them to 7th grade reading level.
"""

import sys
import argparse
from pathlib import Path
from typing import Generator, Tuple, Union
from pdf_extractor import extract_text_from_pdf
from text_simplifier import simplify_text
from text_summarizer import summarize_text
from url_to_pdf import url_to_pdf, is_valid_url
from text_clearner import clean_text


def _process_pipeline_generator(input_source: str) -> Generator[Tuple[str, str], None, None]:
    """
    Internal generator that processes the pipeline and yields progress updates.
    """
    temp_pdf_path = None
    
    try:
        # Step 0: Detect input type and convert URL to PDF if needed
        if is_valid_url(input_source):
            yield ('progress', f'Detected URL input: {input_source}')
            
            try:
                yield ('progress', 'Converting URL to PDF...')
                temp_pdf_path = url_to_pdf(input_source)
                pdf_path = temp_pdf_path
                yield ('progress', f'URL converted to PDF successfully')
            except ValueError as e:
                error_msg = f"Error: {e}"
                yield ('error', error_msg)
                raise
            except Exception as e:
                error_msg = f"Error converting URL to PDF: {e}"
                yield ('error', error_msg)
                raise
        else:
            # Assume it's a file path
            pdf_path = input_source
        
        # Step 1: Extract text from PDF
        yield ('progress', f'Extracting text from PDF...')
        
        try:
            extracted_text = extract_text_from_pdf(pdf_path)
            yield ('progress', f'Successfully extracted {len(extracted_text)} characters')
        except FileNotFoundError as e:
            error_msg = f"Error: {e}"
            yield ('error', error_msg)
            raise
        except ValueError as e:
            error_msg = f"Error: {e}"
            yield ('error', error_msg)
            raise
        except Exception as e:
            error_msg = f"Error extracting text from PDF: {e}"
            yield ('error', error_msg)
            raise
        
        # Step 1.5: Clean text if from URL
        original_text_length = len(extracted_text)
        if is_valid_url(input_source):
            yield ('progress', 'Cleaning extracted text...')
            
            try:
                extracted_text = clean_text(extracted_text, is_from_url=True)
                yield ('progress', f'Text cleaning completed: {original_text_length} -> {len(extracted_text)} characters')
                
                if len(extracted_text.strip()) == 0:
                    warning_msg = "WARNING: Cleaned text is empty! Re-extracting without cleaning."
                    yield ('progress', warning_msg)
                    extracted_text = extract_text_from_pdf(pdf_path)
                elif len(extracted_text.strip()) < 100:
                    warning_msg = f"WARNING: Cleaned text is very short ({len(extracted_text)} chars). Consider checking the output."
                    yield ('progress', warning_msg)
            except ValueError as e:
                error_msg = f"Error: {e}"
                yield ('error', error_msg)
                raise
            except Exception as e:
                error_msg = f"Error cleaning text: {e}"
                yield ('error', error_msg)
                raise
        
        # Step 2: Summarize text to core ideas
        original_text_length = len(extracted_text)
        yield ('progress', 'Summarizing text to extract core ideas...')
        
        try:
            summarized_text = summarize_text(extracted_text)
            yield ('progress', f'Summarization completed: {original_text_length} -> {len(summarized_text)} characters')
            
            if len(summarized_text.strip()) == 0:
                error_msg = "ERROR: Summarized text is empty! Check API response."
                yield ('error', error_msg)
                raise ValueError(error_msg)
        except ValueError as e:
            error_msg = f"Error: {e}"
            yield ('error', error_msg)
            raise
        except Exception as e:
            error_msg = f"Error summarizing text: {e}"
            yield ('error', error_msg)
            raise
        
        # Step 3: Simplify summary to plain language
        summarized_text_length = len(summarized_text)
        yield ('progress', 'Simplifying summary to 7th grade reading level...')
        
        try:
            simplified_text = simplify_text(summarized_text)
            yield ('progress', f'Simplification completed: {summarized_text_length} -> {len(simplified_text)} characters')
            
            if len(simplified_text.strip()) == 0:
                error_msg = "ERROR: Simplified text is empty! Check API response."
                yield ('error', error_msg)
                raise ValueError(error_msg)
        except ValueError as e:
            error_msg = f"Error: {e}"
            yield ('error', error_msg)
            raise
        except Exception as e:
            error_msg = f"Error simplifying text: {e}"
            yield ('error', error_msg)
            raise
        
        # Clean up temporary PDF file if created from URL
        if temp_pdf_path and Path(temp_pdf_path).exists():
            try:
                Path(temp_pdf_path).unlink()
                yield ('progress', 'Cleaned up temporary PDF file')
            except Exception as e:
                warning_msg = f"Warning: Could not delete temporary PDF {temp_pdf_path}: {e}"
                yield ('progress', warning_msg)
        
        yield ('progress', 'Pipeline completed successfully!')
        # Yield both original and simplified text
        yield ('result', {'original': extracted_text, 'simplified': simplified_text})
        
    except KeyboardInterrupt:
        error_msg = "\nPipeline interrupted by user"
        yield ('error', error_msg)
        # Clean up temporary PDF on interrupt
        if temp_pdf_path and Path(temp_pdf_path).exists():
            try:
                Path(temp_pdf_path).unlink()
            except Exception:
                pass
        raise
    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        yield ('error', error_msg)
        # Clean up temporary PDF on error
        if temp_pdf_path and Path(temp_pdf_path).exists():
            try:
                Path(temp_pdf_path).unlink()
            except Exception:
                pass
        raise


def process_pipeline(input_source: str, output_path: str = None, yield_progress: bool = False) -> Union[Generator[Tuple[str, str], None, None], str]:
    """
    Process a URL or PDF file through the pipeline.
    
    Args:
        input_source: URL or path to PDF file
        output_path: Optional output file path (ignored if yield_progress is True)
        yield_progress: If True, yields (type, message) tuples for progress updates
        
    Yields:
        (type, message) tuples where type is 'progress', 'error', or 'result', message is the content
        
    Returns:
        Simplified text (only if yield_progress is False)
    """
    if yield_progress:
        # Return the generator directly
        return _process_pipeline_generator(input_source)
    else:
        # Consume the generator and print messages, return the result
        result_data = None
        for msg_type, message in _process_pipeline_generator(input_source):
            if msg_type == 'result':
                result_data = message
            elif msg_type == 'error':
                print(message, file=sys.stderr)
            else:
                print(message, file=sys.stderr)
        
        if result_data is None:
            raise Exception("Pipeline did not return a result")
        
        # Handle both dict (with original) and string (backward compatibility) results
        if isinstance(result_data, dict):
            simplified_text = result_data.get('simplified', '')
        else:
            simplified_text = result_data
        
        # Determine output path and save
        from urllib.parse import urlparse
        if output_path is None:
            if is_valid_url(input_source):
                # Generate filename from URL
                parsed = urlparse(input_source)
                domain = parsed.netloc.replace('.', '_').replace(':', '_')
                path_part = parsed.path.strip('/').replace('/', '_')[:50]
                if not path_part:
                    path_part = "page"
                filename = f"{domain}_{path_part}_simplified.txt"
                output_path = Path(filename)
            else:
                pdf_path_obj = Path(input_source)
                output_path = pdf_path_obj.parent / f"{pdf_path_obj.stem}_simplified.txt"
        else:
            output_path = Path(output_path)
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(simplified_text)
        print(f"Simplified text saved to: {output_path}", file=sys.stderr)
        
        return simplified_text


def main():
    """Main pipeline function."""
    parser = argparse.ArgumentParser(
        description="Simplify health documents to 7th grade reading level. Accepts PDF files or URLs."
    )
    parser.add_argument(
        "input_source",
        type=str,
        help="Path to PDF file or URL to process"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output file path (default: input_filename_simplified.txt)"
    )
    
    args = parser.parse_args()
    
    input_source = args.input_source
    output_path = args.output
    
    try:
        # Use the refactored pipeline function
        result = process_pipeline(input_source, output_path, yield_progress=False)
        # result will be the simplified text string when yield_progress=False
    except Exception:
        sys.exit(1)


if __name__ == "__main__":
    main()

