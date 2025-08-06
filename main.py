import sys
import os
import logging
import pprint
import json

# 현재 디렉토리를 PYTHONPATH에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# crawler_utils에서 함수 직접 import
from crawler_utils import crawl_tradewinds, crawl_freightwaves
from config import MAX_ARTICLES_PER_DAY

# logs 디렉토리가 없으면 생성
if not os.path.exists('logs'):
    os.makedirs('logs')

# 로깅 설정
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/crawl.log'),
        logging.StreamHandler()  # 콘솔에도 출력
    ]
)

def main():
    """메인 실행 함수"""
    logging.info("크롤링 작업 시작")
    
    try:
        # 두 사이트에서 데이터 수집
        logging.info("TradeWinds 크롤링 시작...")
        tradewinds_data = crawl_tradewinds(MAX_ARTICLES_PER_DAY)
        
        logging.info("FreightWaves 크롤링 시작...")
        freightwaves_data = crawl_freightwaves(MAX_ARTICLES_PER_DAY)
        
        # 출력으로 데이터 확인하기
        pp = pprint.PrettyPrinter(indent=2)

        # TradeWinds 결과 출력
        print("\n" + "="*60)
        print("=== TradeWinds 크롤링 결과 ===")
        print("="*60)
        if tradewinds_data:
            print(f"수집된 기사 수: {len(tradewinds_data)}개")
            print("\n처음 3개 기사:")
            pp.pprint(tradewinds_data[:3])
        else:
            print("수집된 기사가 없습니다.")
        
        # FreightWaves 결과 출력
        print("\n" + "="*60)
        print("=== FreightWaves 크롤링 결과 ===")
        print("="*60)
        if freightwaves_data:
            print(f"수집된 기사 수: {len(freightwaves_data)}개")
            print("\n처음 3개 기사:")
            pp.pprint(freightwaves_data[:3])
        else:
            print("수집된 기사가 없습니다.")
        
        # 전체 통계 출력
        total_articles = len(tradewinds_data) + len(freightwaves_data)
        print("\n" + "="*60)
        print("=== 크롤링 통계 ===")
        print("="*60)
        print(f"TradeWinds 수집 기사 수: {len(tradewinds_data)}개")
        print(f"FreightWaves 수집 기사 수: {len(freightwaves_data)}개")
        print(f"총 수집 기사 수: {total_articles}개")
        
        # 로그에도 기록
        logging.info(f"TradeWinds 수집 기사 수: {len(tradewinds_data)}")
        logging.info(f"FreightWaves 수집 기사 수: {len(freightwaves_data)}")
        logging.info(f"총 수집 기사 수: {total_articles}")
        logging.info("크롤링 작업 완료")
        
        # 수집된 데이터를 하나로 합치기
        all_articles = tradewinds_data + freightwaves_data
        
        # 키워드별 분류 (선택사항)
        if all_articles:
            print("\n" + "="*60)
            print("=== 키워드별 기사 분포 ===")
            print("="*60)
            keyword_count = {}
            for article in all_articles:
                for keyword in article.get('keywords', []):
                    keyword_count[keyword] = keyword_count.get(keyword, 0) + 1
            
            # 상위 10개 키워드 출력
            sorted_keywords = sorted(keyword_count.items(), key=lambda x: x[1], reverse=True)
            for keyword, count in sorted_keywords[:10]:
                print(f"{keyword}: {count}개")
        
        return all_articles
        
    except Exception as e:
        logging.error(f"크롤링 작업 중 오류 발생: {e}")
        print(f"오류 발생: {e}")
        return []

def save_to_json(articles):
    """크롤링 결과를 JSON 파일로 저장"""
    if not articles:
        logging.warning("저장할 기사가 없습니다.")
        return None
        
    # data 폴더가 없으면 생성
    os.makedirs("data", exist_ok=True)
    out_path = "data/crawled_articles.json"
    
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
        
        logging.info(f"크롤링 결과 {len(articles)}건 저장: {out_path}")
        print(f"✅ JSON 저장 완료 → {out_path}")
        return out_path
        
    except Exception as e:
        logging.error(f"JSON 저장 중 오류: {e}")
        return None

if __name__ == "__main__":
    articles = main()
    print(f"\n프로그램 종료. 총 {len(articles)}개 기사 수집됨.")
    
    # JSON 저장 (한 번만)
    if articles:
        save_to_json(articles)