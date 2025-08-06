# category_mapper.py

from typing import List, Set
import logging

CATEGORY_TO_GROUP = {
    # Steel Export Group (소형 벌크선, 철강 관련)
    "handy": "steel_export_group",
    "handymax": "steel_export_group", 
    "supramax": "steel_export_group",
    "bdi": "steel_export_group",
    "steel": "steel_export_group",
    "baltic": "steel_export_group",
    
    # Coal Import Group (대형 벌크선, 석탄/철광석 관련)
    "panamax": "coal_import_group",
    "capesize": "coal_import_group", 
    "coal": "coal_import_group",
    "iron ore": "coal_import_group",
    "ironore": "coal_import_group",  # 공백 없는 버전
    
    # Container Group (컨테이너 관련)
    "container": "container_group",
    "scfi": "container_group",
    "shipping schedule": "container_group",
    "boxship": "container_group",
    "teu": "container_group",
    
    # General shipping terms (일반 그룹으로 분류)
    "bulk": "general_group",
    "bulker": "general_group", 
    "dry bulk": "general_group",
    "freight": "general_group",
    "rates": "general_group",
    "charter": "general_group",
    "tonnage": "general_group",
    "vessel": "general_group",
    "shipping": "general_group",
    "maritime": "general_group",
    "port": "general_group",
    "cargo": "general_group",
    "demand": "general_group",
    "supply": "general_group"
}

def map_categories_to_groups(categories: List[str]) -> List[str]:
    """
    여러 category 키워드에 해당하는 그룹 목록 반환
    중복 제거하여 리턴
    """
    if not categories:
        return ["general_group"]
        
    groups: Set[str] = set()
    
    for cat in categories:
        if not cat:  # 빈 문자열 체크
            continue
            
        key = cat.lower().strip()
        
        # 정확히 일치하는 키워드 찾기
        if key in CATEGORY_TO_GROUP:
            groups.add(CATEGORY_TO_GROUP[key])
        else:
            # 부분 일치 검사 (예: "iron ore"가 "iron ore import" 내에 포함)
            for category_key, group in CATEGORY_TO_GROUP.items():
                if category_key in key or key in category_key:
                    groups.add(group)
                    break
    
    result = list(groups) if groups else ["general_group"]
    
    logging.debug(f"카테고리 매핑: {categories} → {result}")
    
    return result

def get_group_description(group_name: str) -> str:
    """그룹 설명 반환"""
    descriptions = {
        "steel_export_group": "철강 수출 관련 (소형 벌크선: Handy, Handymax, Supramax)",
        "coal_import_group": "석탄/철광석 수입 관련 (대형 벌크선: Panamax, Capesize)", 
        "container_group": "컨테이너 운송 관련",
        "general_group": "일반 해운/물류 관련"
    }
    return descriptions.get(group_name, "알 수 없는 그룹")

def get_all_groups() -> List[str]:
    """모든 가능한 그룹 목록 반환"""
    return ["steel_export_group", "coal_import_group", "container_group", "general_group"]