# analyzer.py (개선 버전)
import os
import json
import logging
import time
from typing import Dict, List, Optional
from dotenv import load_dotenv
from openai import OpenAI
from prompts import DOMAIN_SYSTEM_PROMPT
from category_mapper import map_categories_to_groups

# 로깅 설정
logger = logging.getLogger(__name__)

# 환경변수 로드
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 재시도 설정
MAX_RETRIES = 3
RETRY_DELAY = 2.0

def validate_article_input(article: Dict) -> bool:
    """입력 기사 데이터 검증"""
    required_fields = ['title', 'content']
    
    for field in required_fields:
        if not article.get(field):
            logger.warning(f"필수 필드 누락: {field}")
            return False
        
        if str(article[field]).strip() in ['', 'None', 'none']:
            logger.warning(f"빈 값 또는 None: {field}")
            return False
    
    return True

def clean_gpt_response(gpt_output: str) -> str:
    """GPT 응답에서 JSON 부분 추출"""
    gpt_output = gpt_output.strip()
    
    # JSON 코드 블록 처리
    if "```json" in gpt_output:
        json_start = gpt_output.find("```json") + 7
        json_end = gpt_output.find("```", json_start)
        if json_end != -1:
            return gpt_output[json_start:json_end].strip()
    
    # 일반 JSON 블록 처리
    if "{" in gpt_output and "}" in gpt_output:
        json_start = gpt_output.find("{")
        json_end = gpt_output.rfind("}") + 1
        return gpt_output[json_start:json_end]
    
    return gpt_output

def parse_gpt_output(gpt_output: str) -> Dict:
    """GPT 출력 파싱 (개선된 오류 처리)"""
    try:
        json_text = clean_gpt_response(gpt_output)
        result = json.loads(json_text)
        
        # 결과 검증 및 정리
        if not isinstance(result, dict):
            raise ValueError("결과가 딕셔너리 형태가 아닙니다")
        
        # 필수 필드 확인 및 기본값 설정
        cleaned_result = {
            "summary": str(result.get("summary", "")).strip(),
            "category": result.get("category", []) if isinstance(result.get("category"), list) else [],
            "assigned_group": result.get("assigned_group", "general_group"),
            "events": result.get("events", []) if isinstance(result.get("events"), list) else []
        }
        
        # 빈 값들 필터링
        cleaned_result["category"] = [
            cat for cat in cleaned_result["category"] 
            if isinstance(cat, str) and cat.strip() and cat.strip().lower() not in ['none', '']
        ]
        
        cleaned_result["events"] = [
            event for event in cleaned_result["events"] 
            if isinstance(event, str) and event.strip() and event.strip().lower() not in ['none', '']
        ]
        
        # 요약이 너무 짧거나 의미없는 경우 처리
        if len(cleaned_result["summary"]) < 10 or cleaned_result["summary"].lower() in ['none', 'n/a', 'not available']:
            logger.warning("요약이 너무 짧거나 의미없음")
            return None
        
        return cleaned_result
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON 파싱 오류: {e}")
        logger.error(f"원본 텍스트: {gpt_output[:200]}...")
        return None
    except Exception as e:
        logger.error(f"결과 파싱 중 오류: {e}")
        return None

def create_fallback_result(article: Dict) -> Dict:
    """분석 실패시 기본 결과 생성"""
    title = article.get("title", "")
    content = article.get("content", "")
    
    # 간단한 키워드 기반 카테고리 추출
    basic_categories = []
    keywords = [
        "bulk", "handy", "handymax", "supramax", "panamax", "capesize",
        "steel", "iron ore", "coal", "container", "freight", "rates"
    ]
    
    text_lower = (title + " " + content).lower()
    for keyword in keywords:
        if keyword in text_lower:
            basic_categories.append(keyword)
    
    # 요약 생성 (첫 200자)
    summary = content[:200].strip()
    if len(summary) > 197:
        summary = summary[:197] + "..."
    
    return {
        "summary": summary,
        "category": basic_categories[:5],  # 최대 5개
        "assigned_group": map_categories_to_groups(basic_categories),
        "events": []
    }

def analyze_article_with_retry(article: Dict) -> Optional[Dict]:
    """재시도 로직이 포함된 GPT 분석"""
    for attempt in range(MAX_RETRIES):
        try:
            title = article.get("title", "")
            content = article.get("content", "")
            
            # 프롬프트 구성
            prompt = f"Title: {title}\n\nContent: {content}"
            
            logger.info(f"GPT 분석 시도 {attempt + 1}/{MAX_RETRIES}: {title[:50]}...")
            
            # GPT API 호출
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": DOMAIN_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=1000,
                timeout=30  # 타임아웃 설정
            )
            
            gpt_output = response.choices[0].message.content.strip()
            logger.debug(f"GPT 원본 응답: {gpt_output[:200]}...")
            
            # 결과 파싱
            parsed_result = parse_gpt_output(gpt_output)
            
            if parsed_result:
                logger.info(f"GPT 분석 성공 (시도 {attempt + 1})")
                return parsed_result
            else:
                logger.warning(f"GPT 응답 파싱 실패 (시도 {attempt + 1})")
                
        except Exception as e:
            logger.error(f"GPT 분석 실패 (시도 {attempt + 1}): {e}")
            
            # 마지막 시도가 아니면 잠시 대기
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            continue
    
    logger.error(f"모든 재시도 실패, 폴백 결과 생성")
    return None

def analyze_article(article: Dict) -> Dict:
    """
    기사 분석 메인 함수
    
    Args:
        article: 분석할 기사 데이터
        
    Returns:
        분석 결과 딕셔너리
    """
    start_time = time.time()
    
    try:
        # 입력 검증
        if not validate_article_input(article):
            logger.error("입력 데이터 검증 실패")
            raise ValueError("유효하지 않은 기사 데이터")
        
        title = article.get("title", "")
        content = article.get("content", "")
        
        logger.info(f"기사 분석 시작: {title[:50]}...")
        
        # GPT 분석 시도
        gpt_result = analyze_article_with_retry(article)
        
        # 분석 실패시 폴백 결과 사용
        if not gpt_result:
            logger.warning("GPT 분석 실패, 폴백 결과 생성")
            gpt_result = create_fallback_result(article)
        
        # 카테고리와 그룹 처리
        category_list = gpt_result.get("category", [])
        assigned_groups = gpt_result.get("assigned_group")
        
        # 그룹 매핑 검증 및 보정
        if not assigned_groups or assigned_groups == "":
            assigned_groups = map_categories_to_groups(category_list)
        elif isinstance(assigned_groups, str):
            assigned_groups = [assigned_groups]
        
        # 최종 결과 구성
        result = {
            "title": title,
            "category": category_list,
            "assigned_group": assigned_groups,
            "events": gpt_result.get("events", []),
            "summary": gpt_result.get("summary", ""),
            "source_url": article.get("url", ""),
            "source": article.get("source", ""),
            "date": article.get("date", ""),
            "keywords": article.get("keywords", [])
        }
        
        # 처리 시간 로깅
        processing_time = time.time() - start_time
        logger.info(f"분석 완료 ({processing_time:.1f}초): 카테고리 {len(category_list)}개, 이벤트 {len(result['events'])}개")
        
        return result
        
    except Exception as e:
        logger.error(f"기사 분석 중 오류 발생: {e}")
        
        # 최종 폴백 - 최소한의 결과라도 반환
        return {
            "title": article.get("title", ""),
            "category": [],
            "assigned_group": ["general_group"],
            "events": [],
            "summary": article.get("content", "")[:200] + "..." if len(article.get("content", "")) > 200 else article.get("content", ""),
            "source_url": article.get("url", ""),
            "source": article.get("source", ""),
            "date": article.get("date", ""),
            "keywords": article.get("keywords", [])
        }

def batch_analyze_articles(articles: List[Dict], batch_size: int = 10) -> List[Dict]:
    """
    여러 기사를 배치로 분석
    
    Args:
        articles: 분석할 기사 리스트
        batch_size: 배치 크기
        
    Returns:
        분석 결과 리스트
    """
    results = []
    total_articles = len(articles)
    
    logger.info(f"배치 분석 시작: {total_articles}개 기사")
    
    for i in range(0, total_articles, batch_size):
        batch = articles[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (total_articles - 1) // batch_size + 1
        
        logger.info(f"배치 {batch_num}/{total_batches} 처리 중 ({len(batch)}개 기사)...")
        
        batch_results = []
        for j, article in enumerate(batch):
            try:
                result = analyze_article(article)
                batch_results.append(result)
                logger.info(f"  배치 내 진행: {j+1}/{len(batch)} 완료")
            except Exception as e:
                logger.error(f"  기사 분석 실패: {e}")
                continue
        
        results.extend(batch_results)
        
        # 배치 간 쿨다운 (API 제한 방지)
        if i + batch_size < total_articles:
            logger.info("배치 간 대기 중...")
            time.sleep(2)
    
    logger.info(f"배치 분석 완료: {len(results)}/{total_articles} 성공")
    return results

def analyze_article_quality(result: Dict) -> Dict:
    """분석 결과 품질 평가"""
    quality_score = 0
    issues = []
    
    # 요약 품질 확인
    summary = result.get("summary", "")
    if len(summary) >= 50:
        quality_score += 25
    else:
        issues.append("요약이 너무 짧음")
    
    # 카테고리 확인
    categories = result.get("category", [])
    if len(categories) >= 1:
        quality_score += 25
    else:
        issues.append("카테고리 없음")
    
    # 이벤트 확인
    events = result.get("events", [])
    if len(events) >= 1:
        quality_score += 25
    else:
        issues.append("이벤트 없음")
    
    # 그룹 할당 확인
    groups = result.get("assigned_group", [])
    if groups and groups != ["general_group"]:
        quality_score += 25
    else:
        issues.append("일반 그룹으로만 분류됨")
    
    return {
        "quality_score": quality_score,
        "issues": issues,
        "grade": "A" if quality_score >= 75 else "B" if quality_score >= 50 else "C"
    }

# 테스트 함수
def test_analyzer():
    """분석기 테스트"""
    test_article = {
        "title": "Supramax freight rates surge on strong steel demand",
        "content": "Supramax bulk carriers are experiencing significant rate increases as global steel production ramps up. The Baltic Dry Index has risen 15% this week, driven by strong demand from China and Europe. Iron ore shipments from Australia have increased substantially.",
        "url": "https://example.com/test",
        "source": "Test News",
        "date": "2024-08-04",
        "keywords": ["supramax", "steel", "rates"]
    }
    
    print("=== 분석기 테스트 ===")
    
    try:
        result = analyze_article(test_article)
        quality = analyze_article_quality(result)
        
        print(f"분석 결과:")
        print(f"- 요약: {result['summary'][:100]}...")
        print(f"- 카테고리: {result['category']}")
        print(f"- 그룹: {result['assigned_group']}")
        print(f"- 이벤트: {result['events']}")
        print(f"- 품질 점수: {quality['quality_score']}/100 ({quality['grade']})")
        print(f"- 이슈: {quality['issues']}")
        
    except Exception as e:
        print(f"테스트 실패: {e}")
    
    print("=== 테스트 완료 ===")

if __name__ == "__main__":
    test_analyzer()