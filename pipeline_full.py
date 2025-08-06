# pipeline_full.py
"""
전체 파이프라인 실행: 크롤링 → 분석 → 벡터스토어 저장
"""
import os
import sys
import logging
import json
from datetime import datetime

# 현재 디렉토리를 PYTHONPATH에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from crawler_utils import crawl_tradewinds, crawl_freightwaves
from analyzer import analyze_article
from vector_store import add_documents
from config import MAX_ARTICLES_PER_DAY

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/pipeline.log'),
        logging.StreamHandler()
    ]
)

def step1_crawl():
    """1단계: 뉴스 크롤링"""
    logging.info("="*60)
    logging.info("1단계: 뉴스 크롤링 시작")
    logging.info("="*60)
    
    # 크롤링 실행
    tradewinds_data = crawl_tradewinds(MAX_ARTICLES_PER_DAY)
    freightwaves_data = crawl_freightwaves(MAX_ARTICLES_PER_DAY)
    
    all_articles = tradewinds_data + freightwaves_data
    
    logging.info(f"크롤링 완료: 총 {len(all_articles)}개 기사 수집")
    logging.info(f"- TradeWinds: {len(tradewinds_data)}개")
    logging.info(f"- FreightWaves: {len(freightwaves_data)}개")
    
    # JSON 파일로 저장
    os.makedirs("data", exist_ok=True)
    crawl_file = "data/crawled_articles.json"
    
    with open(crawl_file, "w", encoding="utf-8") as f:
        json.dump(all_articles, f, ensure_ascii=False, indent=2)
    
    logging.info(f"크롤링 결과 저장: {crawl_file}")
    return all_articles

def step2_analyze(articles):
    """2단계: GPT 분석"""
    logging.info("="*60)
    logging.info("2단계: GPT 분석 시작")
    logging.info("="*60)
    
    if not articles:
        logging.warning("분석할 기사가 없습니다.")
        return []
    
    analyzed_articles = []
    
    for i, article in enumerate(articles, 1):
        try:
            logging.info(f"분석 중 ({i}/{len(articles)}): {article['title'][:50]}...")
            
            analyzed = analyze_article(article)
            analyzed["date"] = datetime.now().strftime("%Y-%m-%d")
            analyzed_articles.append(analyzed)
            
        except Exception as e:
            logging.error(f"기사 분석 실패: {e}")
            continue
    
    logging.info(f"분석 완료: {len(analyzed_articles)}개 기사")
    
    # 분석 결과 저장
    analyzed_file = "data/analyzed_articles.json"
    with open(analyzed_file, "w", encoding="utf-8") as f:
        json.dump(analyzed_articles, f, ensure_ascii=False, indent=2)
    
    logging.info(f"분석 결과 저장: {analyzed_file}")
    return analyzed_articles

def step3_vectorize(analyzed_articles):
    """3단계: 벡터스토어 저장"""
    logging.info("="*60)
    logging.info("3단계: 벡터스토어 저장 시작")
    logging.info("="*60)
    
    if not analyzed_articles:
        logging.warning("벡터화할 기사가 없습니다.")
        return
    
    try:
        add_documents(analyzed_articles)
        logging.info(f"벡터스토어 저장 완료: {len(analyzed_articles)}개 기사")
        
    except Exception as e:
        logging.error(f"벡터스토어 저장 실패: {e}")

def show_summary(articles, analyzed_articles):
    """실행 결과 요약"""
    print("\n" + "="*80)
    print("🎉 전체 파이프라인 실행 완료!")
    print("="*80)
    
    print(f"📊 크롤링: {len(articles)}개 기사 수집")
    print(f"🧠 분석: {len(analyzed_articles)}개 기사 분석")
    print(f"🔍 벡터화: {len(analyzed_articles)}개 기사 저장")
    
    if analyzed_articles:
        # 카테고리 분포
        category_count = {}
        group_count = {}
        event_count = {}
        
        for article in analyzed_articles:
            # 카테고리 통계
            for cat in article.get('category', []):
                category_count[cat] = category_count.get(cat, 0) + 1
            
            # 그룹 통계  
            for group in article.get('assigned_group', []):
                group_count[group] = group_count.get(group, 0) + 1
                
            # 이벤트 통계
            for event in article.get('events', []):
                event_count[event] = event_count.get(event, 0) + 1
        
        print(f"\n📈 분석 결과:")
        print(f"- 상위 카테고리: {dict(sorted(category_count.items(), key=lambda x: x[1], reverse=True)[:5])}")
        print(f"- 그룹 분포: {group_count}")
        print(f"- 상위 이벤트: {dict(sorted(event_count.items(), key=lambda x: x[1], reverse=True)[:5])}")
    
    print(f"\n🚀 다음 단계:")
    print(f"   streamlit run streamlit_app.py")
    print("="*80)

def main():
    """전체 파이프라인 실행"""
    start_time = datetime.now()
    
    try:
        # 필요한 디렉토리 생성
        os.makedirs("logs", exist_ok=True)
        os.makedirs("data", exist_ok=True)
        os.makedirs("vector_store", exist_ok=True)
        
        logging.info("전체 파이프라인 시작")
        
        # 1단계: 크롤링
        articles = step1_crawl()
        
        # 2단계: 분석
        analyzed_articles = step2_analyze(articles)
        
        # 3단계: 벡터화
        step3_vectorize(analyzed_articles)
        
        # 결과 요약
        show_summary(articles, analyzed_articles)
        
        end_time = datetime.now()
        duration = end_time - start_time
        logging.info(f"전체 파이프라인 완료 (소요시간: {duration})")
        
    except Exception as e:
        logging.error(f"파이프라인 실행 중 오류: {e}")
        raise

if __name__ == "__main__":
    main()