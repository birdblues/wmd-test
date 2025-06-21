# test_simple.py
import asyncio
from pathlib import Path
from web_to_markdown import WebToMarkdownConverter, ConverterConfig

async def main():
    # 이미지가 있는 간단한 HTML
    html = """
    <html>
    <body>
        <h1>이미지 다운로드 테스트</h1>
        <p>테스트 이미지 1:</p>
        <img src="https://dummyimage.com/300x200/ffffff/ff0000?text=Test+Image+1" alt="빨간색 테스트 이미지">
        
        <p>인라인 이미지: <img src="https://dummyimage.com/150x150/00FF00/000000?text=Green" alt="녹색 이미지"> 입니다.</p>
        
        <ul>
            <li>리스트 아이템 <img src="https://dummyimage.com/50x50/0000FF/FFFFFF?text=Blue" alt="파란색 작은 이미지"></li>
        </ul>
    </body>
    </html>
    """
    
    # 설정
    config = ConverterConfig(
        download_images=True,  # 이미지 다운로드 활성화
        image_folder=Path("./downloaded_images"),  # 이미지 저장 폴더
        max_image_size=10 * 1024 * 1024  # 최대 10MB
    )
    
    # 변환기 생성
    converter = WebToMarkdownConverter(config)
    
    print("HTML을 마크다운으로 변환 중...")
    markdown = await converter.convert_html(html, base_url="https://example.com")
    
    print("\n=== 생성된 마크다운 ===")
    print(markdown)
    
    # 이미지 폴더 확인
    print("\n=== 다운로드된 이미지 ===")
    if config.image_folder.exists():
        images = list(config.image_folder.glob("*"))
        print(f"총 {len(images)}개의 이미지가 다운로드되었습니다:")
        for img in images:
            print(f"  - {img.name} ({img.stat().st_size:,} bytes)")
    else:
        print("이미지 폴더가 생성되지 않았습니다.")
    
    # 마크다운 파일로 저장
    await converter.save_to_file(markdown, "output.md")
    print(f"\n마크다운이 output.md 파일로 저장되었습니다.")

if __name__ == "__main__":
    asyncio.run(main())
