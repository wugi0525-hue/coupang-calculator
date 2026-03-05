import os
import sys
import json
import glob
import re

# 윈도우 콘솔 한글 인코딩 에러 방지
sys.stdout.reconfigure(encoding='utf-8')

# 8개 카테고리 파일명에 따른 고정 속성 매핑 (LLM 호출 제거 및 속도 최적화)
CATEGORY_MAP = {
    "1_huggies_naturemade_pants_3_boys.json":  {"brand": "하기스", "line": "네이처메이드", "type": "팬티형", "stage": "3단계", "gender": "남아용"},
    "2_huggies_naturemade_pants_3_girls.json": {"brand": "하기스", "line": "네이처메이드", "type": "팬티형", "stage": "3단계", "gender": "여아용"},
    "3_huggies_naturemade_pants_4_boys.json":  {"brand": "하기스", "line": "네이처메이드", "type": "팬티형", "stage": "4단계", "gender": "남아용"},
    "4_huggies_naturemade_pants_4_girls.json": {"brand": "하기스", "line": "네이처메이드", "type": "팬티형", "stage": "4단계", "gender": "여아용"},
    "5_huggies_maxdry_pants_3_common.json":    {"brand": "하기스", "line": "맥스드라이", "type": "팬티형", "stage": "3단계", "gender": "공용"},
    "6_huggies_maxdry_pants_4_common.json":    {"brand": "하기스", "line": "맥스드라이", "type": "팬티형", "stage": "4단계", "gender": "공용"},
    "7_pampers_babydry_pants_4_common.json":   {"brand": "팸퍼스", "line": "베이비드라이", "type": "팬티형", "stage": "4단계", "gender": "공용"},
    "8_pampers_babydry_pants_5_common.json":   {"brand": "팸퍼스", "line": "베이비드라이", "type": "팬티형", "stage": "5단계", "gender": "공용"}
}

def extract_total_count(product_name):
    """정규표현식을 사용하여 상품명에서 총 매수를 추출합니다."""
    # 제일 마지막 부분 (, \d+매) 에서 추출 시도
    parts = product_name.split(',')
    last_part = parts[-1].strip()
    match = re.search(r'(\d+)\s*(?:매|개|p|P)', last_part)
    if match:
        return int(match.group(1))
        
    # 상품명 전체에서 N매 x M팩 패턴 우선 검색 (예: 64매X4팩)
    match_multiply = re.search(r'(\d+)\s*(?:매|개|p|P)\s*[xX*]\s*(\d+)\s*팩?', product_name, re.IGNORECASE)
    if match_multiply:
        return int(match_multiply.group(1)) * int(match_multiply.group(2))
        
    # 전체 텍스트에서 가장 큰 매수 후보를 찾음
    matches = re.findall(r'(\d+)\s*(?:매|개|p|P)', product_name)
    if matches:
        return max(int(m) for m in matches)
        
    return 0

def process_data():
    raw_dir = "raw_data"
    output_file_path = "data.json"

    json_files = glob.glob(os.path.join(raw_dir, "*.json"))
    valid_files = [f for f in json_files if os.path.basename(f) in CATEGORY_MAP]
    
    if not valid_files:
        print(f"❌ '{raw_dir}' 폴더 안에 유효한 8개 매핑 파일이 없습니다.")
        return

    processed_list = []
    print(f"\n🔍 규격화된 {len(valid_files)}개의 최적화 JSON 파일을 분석합니다...")

    for file_path in valid_files:
        filename = os.path.basename(file_path)
        base_attrs = CATEGORY_MAP[filename]
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                items = data if isinstance(data, list) else [data]
                
                for item in items:
                    p_name = item['productName']
                    
                    # 엄격한 속성 필터링: 브랜드, 라인업, 형태, 단계, 성별
                    # 1. 브랜드 확인
                    if base_attrs['brand'] not in p_name:
                        continue
                    
                    # 2. 라인업 확인
                    if base_attrs['line'] not in p_name:
                        continue
                        
                    # 3. 형태 확인 (팬티형 -> 팬티, 밴드형 -> 밴드)
                    expected_type = base_attrs['type'].replace('형', '')
                    if expected_type not in p_name:
                        continue
                        
                    # 4. 단계 확인
                    if base_attrs['stage'] not in p_name:
                        continue
                        
                    # 5. 성별 확인
                    gender_attr = base_attrs['gender']
                    is_valid_gender = False
                    
                    if gender_attr == "남아용":
                        if "남아" in p_name and "남여" not in p_name and "남녀" not in p_name:
                            is_valid_gender = True
                    elif gender_attr == "여아용":
                        if "여아" in p_name and "남여" not in p_name and "남녀" not in p_name:
                            is_valid_gender = True
                    elif gender_attr == "공용":
                        if "공용" in p_name:
                            is_valid_gender = True
                            
                    if not is_valid_gender:
                        continue
                        
                    t_count = extract_total_count(p_name)
                    if t_count > 0:
                        unit_price = round(item['productPrice'] / t_count)
                        processed_item = {
                            "productId": item['productId'],
                            "productName": p_name,
                            "brand": base_attrs['brand'],
                            "line": base_attrs['line'],
                            "type": base_attrs['type'],
                            "stage": base_attrs['stage'],
                            "gender": base_attrs['gender'],
                            "total_count": t_count,
                            "productPrice": item['productPrice'],
                            "unitPrice": unit_price,
                            "productImage": item['productImage'],
                            "productUrl": item['productUrl']
                        }
                        processed_list.append(processed_item)
        except Exception as e:
            print(f"⚠️ {file_path} 읽기 실패: {e}")

    # 속성이 같은 그룹끼리 묶기
    grouped_data = {}
    for item in processed_list:
        group_key = f"{item['brand']} {item['line']} {item['type']} {item['stage']} {item['gender']}"
        if group_key not in grouped_data:
            grouped_data[group_key] = []
        grouped_data[group_key].append(item)

    if not grouped_data:
        print("분석 가능한 유효한 상품이 없습니다.")
        return

    final_list = []
    print("\n💡 카테고리 그룹별 정렬 및 병합 시작")
    for g_key, g_list in grouped_data.items():
        if len(g_list) > 0:
            g_list.sort(key=lambda x: x['unitPrice'])
            final_list.extend(g_list)
            print(f"   - 그룹 [{g_key}]: {len(g_list)}개 상품 정렬 완료 (최저가: {g_list[0]['unitPrice']}원)")
            
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(final_list, f, ensure_ascii=False, indent=2)
        
    print(f"\n✅ 오프라인 초고속 데이터 정제 및 다중 병합 완료! (총 {len(grouped_data)}개 카테고리, {len(final_list)}개 상품)")
    print(f"결과가 {output_file_path}에 저장되었습니다.")

if __name__ == "__main__":
    process_data()
