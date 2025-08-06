"""
RAG 파이프라인 + GPT 응답 테스트
python debug/debug_rag.py "질문 내용"
"""
import argparse, textwrap
from rag_chain import build_answer

parser = argparse.ArgumentParser()
parser.add_argument("question", help="사용자 질문")
parser.add_argument("--role", default="담당자", choices=["사장","실장","그룹장","리더","담당자"])
parser.add_argument("--groups", nargs="*", default=["steel_export_group"])
args = parser.parse_args()

user_meta = {
    "role":   args.role,
    "groups": args.groups,
    "filters": {}          # 필요하면 events/category 필터 추가
}

print("🧪 RAG 응답 생성 중...\n")
answer = build_answer(args.question, user_meta)
print(textwrap.fill(answer, 120))