# Browser MCP Server

This project provides an MCP (Model Context Protocol) server for controlling a browser via Playwright, enabling LLMs to interact with web pages directly.

## Purpose
The Browser MCP Server allows an LLM to navigate the web, extract content, and perform interactions (click, fill) as if it were a user. It simplifies web automation tasks for AI agents by providing clean abstractions over the browser.

## Features
- **Headless Browser Automation:** Uses Playwright to drive a Chromium browser instance.
- **Content Extraction:**
  - `page_text_readability`: Extracts clean, readable text (removes ads/clutter).
  - `page_text_accessibility`: Uses ARIA snapshot for robust UI understanding.
  - `page_pug`: Converts HTML to a readable Pug structural layout.
  - `page_links`: Extracts all links from the page.
- **Interactions:** Supports clicking elements and filling inputs using Playwright selectors (CSS, Role, Text, etc.).
- **Web Search:** Built-in integration with DuckDuckGo for searching the web.
- **Ad Blocking:** Pre-configured with uBlock (via Chromium extension loading).

## Usage (Docker Hub)
You can pull and run the pre-built image directly from Docker Hub (amd64 and arm64):

```bash
docker run -p 8000:8000 --rm catinbeard/browser-mcp:latest
```

## Using Docker Compose
1. Start the server:
   ```bash
   docker-compose up -d
   ```
2. The server will be available at `http://localhost:8000`.

## MCP Configuration for LMStudio
Add the following to your MCP configuration:

```json
{
  "mcpServers": {
    "browser": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
