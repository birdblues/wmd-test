# Web to Markdown Converter
# A modern, modular Python implementation

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Protocol, Union
from pathlib import Path
from urllib.parse import urljoin, urlparse
import asyncio
import aiohttp
from bs4 import BeautifulSoup, Tag, NavigableString
import logging
from enum import Enum
import json
import re
from datetime import datetime
import hashlib
from contextlib import asynccontextmanager
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== Configuration Module =====
@dataclass
class ConverterConfig:
    """Configuration for the converter"""
    # Image handling
    download_images: bool = True
    image_folder: Path = field(default_factory=lambda: Path("images"))
    max_image_size: int = 10 * 1024 * 1024  # 10MB
    
    # Conversion options
    include_links: bool = True
    remove_navigation: bool = False
    preserve_whitespace: bool = False
    code_block_style: str = "```"
    heading_style: str = "atx"  # atx (#) or setext (underline)
    
    # Network settings
    timeout: int = 30
    max_retries: int = 3
    user_agent: str = "Mozilla/5.0 (compatible; WebToMarkdown/1.0)"
    
    # Output settings
    line_width: int = 80
    preserve_empty_lines: bool = False
    
    @classmethod
    def from_json(cls, path: Union[str, Path]) -> "ConverterConfig":
        """Load configuration from JSON file"""
        with open(path, 'r') as f:
            return cls(**json.load(f))

# ===== Type Definitions =====
class ElementHandler(Protocol):
    """Protocol for element handlers"""
    def can_handle(self, element: Tag) -> bool:
        """Check if this handler can process the element"""
        ...
    
    def handle(self, element: Tag, context: Dict[str, Any]) -> str:
        """Convert element to markdown"""
        ...

@dataclass
class ConversionContext:
    """Context passed during conversion"""
    base_url: str
    config: ConverterConfig
    list_stack: List[str] = field(default_factory=list)
    in_pre: bool = False
    in_table: bool = False
    
# ===== Utility Module =====
class TextUtils:
    """Text processing utilities"""
    
    @staticmethod
    def clean_text(text: str, preserve_whitespace: bool = False) -> str:
        """Clean and normalize text"""
        if preserve_whitespace:
            return text
        
        # Replace multiple whitespaces with single space
        text = re.sub(r'\s+', ' ', text)
        # Remove leading/trailing whitespace
        text = text.strip()
        return text
    
    @staticmethod
    def escape_markdown(text: str) -> str:
        """Escape special markdown characters"""
        chars_to_escape = r'*_[](){}#+-!`\\<>'
        pattern = '([' + re.escape(chars_to_escape) + '])'
        return re.sub(pattern, r'\\\1', text)
    
    @staticmethod
    def wrap_text(text: str, width: int = 80) -> str:
        """Wrap text to specified width"""
        if width <= 0:
            return text
        
        lines = []
        for paragraph in text.split('\n'):
            if len(paragraph) <= width:
                lines.append(paragraph)
            else:
                words = paragraph.split()
                current_line = []
                current_length = 0
                
                for word in words:
                    word_length = len(word)
                    if current_length + word_length + len(current_line) > width:
                        lines.append(' '.join(current_line))
                        current_line = [word]
                        current_length = word_length
                    else:
                        current_line.append(word)
                        current_length += word_length
                
                if current_line:
                    lines.append(' '.join(current_line))
        
        return '\n'.join(lines)

# ===== Image Handler Module =====
class ImageHandler:
    """Handle image downloading and processing"""
    
    def __init__(self, config: ConverterConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self.downloaded_images: Dict[str, str] = {}
        

    
    async def download_image(self, url: str, base_url: str) -> Optional[str]:
        """Download image and return local path"""
        if not self.config.download_images:
            return url
        
        # Convert relative URL to absolute
        absolute_url = urljoin(base_url, url)
        
        # Check if already downloaded
        if absolute_url in self.downloaded_images:
            return self.downloaded_images[absolute_url]
        
        try:
            if not self.session:
                self.session = aiohttp.ClientSession(
                    headers={'User-Agent': self.config.user_agent},
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout)
                )
            
            async with self.session.get(absolute_url) as response:
                if response.status != 200:
                    logger.warning(f"Failed to download image: {absolute_url}")
                    return url
                
                content = await response.read()
                if len(content) > self.config.max_image_size:
                    logger.warning(f"Image too large: {absolute_url}")
                    return url
                
                # Generate filename based on URL hash
                filename = self._generate_filename(absolute_url, response.headers)
                filepath = self.config.image_folder / filename
                
                # Ensure directory exists
                filepath.parent.mkdir(parents=True, exist_ok=True)
                
                # Save image
                with open(filepath, 'wb') as f:
                    f.write(content)
                
                self.downloaded_images[absolute_url] = str(filepath)
                logger.info(f"Downloaded image: {absolute_url} -> {filepath}")
                return str(filepath)
                
        except Exception as e:
            logger.error(f"Error downloading image {absolute_url}: {e}")
            return url
    
    async def close(self):
        """Close the session"""
        if self.session:
            await self.session.close()
            self.session = None
    
    def _generate_filename(self, url: str, headers: Dict[str, str]) -> str:
        """Generate unique filename for image"""
        # Try to get extension from URL
        parsed = urlparse(url)
        path = Path(parsed.path)
        ext = path.suffix or '.jpg'
        
        # Generate hash-based name
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        # timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        return f"{url_hash}{ext}"

# ===== Element Handlers =====
class BaseElementHandler(ABC):
    """Base class for element handlers"""
    
    @abstractmethod
    def can_handle(self, element: Tag) -> bool:
        pass
    
    @abstractmethod
    def handle(self, element: Tag, context: ConversionContext) -> str:
        pass
    
    def get_text_content(self, element: Tag, context: ConversionContext) -> str:
        """Extract text content from element"""
        text = element.get_text()
        return TextUtils.clean_text(text, context.config.preserve_whitespace)

class HeadingHandler(BaseElementHandler):
    """Handle h1-h6 elements"""
    
    def can_handle(self, element: Tag) -> bool:
        return element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']
    
    def handle(self, element: Tag, context: ConversionContext) -> str:
        level = int(element.name[1])
        text = self.get_text_content(element, context)
        
        if context.config.heading_style == 'atx':
            return f"{'#' * level} {text}\n\n"
        else:  # setext style (only for h1 and h2)
            if level == 1:
                return f"{text}\n{'=' * len(text)}\n\n"
            elif level == 2:
                return f"{text}\n{'-' * len(text)}\n\n"
            else:
                return f"{'#' * level} {text}\n\n"

class ParagraphHandler(BaseElementHandler):
    """Handle paragraph elements"""
    
    def __init__(self):
        self.image_handler: Optional[ImageHandler] = None
    
    def set_image_handler(self, handler: ImageHandler):
        """Set image handler for downloading images"""
        self.image_handler = handler
    
    def can_handle(self, element: Tag) -> bool:
        return element.name == 'p'
    
    async def handle_async(self, element: Tag, context: ConversionContext) -> str:
        """Async version of handle"""
        text = await self.process_inline_elements(element, context)
        if text.strip():
            return f"{text}\n\n"
        return ""
    
    def handle(self, element: Tag, context: ConversionContext) -> str:
        """Sync wrapper for compatibility"""
        return asyncio.run(self.handle_async(element, context))
    
    async def process_inline_elements(self, element: Tag, context: ConversionContext) -> str:
        """Process inline elements within paragraph"""
        result = []
        
        for child in element.children:
            if isinstance(child, NavigableString):
                result.append(TextUtils.clean_text(str(child), context.config.preserve_whitespace))
            elif isinstance(child, Tag):
                if child.name == 'strong' or child.name == 'b':
                    result.append(f"**{self.get_text_content(child, context)}**")
                elif child.name == 'em' or child.name == 'i':
                    result.append(f"*{self.get_text_content(child, context)}*")
                elif child.name == 'code':
                    result.append(f"`{self.get_text_content(child, context)}`")
                elif child.name == 'a' and context.config.include_links:
                    href = child.get('href', '#')
                    text = self.get_text_content(child, context)
                    result.append(f"[{text}]({href})")
                elif child.name == 'img':
                    alt = child.get('alt', '')
                    src = child.get('src', '')
                    
                    # Download image if handler is available
                    if self.image_handler and context.config.download_images and src:
                        downloaded_path = await self.image_handler.download_image(src, context.base_url)
                        result.append(f"![{alt}]({downloaded_path})")
                    else:
                        result.append(f"![{alt}]({src})")
                elif child.name == 'br':
                    result.append("  \n")
                else:
                    result.append(await self.process_inline_elements(child, context))
        
        return ''.join(result)

class ListHandler(BaseElementHandler):
    """Handle ul and ol elements"""
    
    def __init__(self):
        self.image_handler: Optional[ImageHandler] = None
    
    def set_image_handler(self, handler: ImageHandler):
        """Set image handler for downloading images"""
        self.image_handler = handler
    
    def can_handle(self, element: Tag) -> bool:
        return element.name in ['ul', 'ol']
    
    async def handle_async(self, element: Tag, context: ConversionContext) -> str:
        """Async version of handle"""
        list_type = 'ordered' if element.name == 'ol' else 'unordered'
        context.list_stack.append(list_type)
        
        result = []
        for i, li in enumerate(element.find_all('li', recursive=False)):
            indent = '  ' * (len(context.list_stack) - 1)
            marker = f"{i + 1}." if list_type == 'ordered' else "-"
            
            # Process li content
            li_content = await self.process_list_item(li, context)
            result.append(f"{indent}{marker} {li_content}")
        
        context.list_stack.pop()
        return '\n'.join(result) + '\n\n'
    
    def handle(self, element: Tag, context: ConversionContext) -> str:
        """Sync wrapper for compatibility"""
        return asyncio.run(self.handle_async(element, context))
    
    async def process_list_item(self, li: Tag, context: ConversionContext) -> str:
        """Process list item content"""
        parts = []
        
        for child in li.children:
            if isinstance(child, NavigableString):
                text = TextUtils.clean_text(str(child), context.config.preserve_whitespace)
                if text:
                    parts.append(text)
            elif isinstance(child, Tag):
                if child.name in ['ul', 'ol']:
                    # Nested list
                    nested = await self.handle_async(child, context)
                    parts.append('\n' + nested.rstrip())
                elif child.name == 'img':
                    # Handle images in lists
                    alt = child.get('alt', '')
                    src = child.get('src', '')
                    
                    if self.image_handler and context.config.download_images and src:
                        downloaded_path = await self.image_handler.download_image(src, context.base_url)
                        parts.append(f"![{alt}]({downloaded_path})")
                    else:
                        parts.append(f"![{alt}]({src})")
                else:
                    # Other elements
                    handler = get_handler_for_element(child)
                    if handler:
                        if hasattr(handler, 'handle_async'):
                            content = await handler.handle_async(child, context)
                        else:
                            content = handler.handle(child, context)
                        content = content.strip()
                        if content:
                            parts.append(content)
                    else:
                        # For inline elements like strong, em, etc.
                        if child.name == 'strong' or child.name == 'b':
                            parts.append(f"**{TextUtils.clean_text(child.get_text(), context.config.preserve_whitespace)}**")
                        elif child.name == 'em' or child.name == 'i':
                            parts.append(f"*{TextUtils.clean_text(child.get_text(), context.config.preserve_whitespace)}*")
                        elif child.name == 'code':
                            parts.append(f"`{child.get_text()}`")
                        elif child.name == 'a' and context.config.include_links:
                            href = child.get('href', '#')
                            text = TextUtils.clean_text(child.get_text(), context.config.preserve_whitespace)
                            parts.append(f"[{text}]({href})")
                        else:
                            parts.append(TextUtils.clean_text(child.get_text(), context.config.preserve_whitespace))
        
        return ' '.join(parts)

class CodeBlockHandler(BaseElementHandler):
    """Handle pre and code blocks"""
    
    def can_handle(self, element: Tag) -> bool:
        return element.name == 'pre'
    
    def handle(self, element: Tag, context: ConversionContext) -> str:
        code_element = element.find('code')
        if code_element:
            code = code_element.get_text()
            language = self.detect_language(code_element)
        else:
            code = element.get_text()
            language = ""
        
        style = context.config.code_block_style
        return f"{style}{language}\n{code}\n{style}\n\n"
    
    def detect_language(self, code_element: Tag) -> str:
        """Try to detect programming language from class attributes"""
        classes = code_element.get('class', [])
        for cls in classes:
            if cls.startswith('language-'):
                return cls.replace('language-', '')
            elif cls.startswith('lang-'):
                return cls.replace('lang-', '')
        return ""

class TableHandler(BaseElementHandler):
    """Handle table elements"""
    
    def can_handle(self, element: Tag) -> bool:
        return element.name == 'table'
    
    def handle(self, element: Tag, context: ConversionContext) -> str:
        rows = []
        
        # Process header
        thead = element.find('thead')
        if thead:
            header_row = []
            for th in thead.find_all('th'):
                header_row.append(self.get_text_content(th, context))
            if header_row:
                rows.append('| ' + ' | '.join(header_row) + ' |')
                rows.append('| ' + ' | '.join(['---'] * len(header_row)) + ' |')
        
        # Process body
        tbody = element.find('tbody') or element
        for tr in tbody.find_all('tr', recursive=False):
            row_data = []
            for td in tr.find_all(['td', 'th']):
                row_data.append(self.get_text_content(td, context))
            if row_data:
                rows.append('| ' + ' | '.join(row_data) + ' |')
        
        return '\n'.join(rows) + '\n\n' if rows else ''

class BlockquoteHandler(BaseElementHandler):
    """Handle blockquote elements"""
    
    def can_handle(self, element: Tag) -> bool:
        return element.name == 'blockquote'
    
    def handle(self, element: Tag, context: ConversionContext) -> str:
        lines = []
        for child in element.children:
            if isinstance(child, Tag):
                handler = get_handler_for_element(child)
                if handler:
                    content = handler.handle(child, context).strip()
                    for line in content.split('\n'):
                        if line:
                            lines.append(f"> {line}")
                        else:
                            lines.append(">")
            elif isinstance(child, NavigableString):
                text = TextUtils.clean_text(str(child), context.config.preserve_whitespace)
                if text:
                    lines.append(f"> {text}")
        
        return '\n'.join(lines) + '\n\n' if lines else ''

class ImageElementHandler(BaseElementHandler):
    """Handle standalone img elements"""
    
    def __init__(self):
        self.image_handler: Optional[ImageHandler] = None
    
    def set_image_handler(self, handler: ImageHandler):
        """Set image handler for downloading images"""
        self.image_handler = handler
    
    def can_handle(self, element: Tag) -> bool:
        return element.name == 'img'
    
    async def handle_async(self, element: Tag, context: ConversionContext) -> str:
        """Async version of handle for image downloading"""
        alt = element.get('alt', '')
        src = element.get('src', '')
        
        if not src:
            return ""
        
        # Download image if handler is available
        if self.image_handler and context.config.download_images:
            downloaded_path = await self.image_handler.download_image(src, context.base_url)
            return f"![{alt}]({downloaded_path})\n\n"
        else:
            return f"![{alt}]({src})\n\n"
    
    def handle(self, element: Tag, context: ConversionContext) -> str:
        """Sync wrapper for compatibility"""
        return asyncio.run(self.handle_async(element, context))

# ===== Handler Registry =====
class HandlerRegistry:
    """Registry for element handlers with shared image handler"""
    
    def __init__(self):
        self.handlers: List[BaseElementHandler] = [
            HeadingHandler(),
            ParagraphHandler(),
            ListHandler(),
            CodeBlockHandler(),
            TableHandler(),
            BlockquoteHandler(),
            ImageElementHandler(),
        ]
        self._image_handler: Optional[ImageHandler] = None
    
    def set_image_handler(self, image_handler: ImageHandler):
        """Set image handler for all handlers"""
        self._image_handler = image_handler
        for handler in self.handlers:
            if hasattr(handler, 'set_image_handler'):
                handler.set_image_handler(image_handler)
    
    def get_handler_for_element(self, element: Tag) -> Optional[BaseElementHandler]:
        """Get appropriate handler for element"""
        for handler in self.handlers:
            if handler.can_handle(element):
                return handler
        return None

# Create global registry instance
_handler_registry = HandlerRegistry()

def get_handler_for_element(element: Tag) -> Optional[BaseElementHandler]:
    """Get appropriate handler for element"""
    return _handler_registry.get_handler_for_element(element)

# ===== Main Converter =====
class WebToMarkdownConverter:
    """Main converter class"""
    
    def __init__(self, config: Optional[ConverterConfig] = None):
        self.config = config or ConverterConfig()
        self.image_handler = ImageHandler(self.config)
        # Set image handler in the global registry
        _handler_registry.set_image_handler(self.image_handler)
    
    async def convert_url(self, url: str) -> str:
        """Convert webpage at URL to markdown"""
        headers = {'User-Agent': self.config.user_agent}
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        
        try:
            async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
                async with session.get(url) as response:
                    response.raise_for_status()
                    html = await response.text()
                    return await self.convert_html(html, base_url=url)
        except aiohttp.ClientError as e:
            logger.error(f"Failed to fetch URL {url}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching URL {url}: {e}")
            raise
        finally:
            await self.image_handler.close()
    
    async def convert_html(self, html: str, base_url: str = "") -> str:
        """Convert HTML string to markdown"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove script and style elements
        for element in soup(['script', 'style']):
            element.decompose()
        
        # Find main content (try common content containers)
        content = None
        for selector in ['main', 'article', '[role="main"]', '#content', '.content']:
            content = soup.select_one(selector)
            if content:
                break
        
        # Fallback to body
        if not content:
            content = soup.body or soup
        
        # Convert to markdown
        context = ConversionContext(
            base_url=base_url,
            config=self.config
        )
        
        markdown = await self._convert_element(content, context)
        
        # Post-process
        markdown = self._post_process(markdown)
        
        return markdown
    
    async def _convert_element(self, element: Tag, context: ConversionContext) -> str:
        """Convert a single element and its children"""
        result = []
        
        for child in element.children:
            if isinstance(child, NavigableString):
                text = TextUtils.clean_text(str(child), context.config.preserve_whitespace)
                if text and not text.isspace():
                    result.append(text)
            elif isinstance(child, Tag):
                # Skip hidden elements
                if child.get('style') and 'display:none' in child.get('style'):
                    continue
                
                handler = get_handler_for_element(child)
                if handler:
                    # Check if handler has async method
                    if hasattr(handler, 'handle_async'):
                        content = await handler.handle_async(child, context)
                    else:
                        content = handler.handle(child, context)
                    result.append(content)
                elif child.name not in ['script', 'style', 'meta', 'link']:
                    # Recursively process unknown elements
                    content = await self._convert_element(child, context)
                    if content.strip():
                        result.append(content)
        
        return ''.join(result)
    
    def _post_process(self, markdown: str) -> str:
        """Post-process markdown output"""
        # Remove excessive blank lines
        markdown = re.sub(r'\n{3,}', '\n\n', markdown)
        
        # Ensure proper spacing around headers
        markdown = re.sub(r'([^\n])\n(#{1,6} )', r'\1\n\n\2', markdown)
        
        # Wrap text if configured
        if self.config.line_width > 0:
            lines = markdown.split('\n')
            wrapped_lines = []
            
            for line in lines:
                # Don't wrap code blocks, tables, or headers
                if (line.startswith('```') or 
                    line.startswith('|') or 
                    line.startswith('#') or
                    line.startswith('>') or
                    re.match(r'^\s*[-*+]\s', line) or
                    re.match(r'^\s*\d+\.\s', line)):
                    wrapped_lines.append(line)
                else:
                    wrapped_lines.append(TextUtils.wrap_text(line, self.config.line_width))
            
            markdown = '\n'.join(wrapped_lines)
        
        return markdown.strip()
    
    async def convert_file(self, filepath: Union[str, Path], base_url: str = "") -> str:
        """Convert HTML file to markdown"""
        try:
            filepath = Path(filepath)
            with open(filepath, 'r', encoding='utf-8') as f:
                html = f.read()
            
            if not base_url:
                base_url = filepath.as_uri()
            
            return await self.convert_html(html, base_url)
        finally:
            await self.image_handler.close()
    
    async def save_to_file(self, markdown: str, output_path: Union[str, Path]) -> None:
        """Save markdown to file"""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown)
        
        logger.info(f"Saved markdown to: {output_path}")

# ===== CLI Interface =====
async def main():
    """Command line interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Convert webpage to markdown')
    parser.add_argument('input', help='URL or HTML file path')
    parser.add_argument('-o', '--output', help='Output markdown file path')
    parser.add_argument('-c', '--config', help='Configuration JSON file')
    parser.add_argument('--no-images', action='store_true', help='Skip image downloading')
    parser.add_argument('--width', type=int, help='Line width for text wrapping')
    
    args = parser.parse_args()
    
    # Load configuration
    if args.config:
        config = ConverterConfig.from_json(args.config)
    else:
        config = ConverterConfig()
    
    # Apply command line overrides
    if args.no_images:
        config.download_images = False
    if args.width:
        config.line_width = args.width
    
    # Create converter
    converter = WebToMarkdownConverter(config)
    
    # Convert
    if args.input.startswith(('http://', 'https://')):
        markdown = await converter.convert_url(args.input)
    else:
        markdown = await converter.convert_file(args.input)
    
    # Output
    if args.output:
        await converter.save_to_file(markdown, args.output)
    else:
        print(markdown)

# ===== Usage Examples =====
"""
# Example 1: Basic usage
converter = WebToMarkdownConverter()
markdown = await converter.convert_url("https://example.com")

# Example 2: Custom configuration
config = ConverterConfig(
    download_images=True,
    image_folder=Path("./images"),
    line_width=100,
    code_block_style="~~~"
)
converter = WebToMarkdownConverter(config)
markdown = await converter.convert_file("page.html")

# Example 3: Command line
python web_to_markdown.py https://example.com -o output.md --width 80
"""

if __name__ == "__main__":
    asyncio.run(main())