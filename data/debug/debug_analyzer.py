# debug_analyzer.py

import os
import sys
import logging
from dotenv import load_dotenv

# 현재 디렉토리를 PYTHONPATH에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ✅ 1. 환경변수에서 OpenAI API 키 로드
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

print("🔍 환경변수 체크...")
print(f"OPENAI_API_KEY 존재: {'✅' if openai_api_key else '❌'}")

if not openai_api_key:
    print("\n❌ 오류: OPENAI_API_KEY가 .env 파일에 정의되지 않았습니다.")
    print("해결 방법:")
    print("1. 프로젝트 루트에 .env 파일을 생성하세요")
    print("2. .env 파일에 다음 내용을 추가하세요:")
    print("   OPENAI_API_KEY=your_actual_api_key_here")
    print("3. OpenAI API 키는 https://platform.openai.com/api-keys 에서 생성할 수 있습니다")
    sys.exit(1)

# OpenAI 모듈 테스트
try:
    from openai import OpenAI
    client = OpenAI(api_key=openai_api_key)
    print("✅ OpenAI 클라이언트 초기화 성공")
except Exception as e:
    print(f"❌ OpenAI 클라이언트 초기화 실패: {e}")
    sys.exit(1)

# ✅ 2. analyzer 모듈 import 테스트
try:
    from analyzer import analyze_article
    print("✅ analyzer 모듈 import 성공")
except Exception as e:
    print(f"❌ analyzer 모듈 import 실패: {e}")
    print("필요한 파일들이 모두 있는지 확인하세요: analyzer.py, prompts.py, category_mapper.py")
    sys.exit(1)

# ✅ 3. 테스트용 기사 샘플 정의
sample_articles = [
    {
        "title": "Supramax rates surge as China boosts iron ore imports",
        "content": (
            "Supramax bulk carrier freight rates surged this week, driven by rising demand from China for iron ore. "
            "Analysts attribute the increase to seasonal steel production and ongoing constraints at key loading ports in Australia. "
            "The Baltic Dry Index climbed by 12% over the last three days, signaling growing pressure on global tonnage supply. "
            "Market experts expect the upward trend to continue through the remainder of the quarter."
        ),
        "url": "https://example.com/supramax-market-update",
        "source": "TestNews",
        "date": "2025-08-03",
        "keywords": ["supramax", "iron ore", "freight", "rates"]
    },
    {
        "title": "Container shipping rates drop amid reduced demand",
        "content": (
            "Container shipping rates on major Asia-Europe routes declined for the third consecutive week. "
            "The Shanghai Containerized Freight Index (SCFI) fell by 8% as seasonal demand weakened. "
            "Carriers are implementing capacity management strategies to stabilize rates in the coming months."
        ),
        "url": "https://example.com/container-rates-drop",
        "source": "ShippingDaily",
        "date": "2025-08-03",  
        "keywords": ["container", "scfi", "rates"]
    }
]

# ✅ 4. 각 샘플 기사에 대해 analyze_article() 호출
for i, sample_article in enumerate(sample_articles, 1):
    print(f"\n{'='*60}")
    print(f"🧪 테스트 {i}: GPT 분석 중...")
    print(f"제목: {sample_article['title']}")
    print("="*60)

    try:
        result = analyze_article(sample_article)
        
        print("✅ 분석 결과:")
        print("-" * 40)
        print(f"📝 요약: {result['summary']}")
        print(f"🏷️  카테고리: {result['category']}")
        print(f"👥 그룹: {result['assigned_group']}")
        print(f"📅 이벤트: {result['events']}")
        print(f"🔗 URL: {result['source_url']}")
        print(f"📰 출처: {result['source']}")
        print("-" * 40)
        
    except Exception as e:
        print(f"❌ GPT 분석 중 오류 발생: {e}")
        logging.exception("상세 오류 정보:")

print(f"\n{'='*60}")
print("🎉 테스트 완료!")
print("="*60)