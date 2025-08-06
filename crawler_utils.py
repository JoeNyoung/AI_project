import requests
from bs4 import BeautifulSoup
from datetime import datetime
import logging
import time

def fetch_article(url):
    """기사 내용을 가져오는 함수"""
    from config import HEADERS
    
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 기사 본문 추출 (실제 사이트 구조에 맞게 수정 필요)
        content_selectors = [
            'div.article-content',
            'div.content',
            'article',
            'div.post-content',
            'div.entry-content',
            '.article-body',
            '.story-body'
        ]
        
        content = ""
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                content = content_elem.get_text(strip=True)
                break
        
        return content
    except Exception as e:
        logging.error(f"기사 내용 가져오기 실패 - URL: {url}, 오류: {e}")
        return None

def fetch_freightwaves_article(url):
    """FreightWaves 기사 내용을 가져오는 함수"""
    from config import HEADERS
    
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # FreightWaves 기사 본문 추출을 위한 선택자
        content_selectors = [
            'div.entry-content',
            'div.post-content', 
            'div.article-content',
            'div.content',
            'article .content',
            '.post-body',
            '.article-body',
            '.entry-body',
            'main article',
            '[class*="content"]'
        ]
        
        content = ""
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                # 광고나 불필요한 요소 제거
                for unwanted in content_elem.select('script, style, .advertisement, .ad, .social-share'):
                    unwanted.decompose()
                content = content_elem.get_text(strip=True)
                break
        
        return content
    except Exception as e:
        logging.error(f"FreightWaves 기사 내용 가져오기 실패 - URL: {url}, 오류: {e}")
        return None

def is_relevant(title, content, keywords):
    """키워드 기반으로 관련성 확인"""
    text = (title + " " + content).lower()
    for keyword in keywords:
        if keyword.lower() in text:
            return True
    return False

def crawl_tradewinds(max_articles):
    """개선된 TradeWinds 사이트 크롤링"""
    from config import TARGET_URLS, KEYWORDS, HEADERS
    
    url = TARGET_URLS["tradewinds_bulkers"]
    try:
        # 더 강화된 헤더로 요청
        enhanced_headers = HEADERS.copy()
        enhanced_headers.update({
            'Referer': 'https://www.tradewindsnews.com/',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        })
        
        response = requests.get(url, headers=enhanced_headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        articles = []
        
        logging.info(f"TradeWinds 페이지 로드 성공: {len(response.content)} bytes")
        
        # 더 다양한 링크 선택자 시도
        link_selectors = [
            # 기존 선택자들
            "a.card-headline",
            "h2 a", "h3 a", "h4 a",
            ".headline a", ".title a",
            "a[href*='/bulkers/']",
            "a[href*='/article/']", 
            "a[href*='/news/']",
            
            # 새로운 선택자들 (실제 사이트 구조 기반)
            ".story-headline a",
            ".article-headline a", 
            ".news-item a",
            ".story-item a",
            "article h2 a",
            "article h3 a",
            ".content-item a",
            ".list-item a",
            
            # 더 일반적인 선택자들
            "a[href*='tradewindsnews.com']",
            "a[title*='bulker']",
            "a[title*='shipping']"
        ]
        
        # 각 선택자별로 테스트
        all_found_links = []
        for selector in link_selectors:
            links = soup.select(selector)
            if links:
                logging.info(f"TradeWinds 선택자 '{selector}': {len(links)}개 링크 발견")
                all_found_links.extend(links)
                
        # 중복 제거
        unique_links = []
        seen_urls = set()
        for link in all_found_links:
            href = link.get('href', '')
            if href and href not in seen_urls:
                unique_links.append(link)
                seen_urls.add(href)
        
        if not unique_links:
            # 대안: 텍스트에서 기사 제목 추출
            logging.warning("일반 선택자로 링크를 찾을 수 없음. 텍스트 분석 시도...")
            
            # 페이지의 모든 텍스트에서 기사 제목 패턴 찾기
            page_text = soup.get_text()
            
            # 기사 제목으로 보이는 패턴들 찾기
            potential_titles = []
            
            # 줄 단위로 분석
            lines = page_text.split('\n')
            for line in lines:
                line = line.strip()
                if (len(line) > 20 and len(line) < 200 and 
                    any(keyword.lower() in line.lower() for keyword in KEYWORDS)):
                    potential_titles.append(line)
            
            logging.info(f"텍스트 분석으로 {len(potential_titles)}개 잠재 기사 발견")
            
            # 잠재 기사들을 articles로 변환
            for i, title in enumerate(potential_titles[:max_articles]):
                if any(keyword.lower() in title.lower() for keyword in KEYWORDS):
                    article_data = {
                        "title": title,
                        "url": url,  # 원본 페이지 URL 사용
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "source": "TradeWinds",
                        "content": title,  # 제목을 내용으로 사용
                        "keywords": [kw for kw in KEYWORDS if kw.lower() in title.lower()]
                    }
                    articles.append(article_data)
                    logging.info(f"TradeWinds 텍스트 추출 성공 ({len(articles)}/{max_articles}): {title[:50]}...")
            
            return articles
        
        logging.info(f"TradeWinds 총 고유 링크: {len(unique_links)}개")
        
        # 링크 처리
        for i, link in enumerate(unique_links):
            if len(articles) >= max_articles:
                break
                
            try:
                article_url = link.get('href', '')
                if not article_url:
                    continue
                    
                # URL 정규화
                if not article_url.startswith('http'):
                    if article_url.startswith('/'):
                        article_url = 'https://www.tradewindsnews.com' + article_url
                    else:
                        article_url = 'https://www.tradewindsnews.com/' + article_url
                
                title = link.get_text(strip=True)
                if not title or len(title) < 10:
                    # 제목이 없거나 너무 짧으면 링크의 title 속성 사용
                    title = link.get('title', '')
                    if not title:
                        continue
                
                # 관련성 1차 검사 (제목만으로)
                if not any(keyword.lower() in title.lower() for keyword in KEYWORDS):
                    continue
                
                # 요청 간 딜레이
                if i > 0:
                    time.sleep(1)
                
                # 기사 내용 가져오기 시도
                content = fetch_article(article_url)
                if not content:
                    # 내용을 가져올 수 없으면 제목만 사용
                    content = title
                
                # 최종 관련성 검사
                if is_relevant(title, content, KEYWORDS):
                    article_data = {
                        "title": title,
                        "url": article_url,
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "source": "TradeWinds",
                        "content": content[:1000] + "..." if len(content) > 1000 else content,
                        "keywords": [kw for kw in KEYWORDS if kw.lower() in (title + " " + content).lower()]
                    }
                    articles.append(article_data)
                    logging.info(f"TradeWinds 수집 성공 ({len(articles)}/{max_articles}): {title[:50]}...")
                    
            except Exception as e:
                logging.error(f"TradeWinds 기사 처리 중 오류: {e}")
                continue
                
        return articles
        
    except Exception as e:
        logging.error(f"TradeWinds 크롤링 오류: {e}")
        return []

def crawl_freightwaves(max_articles):
    """FreightWaves 사이트 크롤링"""
    from config import TARGET_URLS, KEYWORDS, HEADERS
    
    url = TARGET_URLS["freightwaves_bulkers"]
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        articles = []

        # FreightWaves 기사 링크 선택자
        link_selectors = [
            "h2.entry-title a",
            "h3.entry-title a", 
            ".post-title a",
            ".article-title a",
            "h2 a",
            "h3 a",
            "a[href*='/news/']",
            ".entry-header h2 a",
            ".post-header h2 a"
        ]
        
        links = []
        for selector in link_selectors:
            links = soup.select(selector)
            if links:
                logging.info(f"FreightWaves 링크 선택자 '{selector}'로 {len(links)}개 링크 발견")
                break

        if not links:
            logging.warning("FreightWaves에서 기사 링크를 찾을 수 없습니다. 사이트 구조를 확인해주세요.")
            return []

        for i, link in enumerate(links):
            if len(articles) >= max_articles:
                break

            try:
                article_url = link.get('href', '')
                if not article_url:
                    continue
                    
                if not article_url.startswith('http'):
                    if article_url.startswith('/'):
                        article_url = 'https://www.freightwaves.com' + article_url
                    else:
                        article_url = 'https://www.freightwaves.com/' + article_url
                
                title = link.get_text(strip=True)
                if not title:
                    continue
                
                # 요청 간 딜레이 추가 (서버 부하 방지)
                if i > 0:
                    time.sleep(1)
                
                content = fetch_freightwaves_article(article_url)

                if content and is_relevant(title, content, KEYWORDS):
                    article_data = {
                        "title": title,
                        "url": article_url,
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "source": "FreightWaves",
                        "content": content[:1000] + "..." if len(content) > 1000 else content,
                        "keywords": [kw for kw in KEYWORDS if kw.lower() in content.lower() or kw.lower() in title.lower()]
                    }
                    articles.append(article_data)
                    logging.info(f"FreightWaves 수집 성공 ({len(articles)}/{max_articles}): {title}")
                else:
                    logging.debug(f"FreightWaves 관련성 없음으로 제외: {title}")
                    
            except Exception as e:
                logging.error(f"FreightWaves 기사 처리 중 오류: {e}")
                continue

        return articles
    except Exception as e:
        logging.error(f"FreightWaves 크롤링 오류: {e}")
        return []