# Health Literacy Pipeline

A Python pipeline that simplifies complex health documents into plain language suitable for a 7th grade reading level using OpenAI's API. Features both a command-line interface and a modern web UI.

## Features

- **Web UI**: Beautiful, modern single-page interface with real-time progress tracking
- **Dual Display**: Side-by-side view of original and simplified text
- **Multiple Input Sources**: Process PDF files or web URLs
- **Smart Processing Pipeline**:
  - Extracts text from PDF files or converts web pages to PDF using browser automation
  - Cleans extracted text to remove navigation, ads, and irrelevant content
  - Summarizes text to extract core ideas (reduces token usage and processing time)
  - Simplifies complex medical/health terminology to 7th grade reading level
- **Preserves Structure**: Maintains headings, paragraphs, and formatting
- **Progress Tracking**: Real-time progress updates with visual water-fill animation
- **Header Detection**: Automatically identifies and styles headers in the simplified output

## Setup

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Install Playwright browsers** (required for URL to PDF conversion):
```bash
playwright install chromium
```
   Note: This only needs to be run once after installing the Python package.

3. **Set up your OpenAI API key:**
   - Create a `.env` file in the project root
   - Add your OpenAI API key to `.env`:
     ```
     OPENAI_API_KEY=your_api_key_here
     OPENAI_MODEL=gpt-5-mini
     ```
   - Get your API key from: https://platform.openai.com/api-keys

## Usage

### Web UI (Recommended)

Start the web server:

```bash
python -m uvicorn app:app --reload
```

Then open your browser to `http://localhost:8000`

The web UI provides:
- Simple URL input in a circular interface
- Real-time progress tracking with water-fill animation
- Side-by-side display of original and simplified text
- Automatic header detection and styling

### Command Line Interface

#### Processing a PDF File

```bash
python main.py path/to/your/document.pdf
```

The simplified output will be saved as `document_simplified.txt` in the same directory as the input file.

#### Processing a URL

```bash
python main.py https://example.com/health-article
```

The pipeline will:
1. Convert the web page to a PDF
2. Extract and clean the text
3. Summarize to extract core ideas
4. Simplify to 7th grade reading level
5. Save the simplified output to a `.txt` file

The output filename will be generated from the URL (e.g., `example_com_health-article_simplified.txt`).

#### Custom Output Path

You can specify a custom output path with the `-o` or `--output` flag:

```bash
python main.py input.pdf -o simplified_output.txt
python main.py https://example.com/article -o my_simplified_text.txt
```

## How It Works

The pipeline follows these steps:

1. **Input Detection**: Automatically detects if the input is a URL or PDF file path
2. **URL Conversion** (if URL provided): Uses Playwright to render the web page and convert it to PDF
3. **PDF Extraction**: Extracts text from the PDF while preserving structure (paragraphs, headings)
4. **Text Cleaning** (for URLs): Removes navigation elements, ads, and irrelevant content using OpenAI
5. **Text Summarization**: Summarizes the cleaned text to extract core ideas (targets 20-30% of original length)
6. **Text Simplification**: Uses OpenAI API to simplify the summary to 7th grade reading level
7. **Output**: Saves the simplified text to a `.txt` file or displays in the web UI

### Processing Details

- **Parallel Processing**: OpenAI API calls are parallelized for faster processing
- **Chunking**: Large texts are automatically split into manageable chunks
- **Retry Logic**: Automatic retry (up to 3 times) if API calls return empty results
- **Error Handling**: Comprehensive error handling with detailed progress messages

## Project Structure

```
hlpipeline/
├── app.py                 # FastAPI web application
├── main.py                # Main pipeline logic and CLI entry point
├── pdf_extractor.py       # PDF text extraction
├── url_to_pdf.py          # URL to PDF conversion using Playwright
├── text_clearner.py       # Text cleaning for web content
├── text_summarizer.py     # Text summarization to extract core ideas
├── text_simplifier.py     # Text simplification to 7th grade level
├── templates/
│   └── index.html         # Web UI frontend
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4o-mini
```

### Model Selection

The default model is `gpt-4o-mini` (cost-effective and fast). You can change it in `.env`:

- `gpt-4o-mini` - Recommended: Fast and cost-effective
- `gpt-4` - More capable but slower and more expensive
- `gpt-3.5-turbo` - Fast but less capable

## Web UI Features

- **Circular Input Interface**: Clean, modern design with water-fill progress animation
- **Real-time Progress**: Live updates as the pipeline processes
- **Side-by-Side Comparison**: View original and simplified text simultaneously
- **Header Styling**: Automatic detection and bold styling of headers
- **Responsive Design**: Works on desktop and mobile devices
- **Full-Width Display**: Wide text fields for comfortable reading

## Performance

- **Typical Processing Time**: 30-60 seconds for most documents
- **Optimizations**:
  - Parallel API calls for faster processing
  - Summarization step reduces token usage
  - Optimized Playwright settings for faster page loading
  - Resource blocking (images, fonts) for faster URL conversion

## Requirements

- Python 3.8+
- OpenAI API key
- Playwright (for URL processing)

## License

See LICENSE file for details.
