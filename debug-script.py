# debug_image_download.py
import asyncio
import logging
from pathlib import Path
from web_to_markdown import WebToMarkdownConverter, ConverterConfig

# Enable detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def debug_image_download():
    """Debug image downloading with detailed logging"""
    
    # Simple HTML with an image
    html = """
    <html>
    <body>
        <h1>Test Page</h1>
        <p>Here is an image:</p>
        <img src="https://dummyimage.com/150" alt="Test Image">
        <p>And here is another one: <img src="https://dummyimage.com/100" alt="Inline Image"></p>
    </body>
    </html>
    """
    
    # Configuration
    config = ConverterConfig(
        download_images=True,
        image_folder=Path("./test_images"),
        max_image_size=10 * 1024 * 1024
    )
    
    print("=== Configuration ===")
    print(f"download_images: {config.download_images}")
    print(f"image_folder: {config.image_folder}")
    print(f"max_image_size: {config.max_image_size}")
    
    # Create converter
    converter = WebToMarkdownConverter(config)
    
    print("\n=== Converting HTML ===")
    markdown = await converter.convert_html(html, base_url="https://example.com")
    
    print("\n=== Generated Markdown ===")
    print(markdown)
    
    print("\n=== Image Handler Status ===")
    print(f"Downloaded images: {converter.image_handler.downloaded_images}")
    
    print("\n=== Checking Image Folder ===")
    if config.image_folder.exists():
        files = list(config.image_folder.iterdir())
        print(f"Files in {config.image_folder}: {len(files)}")
        for f in files:
            print(f"  - {f.name} ({f.stat().st_size} bytes)")
    else:
        print(f"Image folder {config.image_folder} does not exist")

async def test_minimal():
    """Minimal test case"""
    from web_to_markdown import ImageHandler
    
    print("\n=== Testing ImageHandler Directly ===")
    
    config = ConverterConfig(
        download_images=True,
        image_folder=Path("./direct_test")
    )
    
    handler = ImageHandler(config)
    
    # Test direct download
    url = "https://dummyimage.com/50"
    base_url = "https://example.com"
    
    print(f"Downloading {url}...")
    result = await handler.download_image(url, base_url)
    print(f"Result: {result}")
    
    await handler.close()

if __name__ == "__main__":
    asyncio.run(debug_image_download())
    asyncio.run(test_minimal())
