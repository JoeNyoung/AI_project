"""
벡터스토어 검색 단위 테스트
python debug/debug_vector.py "쿼리" --events "운임 급등" --cat supramax
"""
import argparse, json, textwrap, pprint
from vector_store import search_articles

parser = argparse.ArgumentParser()
parser.add_argument("query", help="검색 질의")
parser.add_argument("--events", nargs="*", default=[])
parser.add_argument("--cat",    nargs="*", default=[])
parser.add_argument("--grp",    nargs="*", default=[])
parser.add_argument("--topk",   type=int,  default=5)
args = parser.parse_args()

filters = {}
if args.events: filters["events"] = args.events
if args.cat:    filters["category"] = args.cat
if args.grp:    filters["assigned_group"] = args.grp

hits = search_articles(args.query, filters=filters, top_k=args.topk)
print(f"\n🔎 결과 {len(hits)}건\n" + "-"*60)
for h in hits:
    pprint.pprint(h)
    print("-"*60)