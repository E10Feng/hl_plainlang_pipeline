"""
URL to PDF conversion module using Playwright.
Converts web pages to PDF files, handling JavaScript and dynamic content.
"""

import sys
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import tempfile


def is_valid_url(url: str) -> bool:
    """
    Check if a string is a valid URL.
    
    Args:
        url: String to validate
        
    Returns:
        True if valid URL, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme in ['http', 'https'], result.netloc])
    except Exception:
        return False


def url_to_pdf(url: str, output_path: str = None, timeout: int = 15000) -> str:
    """
    Convert a URL to a PDF file using Playwright.
    Optimized for speed with faster load strategies.
    
    Args:
        url: URL of the webpage to convert
        output_path: Optional path for output PDF. If None, creates temp file.
        timeout: Page load timeout in milliseconds (default: 15000)
        
    Returns:
        Path to the created PDF file
        
    Raises:
        ValueError: If URL is invalid
        Exception: If PDF conversion fails
    """
    # Validate URL
    if not is_valid_url(url):
        raise ValueError(f"Invalid URL: {url}. URL must start with http:// or https://")
    
    # Determine output path
    if output_path is None:
        # Create temporary file
        temp_dir = tempfile.gettempdir()
        # Generate filename from URL
        parsed = urlparse(url)
        domain = parsed.netloc.replace('.', '_').replace(':', '_')
        path_part = parsed.path.strip('/').replace('/', '_')[:50]  # Limit length
        if not path_part:
            path_part = "page"
        filename = f"{domain}_{path_part}.pdf"
        output_path = str(Path(temp_dir) / filename)
    
    output_path_obj = Path(output_path)
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with sync_playwright() as p:
            # Launch browser with optimized settings for speed
            print(f"Launching browser...", file=sys.stderr)
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-gpu',
                    '--disable-extensions',
                    '--disable-background-networking',
                    '--disable-background-timer-throttling',
                    '--disable-renderer-backgrounding',
                    '--disable-backgrounding-occluded-windows',
                ]
            )
            
            try:
                # Create new page with optimized context
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    ignore_https_errors=True,
                    java_script_enabled=True,
                )
                page = context.new_page()
                
                # Block unnecessary resources for faster loading (images, fonts, media)
                def handle_route(route):
                    resource_type = route.request.resource_type
                    if resource_type in ["image", "font", "media", "websocket"]:
                        route.abort()
                    else:
                        route.continue_()
                
                page.route("**/*", handle_route)
                
                # Navigate to URL with faster wait strategy
                print(f"Loading URL: {url}", file=sys.stderr)
                # Use domcontentloaded instead of networkidle for much faster loading
                # This waits for DOM to be ready, not all network activity to stop
                page.goto(url, wait_until="domcontentloaded", timeout=timeout)
                
                # Reduced wait time for dynamic content (from 2s to 0.5s)
                # Most content is ready by domcontentloaded, minimal JS needed
                page.wait_for_timeout(500)  # Wait 0.5 seconds for critical JS to finish
                
                # Generate PDF
                print(f"Generating PDF...", file=sys.stderr)
                page.pdf(
                    path=output_path,
                    format="A4",
                    print_background=True,
                    margin={
                        "top": "1cm",
                        "right": "1cm",
                        "bottom": "1cm",
                        "left": "1cm"
                    }
                )
                
                print(f"PDF saved to: {output_path}", file=sys.stderr)
                
            finally:
                context.close()
                browser.close()
        
        return output_path
        
    except PlaywrightTimeoutError as e:
        raise Exception(f"Timeout while loading URL {url}: {e}")
    except Exception as e:
        raise Exception(f"Error converting URL to PDF: {e}")

