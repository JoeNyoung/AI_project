import requests
from bs4 import BeautifulSoup
from datetime import datetime
import logging
import time

def debug_crawl_tradewinds():
    """TradeWinds 크롤링 디버깅"""
    from config import TARGET_URLS, KEYWORDS, HEADERS
    
    url = TARGET_URLS["tradewinds_bulkers"]
    print(f"=== TradeWinds 디버깅 ===")
    print(f"URL: {url}")
    
    try:
        response = requests.get(url, headers=HEADERS)
        print(f"응답 상태 코드: {response.status_code}")
        print(f"응답 길이: {len(response.content)} bytes")
        
        if response.status_code != 200:
            print(f"HTTP 오류: {response.status_code}")
            return
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # HTML 구조 분석
        print(f"\n=== HTML 구조 분석 ===")
        print(f"페이지 제목: {soup.title.string if soup.title else 'None'}")
        
        # 다양한 선택자로 링크 찾기
        link_selectors = [
            "a.card-headline",
            "h2 a",
            "h3 a", 
            ".headline a",
            ".title a",
            "a[href*='/article/']",
            "a[href*='/news/']",
            "a[href*='/bulkers/']",
            ".card a",
            ".article-card a"
        ]
        
        print(f"\n=== 링크 선택자 테스트 ===")
        for selector in link_selectors:
            links = soup.select(selector)
            print(f"{selector}: {len(links)}개 링크")
            if links:
                for i, link in enumerate(links[:3]):  # 처음 3개만 출력
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    print(f"  [{i+1}] {text[:50]}... -> {href[:50]}...")
                break
        
        # 모든 링크 확인
        all_links = soup.find_all('a', href=True)
        print(f"\n총 링크 수: {len(all_links)}개")
        
        # 기사와 관련될 수 있는 링크 찾기
        article_links = []
        for link in all_links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            if any(keyword in href.lower() for keyword in ['article', 'news', 'bulker', 'shipping']):
                article_links.append((text, href))
        
        print(f"기사 관련 링크: {len(article_links)}개")
        for i, (text, href) in enumerate(article_links[:5]):
            print(f"  [{i+1}] {text[:50]}... -> {href[:50]}...")
            
    except Exception as e:
        print(f"TradeWinds 디버깅 오류: {e}")

def debug_crawl_freightwaves():
    """FreightWaves 크롤링 디버깅"""
    from config import TARGET_URLS, KEYWORDS, HEADERS
    
    url = TARGET_URLS["freightwaves_bulkers"]
    print(f"\n=== FreightWaves 디버깅 ===")
    print(f"URL: {url}")
    
    try:
        response = requests.get(url, headers=HEADERS)
        print(f"응답 상태 코드: {response.status_code}")
        print(f"응답 길이: {len(response.content)} bytes")
        
        if response.status_code != 200:
            print(f"HTTP 오류: {response.status_code}")
            return
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # HTML 구조 분석
        print(f"\n=== HTML 구조 분석 ===")
        print(f"페이지 제목: {soup.title.string if soup.title else 'None'}")
        
        # 다양한 선택자로 링크 찾기
        link_selectors = [
            "h2.entry-title a",
            "h3.entry-title a", 
            ".post-title a",
            ".article-title a",
            "h2 a",
            "h3 a",
            "a[href*='/news/']",
            ".entry-header h2 a",
            ".post-header h2 a",
            ".card a",
            ".article a"
        ]
        
        print(f"\n=== 링크 선택자 테스트 ===")
        for selector in link_selectors:
            links = soup.select(selector)
            print(f"{selector}: {len(links)}개 링크")
            if links:
                for i, link in enumerate(links[:3]):  # 처음 3개만 출력
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    print(f"  [{i+1}] {text[:50]}... -> {href[:50]}...")
                break
        
        # 모든 링크 확인
        all_links = soup.find_all('a', href=True)
        print(f"\n총 링크 수: {len(all_links)}개")
        
        # 기사와 관련될 수 있는 링크 찾기
        article_links = []
        for link in all_links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            if any(keyword in href.lower() for keyword in ['news', 'article', 'bulk', 'shipping']):
                article_links.append((text, href))
        
        print(f"기사 관련 링크: {len(article_links)}개")
        for i, (text, href) in enumerate(article_links[:5]):
            print(f"  [{i+1}] {text[:50]}... -> {href[:50]}...")
            
    except Exception as e:
        print(f"FreightWaves 디버깅 오류: {e}")

def test_article_fetch():
    """기사 내용 가져오기 테스트"""
    print(f"\n=== 기사 내용 가져오기 테스트 ===")
    
    # 테스트 URL (실제 존재하는 기사 URL로 변경 필요)
    test_urls = [
        "https://www.tradewindsnews.com/bulkers",
        "https://www.freightwaves.com/news/tag/dry-bulk-shipping"
    ]
    
    from config import HEADERS
    
    for url in test_urls:
        try:
            print(f"\n테스트 URL: {url}")
            response = requests.get(url, headers=HEADERS)
            print(f"응답 코드: {response.status_code}")
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # 첫 번째 링크 찾기
                first_link = soup.find('a', href=True)
                if first_link:
                    print(f"첫 번째 링크: {first_link.get('href')}")
                    print(f"링크 텍스트: {first_link.get_text(strip=True)[:50]}...")
                
        except Exception as e:
            print(f"테스트 오류: {e}")

def main_debug():
    """디버깅 메인 함수"""
    print("크롤링 디버깅 시작...\n")
    
    # 설정 확인
    try:
        from config import TARGET_URLS, KEYWORDS, HEADERS
        print("=== 설정 확인 ===")
        print(f"TARGET_URLS: {TARGET_URLS}")
        print(f"KEYWORDS 수: {len(KEYWORDS)}개")
        print(f"HEADERS: {HEADERS}")
    except Exception as e:
        print(f"설정 파일 오류: {e}")
        return
    
    # 각 사이트 디버깅
    debug_crawl_tradewinds()
    debug_crawl_freightwaves()
    test_article_fetch()

if __name__ == "__main__":
    main_debug()