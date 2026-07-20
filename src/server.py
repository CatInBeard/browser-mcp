import logging
import urllib.parse
import pathlib
from fastmcp import FastMCP
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from playwright.async_api import async_playwright
import uvicorn

from soup import html_to_pug, links_extractor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp_server = FastMCP("browser-mcp")

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=[
            "mcp-protocol-version",
            "mcp-session-id",
            "Authorization",
            "Content-Type",
        ],
        expose_headers=["mcp-session-id"],
    )
]

app = mcp_server.http_app(middleware=middleware)

browser_state = {
    "playwright": None,
    "context": None,
    "page": None
}

UBLOCK_PATH = "/app/external/uBlock0.chromium"
USER_DATA_DIR = "/tmp/ublock-profile"

async def get_browser():
    if browser_state["playwright"] is None:
        browser_state["playwright"] = await async_playwright().start()

    if browser_state["context"] is None :
        browser_state["context"] = await browser_state["playwright"].chromium.launch_persistent_context(
            USER_DATA_DIR,
            headless=False,
            args=[
                f"--disable-extensions-except={UBLOCK_PATH}",
                f"--load-extension={UBLOCK_PATH}",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
            viewport={"width": 1024, "height": 768},
        )

    
    if browser_state["page"] is None or browser_state["page"].is_closed():
        browser_state["page"] = await browser_state["context"].new_page()
    return browser_state["page"]

@mcp_server.tool()
async def about() -> str:
    """You must call this tool on the first usage to get clear instructions on how it works."""


    text = """This MCP is a wrapper for Playwright. It functions as a single-tab browser.
    Core workflow:
    1. Navigate to a URL using the `navigate` tool.
    2. Extract content using one of the following methods:
       - `page_text_readability`: Best for articles/readable content (clean text).
       - `page_text_accessibility`: Best for complex apps or if readability fails (returns UI structure/labels).
       - `page_pug` or `page_html`: Use if you need to understand the structural layout (pug is cleaner).
    3. Use `selector_click` or `selector_fill` to interact with elements using Playwright-compatible selectors (e.g., CSS, XPath, role=button, text=...).

    Notes:
    - Use `current_url` to check the URL at any time.
    - If you are lost, use `page_text_readability` or `page_text_accessibility` to see where you are.
    - If interactions (click/fill) time out, it is likely the selector was incorrect or the element is not yet ready; try `page_text_accessibility` to find a more robust identifier.

    FAQ:
    Q: I want to search the web.
    A: Use `web_search` and then `page_text_readability` (or `page_text_accessibility`) to examine the results.

    Q: How do I find links?
    A: Use `page_links` for a simple list, or inspect the structure with `page_pug` / `page_text_accessibility`.
    """
    return text


@mcp_server.tool()
async def navigate(url: str) -> str:
    """Navigate to a URL. You must provide the full URL with protocol, for example: https://example.com"""
    page = await get_browser()
    await page.goto(url)

    realUrl = page.url

    return f"Navigated to {url}, real URL: {realUrl}"

@mcp_server.tool()
async def web_search(query: str) -> str:
    """Use the DuckDuckGo search engine and return links from search result."""
    page = await get_browser()
    await page.goto("https://duckduckgo.com/?q=" + urllib.parse.quote(query)  )

    page = await get_browser()
    
    await page.wait_for_timeout(3000)

    content = await page.content()

    links = links_extractor(content)

    return links

@mcp_server.tool()
async def page_html(limit: int = 8192) -> str:
    """Take HTML text from the page. We do not recommend using this due to its large output. Set a limit if you don't want to receive megabytes of data. For a first try, 8192 is recommended."""
    page = await get_browser()
    
    content = await page.content()
    return f"Page content: {content[:limit]}..."

@mcp_server.tool()
async def page_pug() -> str:
    """Take a Pug version of the HTML text from the page; it is more readable than plain HTML."""
    page = await get_browser()
    
    content = await page.content()

    return html_to_pug(content)

READABILITY_JS_PATH = pathlib.Path("/app/external/Readability.js")
READABILITY_JS_SOURCE = READABILITY_JS_PATH.read_text(encoding="utf-8")

@mcp_server.tool()
async def page_text_readability() -> str:
    """
    Return cleared text without any ads or other useless info. Uses readability.js; can break some sites. If a site is broken, try to use page_text_accessibility instead.
    """
    page = await get_browser()

    await page.wait_for_load_state("networkidle")

    await page.add_script_tag(content=READABILITY_JS_SOURCE)

    article = await page.evaluate(
        """
        () => {
            const doc = document.cloneNode(true);
            const reader = new Readability(doc);
            const res = reader.parse();
            if (!res) {
                return {
                    title: document.title || "",
                    text: document.body.innerText || ""
                };
            }
            return {
                title: res.title || document.title || "",
                text: res.textContent || ""
            };
        }
        """
    )

    title = article.get("title", "").strip()
    text = article.get("text", "").strip()

    lines = [line.strip() for line in text.split("\n") if line.strip()]
    cleaned_text = "\n\n".join(lines)

    if title:
        return f"{title}\n\n{cleaned_text}"
    return cleaned_text

@mcp_server.tool()
async def page_text_accessibility() -> str:
    """
    Return text based on accessibility (ARIA) snapshot: roles, names, descriptions, values.
    Safe for mixed types in snapshot. Falls back to body.innerText if snapshot is empty.
    """
    page = await get_browser()
    await page.wait_for_load_state("domcontentloaded")

    snapshot = await page.aria_snapshot()

    if not snapshot:
        body_text = (await page.inner_text("body")).strip()
        title = (await page.title()).strip() if await page.title() else ""
        if title:
            return f"{title}\n\n{body_text}"
        return body_text

    def walk(node, level=0):
        lines = []

        if isinstance(node, str):
            indent = "  " * level
            lines.append(indent + node)
            return lines

        if not isinstance(node, dict):
            if isinstance(node, list):
                for child in node:
                    lines.extend(walk(child, level))
            return lines

        role = node.get("role") or ""
        name = node.get("name") or ""
        description = node.get("description") or ""
        value = node.get("value") or ""

        parts = []
        if role:
            parts.append(f"роль: {role}")
        if name:
            parts.append(f"имя: {name}")
        if description:
            parts.append(f"описание: {description}")
        if value:
            parts.append(f"значение: {value}")

        if parts:
            indent = "  " * level
            lines.append(indent + " | ".join(parts))

        children = node.get("children") or []
        for child in children:
            lines.extend(walk(child, level + 1))

        return lines

    lines = walk(snapshot)
    cleaned_lines = [line.strip() for line in lines if line.strip()]
    text = "\n".join(cleaned_lines)

    title = (await page.title()).strip() if await page.title() else ""
    if title:
        return f"{title}\n\n{text}"
    return text

@mcp_server.tool()
async def selector_click(selector: str) -> str:
    """
    Click on an element matching a Playwright selector.
    selector: Playwright-compatible selector (CSS, text=..., xpath=..., role=...)
    """
    page = await get_browser()

    await page.click(selector)

    return f"Clicked on element matching selector: {selector}"

@mcp_server.tool()
async def selector_fill(selector: str, text: str) -> str:
    """
    Fill text into an element matching a Playwright selector.

    selector: Playwright-compatible selector (CSS, text=..., xpath=..., role=...)
    text: What you want to write in an input/textarea/etc.
    """
    page = await get_browser()

    await page.locator(selector).fill(text)

    return f"Filled '{text}' into element matching selector: {selector}"

@mcp_server.tool()
async def current_url() -> str:
    """
    Get the URL of the current page.
    """
    page = await get_browser()

    return page.url

@mcp_server.tool()
async def page_links() -> str:
    """
    Return a list of links on the current webpage.
    """
    page = await get_browser()
    
    content = await page.content()

    links = links_extractor(content)

    return links


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
