# Health Literacy Pipeline

A Python pipeline that simplifies complex health documents into plain language suitable for a 7th grade reading level using OpenAI's API.

## Features

- Extracts text from PDF files or web URLs while preserving document structure
- Converts web pages to PDF using browser automation (handles JavaScript and dynamic content)
- Simplifies complex medical/health terminology to 7th grade reading level
- Preserves headings, paragraphs, and formatting
- Outputs simplified text to `.txt` files

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Install Playwright browsers (required for URL to PDF conversion):
```bash
playwright install chromium
```
   Note: This only needs to be run once after installing the Python package.

3. Set up your OpenAI API key:
   - Copy `.env.example` to `.env`
   - Add your OpenAI API key to `.env`:
     ```
     OPENAI_API_KEY=your_api_key_here
     ```
   - Get your API key from: https://platform.openai.com/api-keys

## Usage

### Processing a PDF File

Run the pipeline with a PDF file:

```bash
python main.py path/to/your/document.pdf
```

The simplified output will be saved as `document_simplified.txt` in the same directory as the input file.

### Processing a URL

You can also process web pages by providing a URL:

```bash
python main.py https://example.com/health-article
```

The pipeline will:
1. Convert the web page to a PDF
2. Extract and simplify the text
3. Save the simplified output to a `.txt` file

The output filename will be generated from the URL (e.g., `example_com_health-article_simplified.txt`).

### Custom Output Path

You can specify a custom output path with the `-o` or `--output` flag:

```bash
python main.py input.pdf -o simplified_output.txt
python main.py https://example.com/article -o my_simplified_text.txt
```

## How It Works

1. **Input Detection**: The pipeline automatically detects if the input is a URL or PDF file path
2. **URL Conversion** (if URL provided): Uses Playwright to render the web page and convert it to PDF
3. **PDF Extraction**: Extracts text from the PDF while preserving structure (paragraphs, headings)
4. **Text Simplification**: Uses OpenAI API to simplify the text to 7th grade reading level
5. **Output**: Saves the simplified text to a `.txt` file

## Configuration

You can customize the OpenAI model in `.env`:
```
OPENAI_MODEL=gpt-4
```

Supported models: `gpt-4`, `gpt-3.5-turbo`, etc.

