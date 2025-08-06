# config.py
import os
from pathlib import Path

# 프로젝트 루트 디렉토리
PROJECT_ROOT = Path(__file__).parent

# 수집할 키워드
KEYWORDS = [
    "bulk", "handy", "handymax", "supramax", "panamax", "capesize",
    "bulker", "dry bulk", "bulk carrier", "steel", "iron ore", "coal", "grain",
    "cargo", "commodity", "freight", "charter", "bdi", "baltic", "tonnage",
    "vessel", "shipping", "maritime", "port", "terminal", "rates", "index", "market",
    "demand", "supply", "벌크", "철강", "화물", "선박", "해운"
]

# 수집 웹사이트 URL
TARGET_URLS = {
    "tradewinds_latest": "https://www.tradewindsnews.com/latest",
    "tradewinds_bulkers": "https://www.tradewindsnews.com/bulkers",
    "freightwaves_bulkers": "https://www.freightwaves.com/news/tag/dry-bulk-shipping",
    # "hellenic_dry_bulk": "https://www.hellenicshippingnews.com/category/dry-bulk/",
    # "seatrade_dry_cargo": "https://www.seatrade-maritime.com/dry-cargo"
}

# 크롤링 설정
MAX_ARTICLES_PER_DAY = int(os.getenv("MAX_ARTICLES_PER_DAY", 50))
CRAWL_DELAY = float(os.getenv("CRAWL_DELAY", 1.0))  # 요청 간 딜레이(초)
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", 10))  # 요청 타임아웃(초)

# 수집 기간
DATE_RANGE = ("2025-08-01", "2025-08-04")

# 요청 헤더 설정 (봇 차단 방지)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}

# OpenAI 설정
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", 0.2))
OPENAI_MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", 1000))

# 임베딩 설정
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", 1536))

# 파일 경로 설정
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
VECTOR_STORE_DIR = PROJECT_ROOT / "vector_store"

# 파일명
CRAWLED_ARTICLES_FILE = DATA_DIR / "crawled_articles.json"
ANALYZED_ARTICLES_FILE = DATA_DIR / "analyzed_articles.json"
FAISS_INDEX_FILE = VECTOR_STORE_DIR / "faiss.index"
METADATA_FILE = VECTOR_STORE_DIR / "metadata.jsonl"

# 로깅 설정
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# 검색 설정
DEFAULT_TOP_K = int(os.getenv("DEFAULT_TOP_K", 5))
MAX_SEARCH_RESULTS = int(os.getenv("MAX_SEARCH_RESULTS", 20))

# Streamlit 설정
STREAMLIT_PAGE_TITLE = "해운·철강 GPT Assistant"
STREAMLIT_PAGE_ICON = "🚢"
STREAMLIT_LAYOUT = "wide"

# 재시도 설정
MAX_RETRIES = int(os.getenv("MAX_RETRIES", 3))
RETRY_DELAY = float(os.getenv("RETRY_DELAY", 2.0))

def ensure_directories():
    """필요한 디렉토리들을 생성합니다."""
    directories = [DATA_DIR, LOGS_DIR, VECTOR_STORE_DIR]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

# 초기화시 디렉토리 생성
ensure_directories()