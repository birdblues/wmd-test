# CLAUDE.md

이 파일은 이 저장소에서 코드와 함께 작업할 때 Claude Code(claude.ai/code)에 대한 지침을 제공합니다.

## 프로젝트 개요

웹에서 마크다운(Web to Markdown, WMD) 변환기 - 현대적이고 모듈식 Python 구현으로 웹 페이지 및 HTML 파일을 마크다운 형식으로 변환합니다. 비동기 처리, 모듈형 요소 핸들러, 스마트 이미지 다운로드, 광범위한 설정 옵션을 제공합니다.

## 핵심 파일 구조

- `web_to_markdown.py` - 메인 변환기 코드 (단일 파일 구현)
- `simple-test.py` - 이미지 다운로드 기능 테스트 스크립트
- `pyproject.toml` - 프로젝트 메타데이터

## 아키텍처

완전한 비동기 핸들러 기반 아키텍처:

### 핵심 구성 요소
- **ConverterConfig**: 중앙집중식 설정 관리 (이미지 처리, 네트워크, 출력 포맷팅)
- **ImageHandler**: HTTP 응답 헤더 기반 스마트 이미지 다운로드 및 확장자 감지
- **ConversionContext**: 변환 중 상태 및 컨텍스트 관리 (이미지 핸들러 포함)
- **TextUtils**: 텍스트 처리 유틸리티 (정리, 이스케이프, 래핑)

### 요소 핸들러 (모두 비동기)
- **HeadingHandler** - h1-h6 요소 (ATX/setext 스타일 지원)
- **ParagraphHandler** - 인라인 요소가 포함된 단락 (bold, italic, links, images)
- **ListHandler** - 중첩 지원 순서/비순서 목록
- **CodeBlockHandler** - 언어 감지가 포함된 pre/code 블록
- **TableHandler** - HTML 테이블을 마크다운 테이블로 변환
- **BlockquoteHandler** - blockquote 요소

### 중요한 기술적 특징
- 모든 핸들러가 async/await 패턴 사용
- 이미지 다운로드 시 Content-Type 헤더에서 올바른 파일 확장자 추출
- ConversionContext를 통한 이미지 핸들러 전달
- BeautifulSoup + aiohttp를 사용한 완전 비동기 처리

## 개발 환경 설정

```bash
# 가상환경 생성 및 활성화 (권장)
python3 -m venv venv
source venv/bin/activate

# 필수 의존성 설치
pip install aiohttp beautifulsoup4 lxml

# 테스트 실행
python simple-test.py

# 메인 변환기 실행
python web_to_markdown.py https://example.com -o output.md
python web_to_markdown.py local-file.html -o output.md

# 설정 파일 사용
python web_to_markdown.py https://example.com -c config.json -o output.md

# 일반적인 옵션들
python web_to_markdown.py https://example.com --no-images --width 100 -o output.md
```

## 테스트

현재 `simple-test.py`가 이미지 다운로드 기능을 검증하는 테스트 스크립트로 사용됩니다:

```bash
# 이미지 다운로드 테스트 실행
python simple-test.py
```

추가 테스트 개발 시 고려사항:
- 비동기 테스트 지원을 위해 pytest와 pytest-asyncio 사용
- 개별 핸들러를 별도로 테스트 (모든 핸들러가 async 함수)
- 이미지 다운로드 및 Content-Type 감지 기능 테스트
- 종단 간 변환 시나리오 테스트
- 일관된 테스트를 위해 네트워크 요청 모킹

## 주요 설정 옵션

JSON 기반 설정을 통한 세밀한 제어:

### 이미지 처리
- `download_images`: 이미지 다운로드 활성화/비활성화
- `image_folder`: 다운로드된 이미지 저장 디렉터리
- `max_image_size`: 최대 이미지 크기 (바이트)

### 변환 옵션
- `include_links`: 출력에 링크 유지 여부
- `code_block_style`: 코드 블록 경계 스타일 (\`\`\`)
- `heading_style`: ATX (#) 또는 setext (밑줄) 스타일
- `line_width`: 텍스트 줄 바꿈 너비 (0은 비활성화)
- `preserve_whitespace`: 공백 문자 보존 여부

### 네트워크 설정
- `timeout`: HTTP 요청 타임아웃 (초)
- `max_retries`: 최대 재시도 횟수
- `user_agent`: HTTP 요청 시 사용할 User-Agent

## 확장 포인트

새로운 HTML 요소 핸들러 추가:

1. `BaseElementHandler`에서 상속
2. `async def can_handle(self, element: Tag) -> bool` 구현
3. `async def handle(self, element: Tag, context: ConversionContext) -> str` 구현
4. `_handlers` 목록에 등록

**중요**: 모든 핸들러는 비동기 함수여야 하며, 이미지 처리가 필요한 경우 `context.image_handler`를 사용해야 합니다.

## 알려진 이슈 및 개선사항

- 이미지 확장자 감지: HTTP Content-Type 헤더를 기반으로 올바른 파일 확장자 자동 감지
- 완전 비동기 처리: 모든 핸들러가 async/await 패턴을 사용하여 성능 최적화
- 컨텍스트 기반 이미지 처리: ConversionContext를 통한 이미지 핸들러 전달로 일관된 이미지 처리