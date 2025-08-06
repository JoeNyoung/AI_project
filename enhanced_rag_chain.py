# enhanced_rag_chain.py

import os
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from openai import OpenAI
from dotenv import load_dotenv
import langdetect
from vector_store import search_articles

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class EnhancedRAGChain:
    """개선된 하이브리드 RAG 시스템"""
    
    def __init__(self):
        self.client = client
        self.domain_knowledge_base = self._load_domain_knowledge()
        
    def _load_domain_knowledge(self) -> Dict:
        """해운/철강 도메인 기본 지식 베이스"""
        return {
            "vessel_types": {
                "capesize": "180,000 DWT 이상의 대형 벌크선. 주로 철광석, 석탄 운송",
                "panamax": "65,000-80,000 DWT 벌크선. 파나마 운하 통과 가능한 최대 크기",
                "supramax": "50,000-65,000 DWT 벌크선. 중간 규모 화물 운송",
                "handysize": "10,000-40,000 DWT 소형 벌크선. 소규모 항만 접근 가능"
            },
            "market_indices": {
                "bdi": "Baltic Dry Index - 건화물선 종합 운임 지수",
                "scfi": "Shanghai Containerized Freight Index - 상하이 컨테이너 운임 지수"
            },
            "commodities": {
                "iron_ore": "철광석 - 제철 원료, 주요 수출국: 호주, 브라질",
                "coal": "석탄 - 발전/제철용, 주요 수출국: 호주, 인도네시아",
                "grain": "곡물 - 밀, 옥수수, 대두 등"
            }
        }
    
    def analyze_query_type(self, query: str) -> Dict:
        """질문 유형 분석"""
        query_lower = query.lower()
        
        analysis = {
            "needs_realtime_data": False,
            "needs_domain_knowledge": False,
            "needs_market_analysis": False,
            "query_type": "general",
            "confidence_threshold": 0.7
        }
        
        # 실시간 데이터가 필요한 질문
        realtime_keywords = ['최근', '현재', '오늘', '이번주', '지금', 'recent', 'current', 'today']
        if any(keyword in query_lower for keyword in realtime_keywords):
            analysis["needs_realtime_data"] = True
            analysis["query_type"] = "realtime"
        
        # 기본 도메인 지식이 필요한 질문
        domain_keywords = ['뭐야', '무엇', '설명', '차이', 'what is', 'explain', 'difference']
        if any(keyword in query_lower for keyword in domain_keywords):
            analysis["needs_domain_knowledge"] = True
            analysis["query_type"] = "definition"
        
        # 시장 분석이 필요한 질문
        analysis_keywords = ['전망', '예측', '분석', '영향', 'forecast', 'predict', 'analysis', 'impact']
        if any(keyword in query_lower for keyword in analysis_keywords):
            analysis["needs_market_analysis"] = True
            analysis["query_type"] = "analysis"
            analysis["confidence_threshold"] = 0.8  # 더 높은 신뢰도 요구
        
        return analysis
    
    def search_domain_knowledge(self, query: str) -> str:
        """도메인 지식 베이스에서 검색"""
        query_lower = query.lower()
        relevant_info = []
        
        # 선박 유형 검색
        for vessel_type, description in self.domain_knowledge_base["vessel_types"].items():
            if vessel_type in query_lower:
                relevant_info.append(f"**{vessel_type.title()}**: {description}")
        
        # 시장 지수 검색
        for index_name, description in self.domain_knowledge_base["market_indices"].items():
            if index_name in query_lower or index_name.upper() in query.upper():
                relevant_info.append(f"**{index_name.upper()}**: {description}")
        
        # 원자재 검색
        for commodity, description in self.domain_knowledge_base["commodities"].items():
            if commodity.replace('_', ' ') in query_lower:
                relevant_info.append(f"**{commodity.replace('_', ' ').title()}**: {description}")
        
        return "\n".join(relevant_info) if relevant_info else ""
    
    def build_enhanced_answer(self, query: str, user_meta: Dict) -> Tuple[str, Dict]:
        """개선된 답변 생성"""
        
        # 1) 질문 유형 분석
        query_analysis = self.analyze_query_type(query)
        logging.info(f"질문 분석: {query_analysis}")
        
        # 2) 벡터 검색 (항상 실행)
        vector_results = search_articles(
            query, 
            filters=user_meta.get("filters", {}), 
            top_k=5
        )
        
        # 3) 도메인 지식 검색
        domain_info = ""
        if query_analysis["needs_domain_knowledge"]:
            domain_info = self.search_domain_knowledge(query)
        
        # 4) 컨텍스트 구성
        context_parts = []
        
        # 벡터 검색 결과
        if vector_results:
            context_parts.append("[최신 뉴스 정보]")
            for i, result in enumerate(vector_results, 1):
                context_parts.append(f"{i}. 제목: {result['title']}")
                context_parts.append(f"   요약: {result['summary']}")
                context_parts.append(f"   출처: {result['source_url']}")
                context_parts.append("")
        
        # 도메인 지식
        if domain_info:
            context_parts.append("[기본 지식 정보]")
            context_parts.append(domain_info)
            context_parts.append("")
        
        # 5) 프롬프트 구성
        system_prompt = self._build_system_prompt(user_meta, query_analysis)
        user_prompt = self._build_user_prompt(query, context_parts, query_analysis)
        
        # 6) GPT 호출
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3
            )
            
            answer = response.choices[0].message.content.strip()
            
        except Exception as e:
            logging.error(f"GPT 호출 실패: {e}")
            answer = "죄송합니다. 일시적으로 답변을 생성할 수 없습니다."
        
        # 7) 출처 및 메타데이터 추가
        metadata = {
            "query_type": query_analysis["query_type"],
            "vector_results_count": len(vector_results),
            "has_domain_knowledge": bool(domain_info),
            "confidence": self._calculate_confidence(vector_results, domain_info, query_analysis)
        }
        
        # 8) 출처 정보 추가
        if vector_results:
            sources = [f"- {r['title']} ({r['source']}) → {r['source_url']}" for r in vector_results]
            answer += "\n\n**📰 관련 기사:**\n" + "\n".join(sources)
        
        # 신뢰도가 낮은 경우 경고 추가
        if metadata["confidence"] < query_analysis["confidence_threshold"]:
            answer += f"\n\n⚠️ *이 답변은 제한된 정보를 바탕으로 작성되었습니다. 추가 확인이 필요할 수 있습니다.*"
        
        return answer, metadata
    
    def _build_system_prompt(self, user_meta: Dict, query_analysis: Dict) -> str:
        """동적 시스템 프롬프트 생성"""
        
        base_prompt = f"""당신은 해운/물류/철강 전문 AI 어시스턴트입니다.
사용자 직책: {user_meta.get('role', '담당자')}
소속 그룹: {', '.join(user_meta.get('groups', ['general']))}

답변 지침:
"""
        
        # 직책별 답변 깊이
        role = user_meta.get('role', '담당자')
        if role in ['사장', '실장']:
            base_prompt += "- 전략적 관점에서 핵심 요점 중심으로 답변\n"
        elif role == '그룹장':
            base_prompt += "- 관리적 관점에서 실행 가능한 인사이트 제공\n"
        elif role == '리더':
            base_prompt += "- 실무진을 위한 구체적이고 상세한 설명 포함\n"
        else:  # 담당자
            base_prompt += "- 최대한 자세하고 친절하게 설명\n"
        
        # 질문 유형별 지침
        if query_analysis["query_type"] == "realtime":
            base_prompt += "- 최신 정보 우선, 시점 명확히 표기\n"
        elif query_analysis["query_type"] == "definition":
            base_prompt += "- 기본 개념부터 차근차근 설명\n"
        elif query_analysis["query_type"] == "analysis":
            base_prompt += "- 다각도 분석, 위험 요소 및 기회 요소 모두 언급\n"
        
        base_prompt += """
중요 원칙:
1. 제공된 최신 뉴스 정보를 우선적으로 활용
2. 출처가 불분명한 정보는 추측성 답변임을 명시
3. 전문 용어 사용시 간단한 설명 병행
4. 불확실한 정보는 솔직히 모른다고 답변
"""
        
        return base_prompt
    
    def _build_user_prompt(self, query: str, context_parts: List[str], query_analysis: Dict) -> str:
        """사용자 프롬프트 구성"""
        
        # 언어 감지
        try:
            lang = langdetect.detect(query)
            lang_instruction = "[한국어로 답변]" if lang == 'ko' else "[English Response]"
        except:
            lang_instruction = "[한국어로 답변]"
        
        prompt = f"""{lang_instruction}

질문: {query}

"""
        
        # 컨텍스트 추가
        if context_parts:
            prompt += "참고 정보:\n" + "\n".join(context_parts) + "\n"
        else:
            prompt += "참고 정보: 관련 최신 뉴스가 없습니다. 일반적인 해운/철강 지식을 바탕으로 답변해주세요.\n"
        
        # 특별 지침
        if query_analysis["query_type"] == "analysis":
            prompt += "\n분석 요청: 가능한 여러 시나리오와 리스크 요소를 고려하여 균형잡힌 분석을 제공해주세요."
        
        return prompt
    
    def _calculate_confidence(self, vector_results: List, domain_info: str, query_analysis: Dict) -> float:
        """답변 신뢰도 계산"""
        confidence = 0.3  # 기본 신뢰도
        
        # 벡터 검색 결과가 있으면 신뢰도 증가
        if vector_results:
            confidence += 0.4
            # 관련성이 높은 결과가 많을수록 신뢰도 증가
            confidence += min(len(vector_results) * 0.1, 0.2)
        
        # 도메인 지식이 있으면 신뢰도 증가
        if domain_info:
            confidence += 0.2
        
        # 질문 유형별 조정
        if query_analysis["query_type"] == "definition":
            confidence += 0.1  # 정의 질문은 상대적으로 안정적
        elif query_analysis["query_type"] == "realtime":
            if not vector_results:
                confidence -= 0.2  # 실시간 정보 없으면 신뢰도 하락
        
        return min(confidence, 1.0)

# 기존 함수 대체
def build_answer(query: str, user_meta: Dict) -> str:
    """기존 함수와 호환되는 인터페이스"""
    enhanced_rag = EnhancedRAGChain()
    answer, metadata = enhanced_rag.build_enhanced_answer(query, user_meta)
    
    # 로깅
    logging.info(f"답변 메타데이터: {metadata}")
    
    return answer

# 고급 답변 함수 (메타데이터 포함)
def build_enhanced_answer(query: str, user_meta: Dict) -> Tuple[str, Dict]:
    """메타데이터를 포함한 고급 답변 생성"""
    enhanced_rag = EnhancedRAGChain()
    return enhanced_rag.build_enhanced_answer(query, user_meta)