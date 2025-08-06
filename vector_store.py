# vector_store.py (개선 버전)
from pathlib import Path
from typing import List, Dict, Optional
import faiss
import numpy as np
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv
import os
import json
import datetime
import logging
import time

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# 전역 변수
EMBED = OpenAIEmbeddings(model="text-embedding-3-small")
INDEX_PATH = Path("vector_store/faiss.index")
META_PATH = Path("vector_store/metadata.jsonl")

def _create_empty_index(index_dim: int = 1536):
    """빈 FAISS 인덱스 생성"""
    try:
        idx = faiss.IndexFlatIP(index_dim)  # Inner Product (cosine similarity)
        idx = faiss.IndexIDMap(idx)  # ID 매핑 지원
        logger.info(f"새로운 FAISS 인덱스 생성 (차원: {index_dim})")
        return idx
    except Exception as e:
        logger.error(f"FAISS 인덱스 생성 실패: {e}")
        raise

def load_index():
    """FAISS 인덱스 로드"""
    try:
        if INDEX_PATH.exists():
            idx = faiss.read_index(str(INDEX_PATH))
            logger.info(f"FAISS 인덱스 로드 완료: {idx.ntotal}개 벡터")
            return idx
        else:
            logger.info("기존 인덱스 없음, 새로 생성")
            return _create_empty_index()
    except Exception as e:
        logger.error(f"인덱스 로드 실패: {e}")
        return _create_empty_index()

def save_index(idx):
    """FAISS 인덱스 저장"""
    try:
        INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(idx, str(INDEX_PATH))
        logger.info(f"FAISS 인덱스 저장 완료: {idx.ntotal}개 벡터")
    except Exception as e:
        logger.error(f"인덱스 저장 실패: {e}")
        raise

def validate_document(doc: Dict) -> bool:
    """문서 데이터 검증"""
    required_fields = ['title', 'summary']
    
    for field in required_fields:
        if not doc.get(field) or doc[field] in ['None', 'none', '']:
            logger.warning(f"문서 검증 실패: {field} 필드 누락 또는 빈 값")
            return False
    
    return True

def add_documents(docs: List[Dict], batch_size: int = 50):
    """
    문서들을 벡터스토어에 추가
    
    Args:
        docs: 문서 리스트
        batch_size: 배치 처리 크기
    """
    if not docs:
        logger.warning("추가할 문서가 없습니다")
        return
    
    # 문서 검증
    valid_docs = [doc for doc in docs if validate_document(doc)]
    if len(valid_docs) != len(docs):
        logger.warning(f"유효하지 않은 문서 {len(docs) - len(valid_docs)}개 제외")
    
    if not valid_docs:
        logger.error("유효한 문서가 없습니다")
        return
    
    try:
        idx = load_index()
        
        # 기존 메타데이터 로드
        existing_metas = []
        if META_PATH.exists():
            with open(META_PATH, 'r', encoding='utf-8') as f:
                existing_metas = f.read().splitlines()
        
        id_base = len(existing_metas)
        
        # 배치별로 처리
        for i in range(0, len(valid_docs), batch_size):
            batch_docs = valid_docs[i:i + batch_size]
            batch_vectors = []
            batch_ids = []
            batch_metas = []
            
            logger.info(f"배치 {i//batch_size + 1}/{(len(valid_docs)-1)//batch_size + 1} 처리 중...")
            
            for j, doc in enumerate(batch_docs):
                try:
                    # 임베딩할 텍스트 구성
                    text_parts = [
                        doc.get('title', ''),
                        doc.get('summary', ''),
                        ' '.join(doc.get('events', [])),
                        ' '.join(doc.get('category', []))
                    ]
                    text_for_embed = ' '.join(filter(None, text_parts))
                    
                    if not text_for_embed.strip():
                        logger.warning(f"문서 {id_base + i + j}: 임베딩할 텍스트 없음")
                        continue
                    
                    # 임베딩 생성
                    vector = np.array(EMBED.embed_query(text_for_embed), dtype='float32')
                    
                    # 벡터 정규화 (cosine similarity를 위해)
                    norm = np.linalg.norm(vector)
                    if norm > 0:
                        vector = vector / norm
                    
                    batch_vectors.append(vector)
                    batch_ids.append(id_base + i + j)
                    
                    # 메타데이터 정리
                    clean_meta = {
                        'title': str(doc.get('title', '')),
                        'summary': str(doc.get('summary', '')),
                        'category': doc.get('category', []),
                        'assigned_group': doc.get('assigned_group', []),
                        'events': doc.get('events', []),
                        'source_url': str(doc.get('source_url', '')),
                        'source': str(doc.get('source', '')),
                        'date': doc.get('date', datetime.datetime.now().strftime('%Y-%m-%d')),
                        'keywords': doc.get('keywords', [])
                    }
                    
                    batch_metas.append(json.dumps(clean_meta, ensure_ascii=False))
                    
                except Exception as e:
                    logger.error(f"문서 {id_base + i + j} 처리 실패: {e}")
                    continue
            
            # 배치를 인덱스에 추가
            if batch_vectors:
                try:
                    vectors_array = np.vstack(batch_vectors)
                    ids_array = np.array(batch_ids, dtype=np.int64)
                    
                    idx.add_with_ids(vectors_array, ids_array)
                    
                    # 메타데이터 저장
                    with open(META_PATH, 'a', encoding='utf-8') as f:
                        f.write('\n'.join(batch_metas) + '\n')
                    
                    logger.info(f"배치 완료: {len(batch_vectors)}개 문서 추가")
                    
                except Exception as e:
                    logger.error(f"배치 추가 실패: {e}")
                    continue
            
            # API 호출 제한을 위한 딜레이
            if i + batch_size < len(valid_docs):
                time.sleep(1)
        
        # 인덱스 저장
        save_index(idx)
        logger.info(f"전체 처리 완료: {len(valid_docs)}개 문서 추가")
        
    except Exception as e:
        logger.error(f"문서 추가 중 오류 발생: {e}")
        raise

def _apply_filters(meta: Dict, filters: Dict) -> bool:
    """필터 조건 적용"""
    try:
        # 이벤트 필터 (최우선)
        if filters.get("events"):
            events = meta.get("events", [])
            if not isinstance(events, list):
                return False
            if not any(event in filters["events"] for event in events):
                return False
        
        # 카테고리 필터
        if filters.get("category"):
            categories = meta.get("category", [])
            if not isinstance(categories, list):
                return False
            if not any(cat in filters["category"] for cat in categories):
                return False
        
        # 그룹 필터
        if filters.get("assigned_group"):
            groups = meta.get("assigned_group", [])
            if not isinstance(groups, list):
                return False
            if not any(group in filters["assigned_group"] for group in groups):
                return False
        
        # 날짜 필터
        if filters.get("date_range"):
            doc_date = meta.get("date", "")
            if not doc_date:
                return False
            try:
                doc_date_obj = datetime.datetime.strptime(doc_date, "%Y-%m-%d").date()
                start_date, end_date = filters["date_range"]
                if not (start_date <= doc_date_obj <= end_date):
                    return False
            except:
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"필터 적용 중 오류: {e}")
        return False

def search_articles(
    query: str,
    filters: Optional[Dict] = None,
    top_k: int = 5,
    similarity_threshold: float = 0.1
) -> List[Dict]:
    """
    벡터 유사도 기반 기사 검색
    
    Args:
        query: 검색 쿼리
        filters: 필터 조건
        top_k: 반환할 결과 수
        similarity_threshold: 유사도 임계값
    
    Returns:
        검색 결과 리스트
    """
    try:
        filters = filters or {}
        idx = load_index()
        
        if idx.ntotal == 0:
            logger.warning("인덱스가 비어있습니다")
            return []
        
        # 쿼리 임베딩
        query_vector = np.array(EMBED.embed_query(query), dtype="float32")
        norm = np.linalg.norm(query_vector)
        if norm > 0:
            query_vector = query_vector / norm
        
        # 검색 (여유분 확보)
        search_k = min(top_k * 5, idx.ntotal)
        scores, ids = idx.search(query_vector[None, :], k=search_k)
        
        # 메타데이터 로드
        if not META_PATH.exists():
            logger.error("메타데이터 파일이 없습니다")
            return []
        
        with open(META_PATH, 'r', encoding='utf-8') as f:
            meta_lines = f.read().splitlines()
        
        hits = []
        for doc_id, score in zip(ids[0], scores[0]):
            if doc_id == -1 or score < similarity_threshold:
                continue
            
            if doc_id >= len(meta_lines):
                logger.warning(f"메타데이터 인덱스 오류: {doc_id} >= {len(meta_lines)}")
                continue
            
            try:
                meta = json.loads(meta_lines[doc_id])
                
                # 필터 적용
                if _apply_filters(meta, filters):
                    meta["score"] = float(score)
                    meta["doc_id"] = int(doc_id)
                    hits.append(meta)
                
                if len(hits) >= top_k:
                    break
                    
            except json.JSONDecodeError as e:
                logger.error(f"메타데이터 파싱 오류 (ID: {doc_id}): {e}")
                continue
            except Exception as e:
                logger.error(f"문서 처리 오류 (ID: {doc_id}): {e}")
                continue
        
        # 정렬: 날짜(최신순) → 유사도(높은순)
        hits.sort(key=lambda x: (x.get("date", ""), x["score"]), reverse=True)
        
        logger.info(f"검색 완료: {len(hits)}개 결과 (쿼리: '{query[:50]}...')")
        return hits[:top_k]
        
    except Exception as e:
        logger.error(f"검색 중 오류 발생: {e}")
        return []

def get_index_stats() -> Dict:
    """인덱스 통계 정보 반환"""
    try:
        idx = load_index()
        
        # 메타데이터 통계
        meta_count = 0
        if META_PATH.exists():
            with open(META_PATH, 'r', encoding='utf-8') as f:
                meta_count = len(f.read().splitlines())
        
        return {
            "total_vectors": idx.ntotal,
            "vector_dimension": idx.d if hasattr(idx, 'd') else 1536,
            "metadata_count": meta_count,
            "index_size_mb": INDEX_PATH.stat().st_size / (1024 * 1024) if INDEX_PATH.exists() else 0,
            "metadata_size_mb": META_PATH.stat().st_size / (1024 * 1024) if META_PATH.exists() else 0
        }
        
    except Exception as e:
        logger.error(f"통계 조회 실패: {e}")
        return {
            "total_vectors": 0,
            "vector_dimension": 1536,
            "metadata_count": 0,
            "index_size_mb": 0,
            "metadata_size_mb": 0
        }

def rebuild_index():
    """인덱스 재구축 (문제 발생시 사용)"""
    try:
        logger.info("인덱스 재구축 시작...")
        
        if not META_PATH.exists():
            logger.error("메타데이터 파일이 없어 재구축할 수 없습니다")
            return False
        
        # 기존 인덱스 삭제
        if INDEX_PATH.exists():
            INDEX_PATH.unlink()
        
        # 메타데이터에서 문서 복원
        documents = []
        with open(META_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    doc = json.loads(line.strip())
                    documents.append(doc)
                except:
                    continue
        
        if not documents:
            logger.error("복원할 문서가 없습니다")
            return False
        
        # 메타데이터 파일 백업 후 삭제
        backup_path = META_PATH.with_suffix('.backup')
        META_PATH.rename(backup_path)
        
        # 문서 재추가
        add_documents(documents)
        
        # 백업 파일 삭제
        backup_path.unlink()
        
        logger.info(f"인덱스 재구축 완료: {len(documents)}개 문서")
        return True
        
    except Exception as e:
        logger.error(f"인덱스 재구축 실패: {e}")
        return False