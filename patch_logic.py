import os

filepath = r"c:\Users\wugi2\Desktop\Project\Items\coupang-calculator\calc_logic.py"

with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if "processed_list.sort(key=lambda x: x['unitPrice'])" in line:
        skip = True
        
        # 주입할 로직
        replacement = """    # 4. 세부 속성이 완전히 같은 그룹끼리 묶기
    grouped_data = {}
    for item in processed_list:
        group_key = f"{item.get('brand','')} {item.get('line','')} {item.get('type','')} {item.get('stage','')} {item.get('gender','')}"
        if group_key not in grouped_data:
            grouped_data[group_key] = []
        grouped_data[group_key].append(item)

    if not grouped_data:
        print("분석 가능한 유효한 상품이 없습니다.")
        return

    # 5. 가장 많은 상품이 묶인(검색 메인 타겟일 확률이 높은) 그룹을 선택
    best_group_key = max(grouped_data.keys(), key=lambda k: len(grouped_data[k]))
    best_group_list = grouped_data[best_group_key]

    print(f"\\n💡 메인 상품 그룹 선정: [{best_group_key}] (총 {len(best_group_list)}개 상품)")
    print("해당 그룹 내에서만 1장당 단가 기준으로 순위를 매깁니다.")

    # 6. 해당 그룹 안에서만 1장당 가격 오름차순 정렬
    best_group_list.sort(key=lambda x: x['unitPrice'])
    
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(best_group_list, f, ensure_ascii=False, indent=2)
        
    print(f"✅ 데이터 정제 완료! 결과가 {output_file_path}에 저장되었습니다. (총 {len(best_group_list)}건)")
"""
        new_lines.append(replacement)
    
    if skip and "process_data()" in line:
        skip = False # 끝부분
        
    if not skip:
        new_lines.append(line)

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print("성공적으로 변경되었습니다!")
