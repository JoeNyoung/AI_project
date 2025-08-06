# run_embedding_update.py
"""
1단계 크롤링 → 2단계 GPT 분석 → 3단계 벡터스토어 저장 전체 배치
"""
import json, datetime
from analyzer import analyze_article
from vector_store import add_documents

CRAWL_JSON = "data/crawled_articles.json"  # 1단계 결과 파일

def main():
    with open(CRAWL_JSON, encoding="utf-8") as f:
        docs = json.load(f)

    enriched = []
    for d in docs:
        enriched_doc = analyze_article(d)
        enriched_doc["date"] = datetime.date.today().isoformat()
        enriched.append(enriched_doc)

    add_documents(enriched)
    print(f"✅ {len(enriched)}건 임베딩 & 저장 완료")

if __name__ == "__main__":
    main()