# example_usage.py
import asyncio
from pathlib import Path
from web_to_markdown import WebToMarkdownConverter, ConverterConfig

async def test_image_download():
    """Test image downloading functionality"""
    
    # HTML with images for testing
    test_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Page with Images</title>
    </head>
    <body>
        <h1>Test Page</h1>
        <p>This is a paragraph with an inline image: <img src=https://dummyimage.com/400x200/000/fff" alt="Test Image 1"></p>
        
        <img src="https://dummyimage.com/400x200/000/fff" alt="Standalone Image">
        
        <p>Another paragraph with <strong>bold text</strong> and another image:</p>
        <img src="images/test.svg" alt="Relative Image">
        
        <ul>
            <li>List item with image: <img src="https://dummyimage.com/50" alt="Small Image"></li>
            <li>Regular list item</li>
        </ul>
    </body>
    </html>
    """
    
    # Configuration with image downloading enabled
    config = ConverterConfig(
        download_images=True,
        image_folder=Path("./images"),
        max_image_size=10 * 1024 * 1024,  # 10MB
        include_links=True,
        line_width=0  # No wrapping for cleaner output
    )
    
    # Create converter
    converter = WebToMarkdownConverter(config)
    
    # Convert HTML
    print("Converting HTML with image downloads...")
    markdown = await converter.convert_html(test_html, base_url="https://dummyimage.com")
    
    print("\n=== Generated Markdown ===")
    print(markdown)
    
    print("\n=== Downloaded Images ===")
    if config.image_folder.exists():
        for image_file in config.image_folder.iterdir():
            print(f"- {image_file.name}")
    
    # Save to file
    # await converter.save_to_file(markdown, "output_with_images.md")
    # print(f"\nMarkdown saved to: output_with_images.md")

async def test_url_conversion():
    """Test converting a real URL"""
    
    config = ConverterConfig(
        download_images=True,
        image_folder=Path("./web_images"),
        max_image_size=5 * 1024 * 1024,  # 5MB limit
        timeout=30,
        line_width=80
    )
    
    converter = WebToMarkdownConverter(config)
    
    # Convert a real webpage
    url = "https://github.com/topics/markdown"  # Example URL with images
    print(f"Converting {url}...")
    
    try:
        markdown = await converter.convert_url(url)
        await converter.save_to_file(markdown, "github_markdown_page.md")
        print(f"Conversion complete! Check github_markdown_page.md")
        
        # Show first 500 characters
        print("\n=== Preview (first 500 chars) ===")
        print(markdown[:500] + "..." if len(markdown) > 500 else markdown)
        
    except Exception as e:
        print(f"Error converting URL: {e}")

async def test_no_image_download():
    """Test conversion without image downloading"""
    
    config = ConverterConfig(
        download_images=False,  # Disable image downloads
        include_links=True,
        line_width=80
    )
    
    converter = WebToMarkdownConverter(config)
    
    html = """
    <h1>Test without image download</h1>
    <p>Image URL will be preserved: <img src="https://dummyimage.com/300x200/ffffff/ff0000&text=Test+Image+1" alt="Test"></p>
    """
    
    markdown = await converter.convert_html(html)
    print("\n=== Without Image Download ===")
    print(markdown)

async def main():
    """Run all tests"""
    print("Testing Web to Markdown Converter with Image Support\n")
    
    # Test 1: Basic HTML with image downloads
    await test_image_download()
    
    print("\nend test_image_download\n" + "="*50 + "\n")
    
    # Test 2: Real URL conversion
    # await test_url_conversion()  # Uncomment to test real URL
 
    # Test 3: Without image downloads
    await test_no_image_download()

if __name__ == "__main__":
    asyncio.run(test_url_conversion())
    asyncio.run(test_no_image_download())
    asyncio.run(test_image_download())
