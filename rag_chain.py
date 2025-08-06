# rag_chain.py (개선 버전)
from openai import OpenAI
from dotenv import load_dotenv
import os
import textwrap
import langdetect
import logging
from typing import Dict, List, Tuple
from vector_store import search_articles

# 로깅 설정
logger = logging.getLogger(__name__)

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 시스템 프롬프트 개선
ENHANCED_SYSTEM_PROMPT = """
당신은 해운/물류/철강 산업의 전문 AI 어시스턴트입니다.

## 역할별 답변 가이드:
- **사장/실장**: 전략적 관점, 핵심 포인트 중심, 간결하고 임팩트 있게
- **그룹장**: 관리적 관점, 실행 가능한 액션 아이템 포함
- **리더**: 팀 관리 + 실무 세부사항, 균형잡힌 상세도
- **담당자**: 최대한 상세하고 친절하게, 용어 설명 포함

## 답변 원칙:
1. 제공된 최신 뉴스 정보를 우선적으로 활용
2. 정보가 불충분한 경우 명시적으로 언급
3. 전문 용어 사용시 간단한 설명 병행
4. 다각도 분석 (기회 요소와 위험 요소 모두 언급)
5. 출처가 불분명한 추측은 피하고 팩트 기반 답변

## 특별 지침:
- 수치나 데이터 언급시 출처 명시
- 전망이나 예측시 불확실성 인정
- 사용자의 비즈니스 그룹과 관련성 높은 정보 우선 제공
"""

def detect_language(text: str) -> str:
    """언어 감지 (개선된 버전)"""
    try:
        # 한글 문자 비율 체크
        korean_chars = sum(1 for char in text if '\uAC00' <= char <= '\uD7A3')
        total_chars = len([char for char in text if char.isalpha()])
        
        if total_chars > 0 and korean_chars / total_chars > 0.3:
            return "ko"
        
        # langdetect 라이브러리 사용
        detected = langdetect.detect(text)
        return detected
        
    except Exception:
        # 기본값은 한국어
        return "ko"

def analyze_query_intent(query: str, user_meta: Dict) -> Dict:
    """쿼리 의도 분석"""
    query_lower = query.lower()
    
    intent = {
        "type": "general",
        "urgency": "normal",
        "scope": "general",
        "requires_recent_data": False,
        "technical_level": "medium"
    }
    
    # 시급성 키워드
    urgent_keywords = ['긴급', '즉시', 'urgent', 'immediate', '오늘', 'today']
    if any(keyword in query_lower for keyword in urgent_keywords):
        intent["urgency"] = "high"
    
    # 최신 정보 필요성
    recent_keywords = ['최근', '현재', '지금', '요즘', 'recent', 'current', 'latest']
    if any(keyword in query_lower for keyword in recent_keywords):
        intent["requires_recent_data"] = True
    
    # 쿼리 유형 분류
    if any(word in query_lower for word in ['전망', '예측', 'forecast', 'outlook']):
        intent["type"] = "forecast"
    elif any(word in query_lower for word in ['분석', '영향', 'analysis', 'impact']):
        intent["type"] = "analysis"
    elif any(word in query_lower for word in ['무엇', '뭐야', 'what is', 'explain']):
        intent["type"] = "definition"
    elif any(word in query_lower for word in ['어떻게', 'how to', '방법']):
        intent["type"] = "how_to"
    
    # 기술적 수준 (직책 기반 조정)
    role = user_meta.get("role", "담당자")
    if role in ["사장", "실장"]:
        intent["technical_level"] = "low"  # 간단한 설명
    elif role == "그룹장":
        intent["technical_level"] = "medium"
    else:  # 리더, 담당자
        intent["technical_level"] = "high"  # 상세한 설명
    
    return intent

def build_context_from_search(search_results: List[Dict], user_meta: Dict) -> str:
    """검색 결과를 컨텍스트로 구성"""
    if not search_results:
        return "관련된 최신 뉴스 정보가 없습니다."
    
    context_parts = []
    user_groups = user_meta.get("groups", [])
    
    # 사용자 그룹과 관련성 높은 순으로 정렬
    def relevance_score(result):
        score = result.get("score", 0)
        
        # 사용자 그룹과 일치하는 경우 가산점
        result_groups = result.get("assigned_group", [])
        if isinstance(result_groups, list):
            group_match = len(set(user_groups) & set(result_groups))
            score += group_match * 0.1
        
        return score
    
    sorted_results = sorted(search_results, key=relevance_score, reverse=True)
    
    context_parts.append("=== 관련 최신 뉴스 정보 ===")
    
    for i, result in enumerate(sorted_results[:5], 1):
        title = result.get("title", "")
        summary = result.get("summary", "")
        date = result.get("date", "")
        source = result.get("source", "")
        
        context_part = f"""
[뉴스 {i}]
제목: {title}
요약: {summary}
날짜: {date}
출처: {source}
"""
        context_parts.append(context_part.strip())
    
    return "\n\n".join(context_parts)

def build_system_message(user_meta: Dict, query_intent: Dict) -> str:
    """동적 시스템 메시지 생성"""
    role = user_meta.get("role", "담당자")
    groups = user_meta.get("groups", [])
    
    system_msg = ENHANCED_SYSTEM_PROMPT
    
    # 현재 사용자 정보 추가
    system_msg += f"\n\n## 현재 사용자 정보:"
    system_msg += f"\n- 직책: {role}"
    system_msg += f"\n- 소속 그룹: {', '.join(groups)}"
    
    # 쿼리 의도에 따른 특별 지침
    if query_intent["type"] == "forecast":
        system_msg += "\n\n## 특별 지침 (전망/예측):"
        system_msg += "\n- 과거 데이터와 현재 트렌드를 기반으로 분석"
        system_msg += "\n- 불확실성과 리스크 요소 명시"
        system_msg += "\n- 여러 시나리오 고려"
    
    elif query_intent["type"] == "analysis":
        system_msg += "\n\n## 특별 지침 (분석):"
        system_msg += "\n- 다각도 분석 (기술적, 경제적, 정치적 요인)"
        system_msg += "\n- 단기/중기/장기 영향 구분"
        system_msg += "\n- 정량적 데이터와 정성적 분석 병행"
    
    elif query_intent["type"] == "definition":
        system_msg += "\n\n## 특별 지침 (정의/설명):"
        system_msg += "\n- 기본 개념부터 차근차근 설명"
        system_msg += "\n- 실제 사례나 예시 포함"
        system_msg += "\n- 관련 용어나 개념도 함께 설명"
    
    # 기술적 수준 조정
    if query_intent["technical_level"] == "low":
        system_msg += "\n- 전문 용어 최소화, 핵심만 간단히"
    elif query_intent["technical_level"] == "high":
        system_msg += "\n- 상세한 설명과 기술적 세부사항 포함"
    
    return system_msg

def build_user_message(query: str, context: str, query_intent: Dict) -> str:
    """사용자 메시지 구성"""
    language = detect_language(query)
    lang_instruction = "[한국어로 답변]" if language == "ko" else "[Answer in English]"
    
    user_msg = f"{lang_instruction}\n\n"
    user_msg += f"질문: {query}\n\n"
    user_msg += f"참고 정보:\n{context}\n\n"
    
    # 쿼리 의도별 추가 지침
    if query_intent["urgency"] == "high":
        user_msg += "⚠️ 이 질문은 시급한 사안입니다. 핵심 포인트를 우선적으로 답변해주세요.\n\n"
    
    if query_intent["requires_recent_data"]:
        user_msg += "📅 최신 정보가 중요한 질문입니다. 제공된 뉴스의 날짜를 확인하고 최신성을 고려해주세요.\n\n"
    
    return user_msg

def format_sources(search_results: List[Dict]) -> str:
    """출처 정보 포맷팅"""
    if not search_results:
        return ""
    
    sources = []
    for i, result in enumerate(search_results, 1):
        title = result.get("title", "")
        source = result.get("source", "")
        url = result.get("source_url", "")
        date = result.get("date", "")
        
        if url and url != "":
            source_line = f"{i}. **{title}** ({source}, {date}) → [링크]({url})"
        else:
            source_line = f"{i}. **{title}** ({source}, {date})"
        
        sources.append(source_line)
    
    return "\n\n**📰 참고 기사:**\n" + "\n".join(sources)

def build_answer(query: str, user_meta: Dict) -> str:
    """개선된 RAG 답변 생성"""
    try:
        # 1단계: 쿼리 의도 분석
        query_intent = analyze_query_intent(query, user_meta)
        logger.info(f"쿼리 의도 분석: {query_intent}")
        
        # 2단계: 벡터 검색
        search_filters = {
            "assigned_group": user_meta.get("groups", [])
        }
        
        # 최신 정보가 필요한 경우 더 많은 결과 검색
        top_k = 7 if query_intent["requires_recent_data"] else 5
        
        search_results = search_articles(
            query, 
            filters=search_filters, 
            top_k=top_k
        )
        
        logger.info(f"검색 결과: {len(search_results)}개")
        
        # 3단계: 컨텍스트 구성
        context = build_context_from_search(search_results, user_meta)
        
        # 4단계: 프롬프트 구성
        system_message = build_system_message(user_meta, query_intent)
        user_message = build_user_message(query, context, query_intent)
        
        # 5단계: GPT 호출
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            temperature=0.3,
            max_tokens=1500
        )
        
        answer = response.choices[0].message.content.strip()
        
        # 6단계: 출처 정보 추가
        sources = format_sources(search_results)
        
        # 7단계: 답변 품질 검증 및 경고
        quality_warnings = []
        
        if len(search_results) == 0:
            quality_warnings.append("⚠️ *관련 최신 뉴스가 없어 일반적인 지식을 바탕으로 답변했습니다.*")
        elif len(search_results) < 3:
            quality_warnings.append("⚠️ *제한적인 정보를 바탕으로 작성된 답변입니다.*")
        
        if query_intent["requires_recent_data"] and search_results:
            # 최신 기사가 얼마나 최근인지 확인
            try:
                from datetime import datetime, timedelta
                latest_date = max(
                    datetime.strptime(result.get("date", "2020-01-01"), "%Y-%m-%d") 
                    for result in search_results
                )
                if datetime.now() - latest_date > timedelta(days=7):
                    quality_warnings.append("⚠️ *최신 정보가 1주일 이상 오래되었습니다.*")
            except:
                pass
        
        # 최종 답변 구성
        final_answer = answer
        
        if sources:
            final_answer += sources
        
        if quality_warnings:
            final_answer += "\n\n" + "\n".join(quality_warnings)
        
        return final_answer
        
    except Exception as e:
        logger.error(f"답변 생성 중 오류: {e}")
        
        # 폴백 답변
        fallback_answer = f"""죄송합니다. 답변 생성 중 기술적 문제가 발생했습니다.

**문제 해결 방법:**
1. 잠시 후 다시 시도해보세요
2. 질문을 더 구체적으로 바꿔보세요
3. 시스템 관리자에게 문의하세요

**오류 정보:** {str(e)[:100]}"""
        
        return fallback_answer

def validate_api_connection() -> bool:
    """OpenAI API 연결 상태 확인"""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=5
        )
        return True
    except Exception as e:
        logger.error(f"API 연결 실패: {e}")
        return False

# 하위 호환성을 위한 기존 함수들
def detect_lang(text: str) -> str:
    """기존 함수명 호환성 유지"""
    return detect_language(text)

# 테스트 함수
def test_rag_system():
    """RAG 시스템 테스트"""
    test_queries = [
        "최근 supramax 운임 동향은?",
        "BDI 지수가 상승하는 이유는?",
        "container shipping 시장 전망은?"
    ]
    
    test_user = {
        "role": "담당자",
        "groups": ["steel_export_group"],
        "filters": {}
    }
    
    print("=== RAG 시스템 테스트 ===")
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. 테스트 쿼리: {query}")
        try:
            answer = build_answer(query, test_user)
            print(f"답변 길이: {len(answer)} 문자")
            print(f"답변 미리보기: {answer[:200]}...")
        except Exception as e:
            print(f"오류: {e}")
    
    print("\n=== 테스트 완료 ===")

if __name__ == "__main__":
    test_rag_system()