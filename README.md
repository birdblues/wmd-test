# Web to Markdown Converter

현대적이고 확장 가능한 Python 기반 웹페이지-마크다운 변환기입니다.

## 특징

- 🚀 **비동기 처리**: aiohttp를 사용한 빠른 웹페이지 다운로드
- 📦 **모듈화된 구조**: 쉽게 확장 가능한 핸들러 시스템
- 🎨 **다양한 HTML 요소 지원**
  - 제목 (h1-h6)
  - 단락 및 인라인 스타일 (bold, italic, code)
  - 리스트 (순서/비순서, 중첩 지원)
  - 코드 블록 (언어 감지 포함)
  - 테이블
  - 인용구
  - 링크 및 이미지
- 🖼️ **이미지 처리**: 자동 다운로드 및 로컬 저장
- ⚙️ **유연한 설정**: JSON 기반 설정 관리
- 🧪 **테스트 완비**: 포괄적인 단위 테스트 포함

## 설치

### 요구사항
- Python 3.8 이상

### 의존성 설치
```bash
pip install aiohttp beautifulsoup4 lxml
```

또는 requirements.txt 사용:
```bash
pip install -r requirements.txt
```

## 사용법

### 1. 명령줄 인터페이스

```bash
# URL 변환
python web_to_markdown.py https://example.com -o output.md

# HTML 파일 변환
python web_to_markdown.py index.html -o output.md

# 설정 파일 사용
python web_to_markdown.py https://example.com -c config.json -o output.md

# 옵션
python web_to_markdown.py https://example.com \
    --no-images \           # 이미지 다운로드 비활성화
    --width 100 \          # 텍스트 너비 설정
    -o output.md
```

### 2. Python 스크립트에서 사용

```python
import asyncio
from web_to_markdown import WebToMarkdownConverter, ConverterConfig

async def main():
    # 기본 사용
    converter = WebToMarkdownConverter()
    markdown = await converter.convert_url("https://example.com")
    print(markdown)
    
    # 커스텀 설정
    config = ConverterConfig(
        download_images=True,
        image_folder=Path("./images"),
        line_width=100,
        code_block_style="~~~"
    )
    converter = WebToMarkdownConverter(config)
    
    # URL 변환 후 파일로 저장
    markdown = await converter.convert_url("https://example.com")
    await converter.save_to_file(markdown, "output.md")

asyncio.run(main())
```

### 3. 설정 파일 (config.json)

```json
{
    "download_images": true,
    "image_folder": "./downloaded_images",
    "max_image_size": 10485760,
    "include_links": true,
    "preserve_whitespace": false,
    "code_block_style": "```",
    "heading_style": "atx",
    "timeout": 30,
    "max_retries": 3,
    "line_width": 80,
    "preserve_empty_lines": false
}
```

## 아키텍처

### 모듈 구조

```
web_to_markdown/
├── Configuration Module     # 설정 관리
├── Element Handlers        # HTML 요소별 변환 핸들러
│   ├── HeadingHandler
│   ├── ParagraphHandler
│   ├── ListHandler
│   ├── CodeBlockHandler
│   ├── TableHandler
│   └── BlockquoteHandler
├── Image Handler          # 이미지 다운로드 및 관리
├── Text Utils            # 텍스트 처리 유틸리티
└── Main Converter        # 메인 변환 로직
```

### 확장하기

새로운 HTML 요소 핸들러 추가:

```python
from web_to_markdown import BaseElementHandler, ConversionContext
from bs4 import Tag

class CustomHandler(BaseElementHandler):
    def can_handle(self, element: Tag) -> bool:
        return element.name == 'custom-element'
    
    def handle(self, element: Tag, context: ConversionContext) -> str:
        content = self.get_text_content(element, context)
        return f"[Custom: {content}]\n\n"

# 핸들러 등록
from web_to_markdown import _handlers
_handlers.append(CustomHandler())
```

## 고급 기능

### 비동기 일괄 처리

```python
async def batch_convert(urls):
    converter = WebToMarkdownConverter()
    tasks = []
    
    for url in urls:
        task = converter.convert_url(url)
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    return results
```

### 콘텐츠 필터링

```python
# 특정 선택자로 콘텐츠 추출
async def convert_specific_content():
    converter = WebToMarkdownConverter()
    html = await fetch_html(url)
    
    soup = BeautifulSoup(html, 'html.parser')
    article = soup.select_one('article.main-content')
    
    if article:
        context = ConversionContext(
            base_url=url,
            config=converter.config
        )
        markdown = await converter._convert_element(article, context)
```

## 테스트

```bash
# pytest 설치
pip install pytest pytest-asyncio

# 테스트 실행
pytest test_web_to_markdown.py -v

# 특정 테스트만 실행
pytest test_web_to_markdown.py::TestTextUtils -v
```

## 성능 고려사항

- **비동기 처리**: 여러 URL을 동시에 처리할 때 asyncio.gather() 사용
- **이미지 캐싱**: 동일한 이미지는 한 번만 다운로드
- **메모리 효율**: 큰 HTML 파일은 스트리밍 처리 고려
- **연결 재사용**: aiohttp 세션을 재사용하여 성능 향상

## 알려진 제한사항

- JavaScript로 렌더링되는 동적 콘텐츠는 변환되지 않음
- CSS 스타일은 무시됨 (인라인 스타일 제외)
- 복잡한 테이블 구조(병합된 셀 등)는 단순화됨

## 기여하기

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 라이선스

MIT License

## 문제 해결

### 이미지 다운로드 실패
- 네트워크 연결 확인
- `max_image_size` 설정 확인
- 이미지 URL이 올바른지 확인

### 인코딩 오류
- HTML 파일의 인코딩이 UTF-8인지 확인
- `charset` 메타 태그 확인

### 메모리 사용량이 높을 때
- 큰 웹페이지의 경우 이미지 다운로드 비활성화
- 텍스트 래핑 비활성화 (`line_width=0`)