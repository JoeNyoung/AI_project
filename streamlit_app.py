# streamlit_app.py (완전 개선 버전)
import streamlit as st
import pandas as pd
import json
import time
import difflib
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dotenv import load_dotenv
from vector_store import search_articles, META_PATH
from rag_chain import build_answer

# ---------- 페이지 설정 ----------
st.set_page_config(
    page_title="해운·철강 GPT Assistant",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------- 유틸리티 함수들 ----------
@st.cache_data(ttl=3600, show_spinner=False)
def safe_json_loads(json_str: str) -> Dict:
    """안전한 JSON 파싱"""
    try:
        if isinstance(json_str, str):
            return json.loads(json_str)
        return json_str if isinstance(json_str, dict) else {}
    except:
        return {}

@st.cache_data(ttl=1800, show_spinner=False)
def load_and_clean_metadata() -> pd.DataFrame:
    """메타데이터 로딩 및 기본 정리 (캐싱)"""
    if not META_PATH.exists():
        return pd.DataFrame()

    rows = []
    failed_count = 0
    
    try:
        with open(META_PATH, 'r', encoding='utf-8') as f:
            for line_num, raw_line in enumerate(f, 1):
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                    
                try:
                    data = json.loads(raw_line)
                    if not isinstance(data, dict):
                        continue
                    
                    # 필수 필드 검증
                    if not data.get('title') or not data.get('summary'):
                        continue
                    
                    # None 값들을 적절한 기본값으로 변환
                    cleaned_data = {
                        'title': str(data.get('title', '')).strip(),
                        'summary': str(data.get('summary', '')).strip(),
                        'date': data.get('date', datetime.now().strftime('%Y-%m-%d')),
                        'source': str(data.get('source', 'Unknown')),
                        'source_url': str(data.get('source_url', '')),
                        'category': data.get('category', []) if isinstance(data.get('category'), list) else [],
                        'assigned_group': data.get('assigned_group', []) if isinstance(data.get('assigned_group'), list) else [],
                        'events': data.get('events', []) if isinstance(data.get('events'), list) else []
                    }
                    
                    # 빈 문자열이나 'None' 문자열 필터링
                    if (cleaned_data['title'] in ['', 'None', 'none'] or 
                        cleaned_data['summary'] in ['', 'None', 'none']):
                        continue
                    
                    rows.append(cleaned_data)
                    
                except json.JSONDecodeError:
                    failed_count += 1
                    continue
                except Exception:
                    failed_count += 1
                    continue
    
    except Exception as e:
        st.error(f"메타데이터 파일 읽기 실패: {e}")
        return pd.DataFrame()
    
    if not rows:
        return pd.DataFrame()
    
    df = pd.DataFrame(rows)
    
    # 날짜 컬럼 정리
    df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.date
    df = df.dropna(subset=['date'])
    
    if failed_count > 0:
        st.info(f"📊 데이터 로딩 완료: {len(df)}개 성공, {failed_count}개 스킵")
    
    return df

def smart_deduplicate(df: pd.DataFrame, similarity_threshold: float = 0.85) -> pd.DataFrame:
    """지능형 중복 제거"""
    if df.empty:
        return df
    
    original_count = len(df)
    
    # 1단계: 정확한 제목 중복 제거
    df_clean = df.copy()
    df_clean['title_normalized'] = df_clean['title'].str.lower().str.strip()
    df_clean = df_clean.drop_duplicates(subset=['title_normalized'], keep='first')
    
    # 2단계: 유사한 제목 제거 (선택적)
    if similarity_threshold > 0:
        to_remove = set()
        titles = df_clean['title_normalized'].tolist()
        
        for i in range(len(titles)):
            if i in to_remove:
                continue
            for j in range(i + 1, len(titles)):
                if j in to_remove:
                    continue
                
                similarity = difflib.SequenceMatcher(None, titles[i], titles[j]).ratio()
                if similarity >= similarity_threshold:
                    # 더 긴 제목을 유지
                    if len(titles[i]) >= len(titles[j]):
                        to_remove.add(j)
                    else:
                        to_remove.add(i)
                        break
        
        if to_remove:
            df_clean = df_clean.drop(df_clean.index[list(to_remove)])
    
    # 임시 컬럼 제거
    df_result = df_clean.drop('title_normalized', axis=1).reset_index(drop=True)
    
    removed_count = original_count - len(df_result)
    if removed_count > 0:
        st.info(f"🔄 중복 제거: {removed_count}개 제거 ({original_count} → {len(df_result)})")
    
    return df_result

@st.cache_data(ttl=3600, show_spinner=False)
def translate_batch_optimized(texts: List[str], target_lang: str = 'ko') -> List[str]:
    """최적화된 배치 번역"""
    if not texts:
        return []
    
    # 이미 한글이 포함된 텍스트는 번역하지 않음
    texts_to_translate = []
    original_indices = []
    results = [''] * len(texts)
    
    for i, text in enumerate(texts):
        if not text or pd.isna(text):
            results[i] = text
            continue
            
        # 한글 포함 여부 체크
        has_korean = any('\uAC00' <= char <= '\uD7A3' for char in str(text))
        if has_korean:
            results[i] = text
            continue
        
        texts_to_translate.append(str(text))
        original_indices.append(i)
    
    if not texts_to_translate:
        return results
    
    try:
        from openai import OpenAI
        load_dotenv()
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # 배치 크기 제한 (토큰 제한 고려)
        batch_size = 10
        translated_results = []
        
        for i in range(0, len(texts_to_translate), batch_size):
            batch = texts_to_translate[i:i + batch_size]
            batch_text = "\n---SEP---\n".join(batch)
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system", 
                        "content": """해운/물류 전문 번역가입니다. 
                        영어 텍스트를 자연스러운 한국어로 번역하세요.
                        ---SEP---로 구분된 각 텍스트를 같은 구분자로 나누어 번역하세요.
                        전문 용어는 정확히 번역하되 읽기 쉽게 의역하세요."""
                    },
                    {"role": "user", "content": f"번역:\n\n{batch_text}"}
                ],
                temperature=0.2,
                max_tokens=2000
            )
            
            translated_batch = response.choices[0].message.content.strip()
            translated_list = translated_batch.split("---SEP---")
            
            # 결과 개수가 맞지 않으면 원본 사용
            if len(translated_list) != len(batch):
                translated_results.extend(batch)
            else:
                translated_results.extend([t.strip() for t in translated_list])
        
        # 결과 병합
        for i, translated in enumerate(translated_results):
            if i < len(original_indices):
                results[original_indices[i]] = translated
        
        return results
        
    except Exception as e:
        st.warning(f"번역 오류: {e}")
        return texts

def apply_translation(df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
    """데이터프레임에 번역 적용"""
    if df.empty:
        return df
    
    df_translated = df.copy()
    
    for column in columns:
        if column not in df_translated.columns:
            continue
        
        with st.spinner(f"🌐 {column} 번역 중..."):
            texts = df_translated[column].tolist()
            translated_texts = translate_batch_optimized(texts)
            
            # 번역 결과 저장
            df_translated[f'{column}_en'] = df_translated[column]
            df_translated[f'{column}_ko'] = translated_texts
            df_translated[column] = translated_texts  # 기본은 한국어
    
    return df_translated

def get_valid_filter_options(df: pd.DataFrame) -> Tuple[List[str], List[str]]:
    """유효한 필터 옵션 추출"""
    valid_categories = set()
    valid_events = set()
    
    if df.empty:
        return [], []
    
    # 해운 관련 키워드
    shipping_keywords = {
        'handy', 'handymax', 'supramax', 'panamax', 'capesize',
        'bulker', 'container', 'steel', 'iron ore', 'coal', 'grain',
        'freight', 'rates', 'bdi', 'scfi', 'baltic', 'shipping',
        'maritime', 'port', 'cargo', 'demand', 'supply', 'tonnage'
    }
    
    for _, row in df.iterrows():
        # 카테고리 처리
        categories = row.get('category', [])
        if isinstance(categories, list):
            for cat in categories:
                if isinstance(cat, str) and cat.strip():
                    cat_lower = cat.lower().strip()
                    if any(keyword in cat_lower for keyword in shipping_keywords):
                        valid_categories.add(cat.strip())
        
        # 이벤트 처리
        events = row.get('events', [])
        if isinstance(events, list):
            for event in events:
                if isinstance(event, str) and len(event.strip()) > 2:
                    event_clean = event.strip()
                    # 의미있는 이벤트만 필터링
                    if any(keyword in event_clean.lower() for keyword in ['운임', '급등', '하락', '증가', '감소', 'rate', 'surge', 'drop']):
                        valid_events.add(event_clean)
    
    return sorted(list(valid_categories)), sorted(list(valid_events))

def apply_filters(df: pd.DataFrame, filters: Dict) -> pd.DataFrame:
    """필터 적용"""
    if df.empty:
        return df
    
    filtered_df = df.copy()
    
    # 날짜 필터
    if filters.get('date_range') and len(filters['date_range']) == 2:
        start_date, end_date = filters['date_range']
        filtered_df = filtered_df[
            (filtered_df['date'] >= start_date) & 
            (filtered_df['date'] <= end_date)
        ]
    
    # 그룹 필터
    if filters.get('groups'):
        filtered_df = filtered_df[filtered_df['assigned_group'].apply(
            lambda groups: isinstance(groups, list) and 
                          any(group in filters['groups'] for group in groups)
        )]
    
    # 카테고리 필터
    if filters.get('categories'):
        filtered_df = filtered_df[filtered_df['category'].apply(
            lambda cats: isinstance(cats, list) and 
                        any(cat in filters['categories'] for cat in cats)
        )]
    
    # 이벤트 필터
    if filters.get('events'):
        filtered_df = filtered_df[filtered_df['events'].apply(
            lambda events: isinstance(events, list) and 
                          any(event in filters['events'] for event in events)
        )]
    
    return filtered_df

def display_article_cards(df: pd.DataFrame, translation_mode: str = "한국어", limit: int = 25):
    """기사 카드 형태로 표시"""
    for idx, row in df.head(limit).iterrows():
        with st.container():
            col1, col2 = st.columns([3, 1])
            
            with col1:
                # 제목 표시
                title = row.get('title', '')
                if translation_mode == "한국어":
                    st.markdown(f"**{title}**")
                elif translation_mode == "영어":
                    title_en = row.get('title_en', title)
                    st.markdown(f"**{title_en}**")
                else:  # 한국어+영어
                    st.markdown(f"**{title}**")
                    if 'title_en' in row and row.get('title_en'):
                        st.caption(f"🇺🇸 {row.get('title_en', '')}")
                
                # 요약 표시
                summary = row.get('summary', '')
                if len(summary) > 200:
                    summary = summary[:200] + "..."
                st.write(summary)
            
            with col2:
                # 메타 정보
                st.write(f"📅 {row.get('date', '')}")
                st.write(f"📰 {row.get('source', '')}")
                
                # 링크
                source_url = row.get('source_url', '')
                if source_url and source_url not in ['', 'None']:
                    st.link_button("🔗 원문", source_url)
                
                # 카테고리
                categories = row.get('category', [])
                if isinstance(categories, list) and categories:
                    valid_cats = [cat for cat in categories if cat and cat != 'None'][:3]
                    if valid_cats:
                        st.caption(f"🏷️ {', '.join(valid_cats)}")
            
            st.divider()

def typing_effect(text: str, placeholder):
    """타이핑 효과"""
    words = text.split()
    current_text = ""
    
    for i, word in enumerate(words):
        current_text += word + " "
        placeholder.write(current_text)
        if i < len(words) - 1:
            time.sleep(0.03)

# ---------- 세션 상태 초기화 ----------
if "user_info" not in st.session_state:
    st.session_state["user_info"] = None

if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

# ---------- 사용자 정보 입력 ----------
if st.session_state["user_info"] is None:
    st.title("👋 해운·철강 GPT Assistant")
    st.subheader("사용자 정보를 입력해주세요")
    
    col1, col2 = st.columns(2)
    
    with col1:
        groups = st.multiselect(
            "소속 그룹",
            options=["steel_export_group", "coal_import_group", "container_group"],
            default=[],
            help="소속된 업무 그룹을 선택하세요"
        )
    
    with col2:
        role = st.selectbox(
            "직책", 
            options=["사장", "실장", "그룹장", "리더", "담당자"],
            help="직책에 따라 답변 상세도가 조절됩니다"
        )
    
    if st.button("확인", type="primary"):
        if groups and role:
            st.session_state["user_info"] = {"groups": groups, "role": role}
            st.rerun()
        else:
            st.error("그룹과 직책을 모두 선택해주세요.")
    
    st.stop()

user = st.session_state["user_info"]

# ---------- 사이드바 ----------
with st.sidebar:
    st.markdown("### 👤 사용자 정보")
    st.write(f"**직책**: {user['role']}")
    st.write(f"**그룹**: {', '.join(user['groups'])}")
    
    if st.button("정보 변경"):
        st.session_state["user_info"] = None
        st.rerun()
    
    st.divider()
    
    # 시스템 상태
    st.markdown("### 📊 시스템 상태")
    
    if META_PATH.exists():
        file_size = META_PATH.stat().st_size / 1024
        st.success(f"✅ 데이터: {file_size:.1f} KB")
    else:
        st.error("❌ 데이터 없음")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key and len(api_key) > 10:
        st.success("✅ OpenAI 연결됨")
    else:
        st.warning("⚠️ API 미설정")
    
    st.divider()
    
    # 빠른 액션
    st.markdown("### ⚡ 빠른 액션")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 새로고침"):
            st.rerun()
    
    with col2:
        if st.button("🗑️ 캐시 삭제"):
            st.cache_data.clear()
            st.success("완료!")
            time.sleep(1)
            st.rerun()

# ---------- 탭 레이아웃 ----------
tab_dash, tab_chat = st.tabs(["📊 대시보드", "💬 챗봇"])

# ==== ① 대시보드 ====
with tab_dash:
    st.header("📊 기사 분석 대시보드")
    
    # 데이터 로딩
    with st.spinner("📂 데이터 로딩 중..."):
        df = load_and_clean_metadata()
    
    if df.empty:
        st.error("데이터가 없습니다. 다음을 실행해주세요:")
        st.code("python main.py\npython run_embedding_update.py")
        st.stop()
    
    # 기본 통계
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("총 기사", len(df))
    
    with col2:
        unique_sources = df['source'].nunique()
        st.metric("뉴스 소스", unique_sources)
    
    valid_categories, valid_events = get_valid_filter_options(df)
    
    with col3:
        st.metric("카테고리", len(valid_categories))
    
    with col4:
        st.metric("이벤트", len(valid_events))
    
    # 필터 설정
    st.subheader("🔍 필터 설정")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        date_range = st.date_input(
            "📅 날짜 범위",
            value=[],
            help="조회할 날짜 범위를 선택하세요"
        )
    
    with col2:
        available_groups = ["steel_export_group", "coal_import_group", "container_group", "general_group"]
        user_groups = user.get("groups", [])
        group_options = [g for g in available_groups if g in user_groups] if user_groups else available_groups
        
        selected_groups = st.multiselect(
            "👥 그룹",
            options=group_options,
            default=user_groups[:1] if user_groups else []
        )
    
    with col3:
        remove_duplicates = st.checkbox("🔄 중복 제거", value=True)
    
    col4, col5 = st.columns(2)
    
    with col4:
        selected_categories = st.multiselect(
            "🏷️ 카테고리",
            options=valid_categories,
            help=f"총 {len(valid_categories)}개 카테고리"
        )
    
    with col5:
        selected_events = st.multiselect(
            "📅 이벤트",
            options=valid_events,
            help=f"총 {len(valid_events)}개 이벤트"
        )
    
    # 번역 설정
    st.subheader("🌐 언어 설정")
    
    col1, col2 = st.columns(2)
    
    with col1:
        language_mode = st.radio(
            "표시 언어",
            options=["한국어", "영어", "한국어+영어"],
            index=0
        )
    
    with col2:
        auto_translate = st.checkbox(
            "🔄 자동 번역", 
            value=False,
            help="영어 기사를 한국어로 번역 (시간 소요)"
        )
    
    # 필터 적용
    filters = {
        'date_range': date_range if len(date_range) == 2 else None,
        'groups': selected_groups,
        'categories': selected_categories,
        'events': selected_events
    }
    
    filtered_df = apply_filters(df, filters)
    
    # 중복 제거
    if remove_duplicates:
        filtered_df = smart_deduplicate(filtered_df)
    
    # 번역 적용
    if auto_translate and not filtered_df.empty:
        filtered_df = apply_translation(filtered_df, ['title', 'summary'])
    
    # 결과 표시
    st.subheader(f"📰 결과 ({len(filtered_df)}건)")
    
    if filtered_df.empty:
        st.warning("조건에 맞는 기사가 없습니다.")
    else:
        # 표시 옵션
        col1, col2, col3 = st.columns(3)
        
        with col1:
            display_limit = st.selectbox(
                "표시 개수",
                options=[10, 25, 50, 100],
                index=1
            )
        
        with col2:
            sort_option = st.selectbox(
                "정렬",
                options=["날짜 (최신순)", "날짜 (오래된순)", "제목순"],
                index=0
            )
        
        with col3:
            view_mode = st.radio(
                "보기 형태",
                options=["카드", "테이블"],
                index=0
            )
        
        # 정렬 적용
        if sort_option == "날짜 (최신순)":
            filtered_df = filtered_df.sort_values('date', ascending=False)
        elif sort_option == "날짜 (오래된순)":
            filtered_df = filtered_df.sort_values('date', ascending=True)
        elif sort_option == "제목순":
            filtered_df = filtered_df.sort_values('title', ascending=True)
        
        # 결과 표시
        if view_mode == "카드":
            display_article_cards(filtered_df, language_mode, display_limit)
        else:
            # 테이블 보기
            display_columns = ["date", "title", "summary", "category", "source", "source_url"]
            if language_mode == "영어" and 'title_en' in filtered_df.columns:
                display_columns = ["date", "title_en", "summary_en", "category", "source", "source_url"]
            
            available_columns = [col for col in display_columns if col in filtered_df.columns]
            
            if available_columns:
                st.dataframe(
                    filtered_df[available_columns].head(display_limit),
                    use_container_width=True,
                    hide_index=True
                )
        
        # 다운로드 옵션
        col1, col2 = st.columns(2)
        
        with col1:
            csv_data = filtered_df.head(display_limit).to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                "📥 CSV 다운로드",
                data=csv_data,
                file_name=f"해운뉴스_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )
        
        with col2:
            json_data = filtered_df.head(display_limit).to_json(orient='records', force_ascii=False, indent=2)
            st.download_button(
                "📥 JSON 다운로드",
                data=json_data,
                file_name=f"해운뉴스_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                mime="application/json"
            )

# ==== ② 챗봇 ====
with tab_chat:
    st.header("💬 RAG 기반 해운·철강 어시스턴트")
    st.caption(f"설정: {user['role']} | 그룹: {', '.join(user['groups'])}")
    
    # 채팅 히스토리 표시
    for msg in st.session_state["chat_history"]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
    
    # 질문 예시
    with st.expander("💡 질문 예시"):
        examples = [
            "최근 supramax 운임 동향은?",
            "iron ore 관련 최신 뉴스는?",
            "BDI 지수 변화 요인은?",
            "capesize 선박 시장 전망은?",
            "container shipping 이슈는?"
        ]
        
        for example in examples:
            if st.button(example, key=f"ex_{hash(example)}"):
                st.session_state.example_question = example
    
    # 질문 입력
    prompt = st.chat_input("질문을 입력하세요...")
    
    # 예시 질문 처리
    if hasattr(st.session_state, 'example_question'):
        prompt = st.session_state.example_question
        delattr(st.session_state, 'example_question')
    
    if prompt:
        # 사용자 메시지
        with st.chat_message("user"):
            st.write(prompt)
        
        # AI 응답
        with st.chat_message("assistant"):
            with st.spinner("답변 생성 중..."):
                try:
                    answer = build_answer(
                        prompt,
                        user_meta={
                            "role": user["role"],
                            "groups": user["groups"],
                            "filters": {}
                        }
                    )
                    
                    # 타이핑 효과
                    answer_placeholder = st.empty()
                    typing_effect(answer, answer_placeholder)
                    
                except Exception as e:
                    st.error(f"답변 생성 오류: {str(e)}")
                    answer = "죄송합니다. 답변을 생성할 수 없습니다."
        
        # 채팅 히스토리에 추가
        st.session_state["chat_history"].append({"role": "user", "content": prompt})
        st.session_state["chat_history"].append({"role": "assistant", "content": answer})
    
    # 채팅 기록 관리
    if st.session_state["chat_history"]:
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🗑️ 채팅 기록 초기화"):
                st.session_state["chat_history"] = []
                st.rerun()
        
        with col2:
            chat_count = len(st.session_state["chat_history"]) // 2
            st.write(f"💬 대화 수: {chat_count}개")