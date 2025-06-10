import os
import asyncio
import json
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Union, Any, Literal, Callable
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import httpx
from bs4 import BeautifulSoup, Comment
import re
from urllib.parse import urljoin, urlparse

try:
    from mcp.server.fastmcp import FastMCP, Context
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    # Create placeholder classes to avoid errors when MCP is not available
    class FastMCP:
        def __init__(self, *args, **kwargs):
            raise ImportError("MCP functionality is not available. Install mcp-server package to use it.")
    
    class Context:
        pass


# --- Client Models ---

class GoogleSearchRequest(BaseModel):
    q: str = Field(..., description="Search query string")
    gl: str = Field(..., description="Region code for search results in ISO 3166-1 alpha-2 format (e.g., 'us')")
    hl: str = Field(..., description="Language code for search results in ISO 639-1 format (e.g., 'en')")
    num: Optional[int] = Field(None, description="Number of results to return (default: 10)")
    page: Optional[int] = Field(None, description="Page number of results to return (default: 1)")
    tbs: Optional[str] = Field(None, description="Time-based search filter ('qdr:h' for past hour, 'qdr:d' for past day, 'qdr:w' for past week, 'qdr:m' for past month, 'qdr:y' for past year)")
    location: Optional[str] = Field(None, description="Optional location for search results (e.g., 'SoHo, New York, United States', 'California, United States')")
    autocorrect: Optional[bool] = Field(None, description="Whether to autocorrect spelling in query")


class ScrapeRequest(BaseModel):
    url: str = Field(..., description="The URL of the webpage to scrape.")
    includeMarkdown: Optional[bool] = Field(None, description="Whether to include markdown content.")


class BatchScrapeRequest(BaseModel):
    urls: List[str] = Field(..., description="List of URLs to scrape in parallel.")
    includeMarkdown: Optional[bool] = Field(None, description="Whether to include markdown content.")


class Link(BaseModel):
    """Represents a link extracted from a webpage."""
    text: str = Field(..., description="The visible text of the link")
    url: str = Field(..., description="The URL the link points to")
    is_external: bool = Field(..., description="Whether the link points to an external domain")


class MetaTag(BaseModel):
    name: Optional[str] = None
    property: Optional[str] = None
    content: Optional[str] = None


class JSONLD(BaseModel):
    raw: str
    parsed: Any


class ScrapedContent(BaseModel):
    """A section of content from the scraped page."""
    type: str = Field(..., description="Type of content (heading, paragraph, list, etc)")
    text: str = Field(..., description="The actual text content")
    level: Optional[int] = Field(None, description="For headings, the level (1-6)")


class ScrapeResult(BaseModel):
    url: str
    timestamp: str
    title: Optional[str] = None
    main_content: List[ScrapedContent] = Field([], description="The main visible content of the page in structured format")
    links: List[Link] = Field([], description="Important links extracted from the page")
    meta_description: Optional[str] = Field(None, description="Meta description of the page if available")
    meta_tags: List[MetaTag] = []
    json_ld: List[JSONLD] = []
    error: Optional[str] = None


# --- Client Implementation ---

class SerperScraperClient:
    def __init__(self, serper_api_key: Optional[str] = None):
        self.serper_api_key = serper_api_key
        self.serper_api_url = "https://google.serper.dev/search"
        self.headers = {
            "X-API-KEY": serper_api_key,
            "Content-Type": "application/json"
        } if serper_api_key else {"Content-Type": "application/json"}

    async def google_search(self, request: GoogleSearchRequest) -> Dict:
        """Perform a Google search using the Serper API."""
        if not self.serper_api_key:
            raise ValueError("Serper API key is required for search operations")

        payload = request.model_dump(exclude_none=True)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.serper_api_url,
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()

    async def _extract_meta_tags(self, soup: BeautifulSoup) -> List[MetaTag]:
        """Extract meta tags from the HTML soup."""
        meta_tags = []
        for tag in soup.find_all("meta"):
            meta_tag = {}
            if tag.get("name"):
                meta_tag["name"] = tag.get("name")
            if tag.get("property"):
                meta_tag["property"] = tag.get("property")
            if tag.get("content"):
                meta_tag["content"] = tag.get("content")
            
            if meta_tag:  # Only add if we found at least one attribute
                meta_tags.append(MetaTag(**meta_tag))
        return meta_tags

    async def _extract_json_ld(self, html: str) -> List[JSONLD]:
        """Extract JSON-LD metadata from the HTML."""
        json_ld_list = []
        pattern = re.compile(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.DOTALL)
        for match in pattern.finditer(html):
            json_str = match.group(1).strip()
            try:
                parsed = json.loads(json_str)
                json_ld_list.append(JSONLD(raw=json_str, parsed=parsed))
            except json.JSONDecodeError:
                # Skip invalid JSON
                pass
        return json_ld_list
    
    def _is_visible_element(self, element) -> bool:
        """Determine if an element would be visible to users."""
        if element.name in ['script', 'style', 'meta', 'noscript', 'head']:
            return False
            
        # Check for hidden elements
        style = element.get('style', '')
        if 'display:none' in style or 'visibility:hidden' in style:
            return False
            
        # Check for comment nodes
        if isinstance(element, Comment):
            return False
            
        # Skip empty elements
        if not element.get_text(strip=True):
            return False
            
        return True
        
    def _remove_duplicate_content(self, content_list: List[ScrapedContent]) -> List[ScrapedContent]:
        """Remove duplicate or near-duplicate content items."""
        unique_content = []
        seen_texts = set()
        
        for content in content_list:
            # Normalize text for comparison
            normalized_text = re.sub(r'\s+', ' ', content.text).strip().lower()
            
            # Skip if too short (likely not useful)
            if len(normalized_text) < 5:
                continue
                
            # Skip if duplicate or near-duplicate
            if normalized_text in seen_texts:
                continue
                
            # Check for near-duplicates (text contained within other texts)
            is_duplicate = False
            for seen_text in seen_texts:
                # If this text is just a small part of an existing text, skip it
                if len(normalized_text) < 50 and normalized_text in seen_text:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                seen_texts.add(normalized_text)
                unique_content.append(content)
                
        return unique_content
        
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[Link]:
        """Extract important links from the page."""
        links = []
        base_domain = urlparse(base_url).netloc
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag.get('href', '').strip()
            if not href or href.startswith('#') or href.startswith('javascript:'):
                continue
                
            # Get the link text and clean it
            link_text = a_tag.get_text(strip=True)
            if not link_text:
                continue
                
            # Normalize the URL
            full_url = urljoin(base_url, href)
            
            # Check if external link
            link_domain = urlparse(full_url).netloc
            is_external = link_domain != base_domain
            
            links.append(Link(
                text=link_text,
                url=full_url,
                is_external=is_external
            ))
            
        # Remove duplicates (same URL and text)
        unique_links = []
        seen_urls = set()
        
        for link in links:
            key = (link.url, link.text)
            if key not in seen_urls:
                seen_urls.add(key)
                unique_links.append(link)
                
        return unique_links
        
    def _extract_main_content(self, soup: BeautifulSoup) -> List[ScrapedContent]:
        """Extract main content in a structured way."""
        content_items = []
        
        # Process headings
        for level in range(1, 7):
            for heading in soup.find_all(f'h{level}'):
                if self._is_visible_element(heading):
                    text = heading.get_text(strip=True)
                    if text:
                        content_items.append(ScrapedContent(
                            type='heading',
                            text=text,
                            level=level
                        ))
        
        # Process paragraphs
        for p in soup.find_all('p'):
            if self._is_visible_element(p):
                text = p.get_text(strip=True)
                if text:
                    content_items.append(ScrapedContent(
                        type='paragraph',
                        text=text
                    ))
        
        # Process lists
        for list_tag in soup.find_all(['ul', 'ol']):
            if self._is_visible_element(list_tag):
                list_type = 'unordered_list' if list_tag.name == 'ul' else 'ordered_list'
                
                # Get list items
                list_items = []
                for li in list_tag.find_all('li', recursive=False):
                    item_text = li.get_text(strip=True)
                    if item_text:
                        list_items.append(item_text)
                
                if list_items:
                    content_items.append(ScrapedContent(
                        type=list_type,
                        text='\n'.join(f"• {item}" for item in list_items)
                    ))
        
        # Look for content in divs only if we don't have enough content yet
        # This helps avoid getting too much boilerplate
        if len(content_items) < 5:
            for div in soup.find_all('div'):
                if self._is_visible_element(div) and not div.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol']):
                    text = div.get_text(strip=True)
                    if text and len(text) > 40:  # Only get substantial text
                        content_items.append(ScrapedContent(
                            type='content_block',
                            text=text
                        ))
        
        # Remove duplicates and noise
        return self._remove_duplicate_content(content_items)

    async def _scrape_single_url(self, url: str, include_markdown: bool = False) -> ScrapeResult:
        """Scrape a single URL and return structured data focused on visible content."""
        # Using datetime.now(timezone.utc) instead of deprecated datetime.utcnow()
        timestamp = datetime.now(timezone.utc).isoformat()
        
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                html_content = response.text

            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove invisible elements
            for invisible in soup.find_all(['script', 'style', 'meta', 'noscript']):
                invisible.extract()
            
            # Fix for deprecated 'text' argument in find_all
            for comment in soup.find_all(string=lambda s: isinstance(s, Comment)):
                comment.extract()
                
            # Basic page information
            title = soup.title.string if soup.title else None
            meta_tags = await self._extract_meta_tags(soup)
            json_ld = await self._extract_json_ld(html_content)
            
            # Get meta description
            meta_description = None
            for tag in meta_tags:
                if (tag.name == 'description' or tag.property == 'og:description') and tag.content:
                    meta_description = tag.content
                    break
            
            # Extract main content and links
            main_content = self._extract_main_content(soup)
            links = self._extract_links(soup, url)

            return ScrapeResult(
                url=url,
                timestamp=timestamp,
                title=title,
                main_content=main_content,
                links=links,
                meta_description=meta_description,
                meta_tags=meta_tags, 
                json_ld=json_ld
            )
        except Exception as e:
            return ScrapeResult(
                url=url,
                timestamp=timestamp,
                main_content=[],
                links=[],
                meta_tags=[],
                json_ld=[],
                error=str(e)
            )

    async def scrape(self, request: ScrapeRequest) -> ScrapeResult:
        """Scrape a single URL and return structured data."""
        return await self._scrape_single_url(request.url, request.includeMarkdown or False)

    async def batch_scrape(self, request: BatchScrapeRequest) -> List[ScrapeResult]:
        """Scrape multiple URLs in parallel and return a list of results."""
        tasks = []
        for url in request.urls:
            tasks.append(self._scrape_single_url(url, request.includeMarkdown or False))
            
        return await asyncio.gather(*tasks)


# --- MCP Server Implementation ---

@asynccontextmanager
async def server_lifespan(server: FastMCP):
    """Initialize SerperScraperClient on server startup."""
    api_key = os.getenv("SERPER_API_KEY")
    client = SerperScraperClient(serper_api_key=api_key)
    
    try:
        yield {"client": client}
    finally:
        # No cleanup needed for this client
        pass


# Function to create the MCP server
def create_mcp_server() -> Optional[FastMCP]:
    """Create and configure the MCP server for SerperScraper.
    
    Returns:
        Optional[FastMCP]: Configured MCP server or None if MCP is not available
    """
    if not MCP_AVAILABLE:
        return None
        
    # Create the FastMCP server
    mcp = FastMCP("SerperScraperMCP", lifespan=server_lifespan)
    
    # Register tools
    @mcp.tool()
    async def google_search(request: GoogleSearchRequest, ctx: Context) -> Dict:
        """Perform a Google search using the Serper API."""
        if "client" not in ctx.request_context.lifespan_context:
            raise ValueError("SerperScraperClient not properly initialized")
            
        client = ctx.request_context.lifespan_context["client"]
        try:
            return await client.google_search(request)
        except Exception as e:
            ctx.error(f"Error during Google search: {str(e)}")
            raise ValueError(f"Failed to perform Google search: {str(e)}")

    @mcp.tool()
    async def scrape(request: ScrapeRequest, ctx: Context) -> ScrapeResult:
        """Scrape a single URL and return structured data focused on visible content."""
        if "client" not in ctx.request_context.lifespan_context:
            raise ValueError("SerperScraperClient not properly initialized")
            
        client = ctx.request_context.lifespan_context["client"]
        try:
            await ctx.info(f"Scraping URL: {request.url}")
            return await client.scrape(request)
        except Exception as e:
            ctx.error(f"Error during web scraping: {str(e)}")
            raise ValueError(f"Failed to scrape URL: {str(e)}")

    @mcp.tool()
    async def batch_scrape(request: BatchScrapeRequest, ctx: Context) -> List[ScrapeResult]:
        """Scrape multiple URLs in parallel and return a list of results with focused content."""
        if "client" not in ctx.request_context.lifespan_context:
            raise ValueError("SerperScraperClient not properly initialized")
            
        client = ctx.request_context.lifespan_context["client"]
        try:
            total_urls = len(request.urls)
            await ctx.info(f"Starting batch scrape of {total_urls} URLs with optimized content extraction")
            
            # Start the scraping operation
            results = await client.batch_scrape(request)
            
            # Count successful and failed results
            success_count = sum(1 for r in results if not r.error)
            error_count = sum(1 for r in results if r.error)
            
            await ctx.info(f"Completed batch scrape: {success_count} successful, {error_count} failed")
            return results
        except Exception as e:
            ctx.error(f"Error during batch web scraping: {str(e)}")
            raise ValueError(f"Failed to execute batch scrape: {str(e)}")

    return mcp


# Global MCP instance for use when running as a script
_mcp_instance = None

def main():
    """Run the MCP server when this module is executed as a script."""
    global _mcp_instance
    if not MCP_AVAILABLE:
        print("ERROR: MCP functionality is not available. Install mcp-server package to use it.")
        return
        
    _mcp_instance = create_mcp_server()
    if _mcp_instance:
        _mcp_instance.run()
    

if __name__ == "__main__":
    main()