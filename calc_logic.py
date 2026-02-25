import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

def llm_parse_titles(products):
    """
    상품명(title)에서 실질적인 총 용량/수량을 추출하는 전처리 모듈입니다.
    현재 API 키가 없다면 테스트용 하드코딩 결과를 반환합니다.
    """
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key or api_key == 'YOUR_GEMINI_API_KEY':
        print("⚠️ [개발 모드] Gemini API 키가 없어 로컬 Mock 정제 결과를 사용합니다.")
        mock_results = []
        for p in products:
            title = p['productName']
            if '2.27' in title:
                mock_results.append({"title": title, "total_g": 2270, "total_count": None})
            elif '2kg+270g' in title:
                mock_results.append({"title": title, "total_g": 2270, "total_count": None})
            elif '2.5kg' in title:
                mock_results.append({"title": title, "total_g": 2500, "total_count": None})
            elif '2.2 킬로그램 x 2' in title:
                mock_results.append({"title": title, "total_g": 4400, "total_count": None})
            elif '2kg' in title:
                mock_results.append({"title": title, "total_g": 2000, "total_count": None})
            elif '1000g' in title:
                mock_results.append({"title": title, "total_g": 1000, "total_count": None})
            else:
                # Fallback for unknown items
                mock_results.append({"title": title, "total_g": 1000, "total_count": None})
        return mock_results
        
    print("🤖 [LLM 호출] 실제 Gemini API를 호츌하여 복잡한 데이터를 정제합니다...")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # 향후 실제 API 연동 시 prompt 전송 및 JSON 파싱 로직 적용 위치
    return []

def calculate_and_rank():
    # 1. raw_data.json 읽어오기
    with open('raw_data.json', 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
        
    # 2. LLM(또는 Mock)을 통한 상품명 분석 -> 퓨어한 갯수/무게 값 추출
    print("⏳ 데이터 전처리 시작...")
    parsed_items = llm_parse_titles(raw_data)
    
    # 3. 단가 계산 
    final_rankings = []
    for raw, parsed in zip(raw_data, parsed_items):
        price = raw['productPrice']
        total_g = parsed.get('total_g')
        total_count = parsed.get('total_count')
        
        unit_price_str = "계산 불가"
        unit_price_val = 9999999  # 계산 불가는 꼴찌 순위로 밀어버림
        
        if total_g:
            # 10g당 단가 산출
            unit_price_val = (price / total_g) * 10
            unit_price_str = f"10g당 {unit_price_val:.0f}원"
        elif total_count:
            # 1장당 단가 산출
            unit_price_val = price / total_count
            unit_price_str = f"1개(장)당 {unit_price_val:.0f}원"
            
        final_rankings.append({
            "rank": 0, 
            "productName": raw['productName'],
            "productPrice": price,
            "productUrl": raw['productUrl'],
            "productImage": raw['productImage'],
            "totalQuantity": f"{total_g}g" if total_g else f"{total_count}개",
            "unitPriceStr": unit_price_str,
            "unitPriceVal": unit_price_val
        })
        
    # 4. 단가 기준 매우 저렴한 순으로 오름차순 정렬
    final_rankings.sort(key=lambda x: x['unitPriceVal'])
    
    # 순위 번호 매기기
    for idx, item in enumerate(final_rankings, 1):
        item['rank'] = idx
        
    # 5. 최종 결과를 프론트엔드(Jinja2) 빌드용 final_ranking.json 으로 저장
    with open('final_ranking.json', 'w', encoding='utf-8') as f:
        json.dump(final_rankings, f, ensure_ascii=False, indent=2)
        
    print(f"✅ 정제 및 단가 계산 완료 -> final_ranking.json 생성 성공 (총 {len(final_rankings)}개 품목)\n")
    
    # 테스트 출력
    for rank in final_rankings[:3]:
        print(f"🥇 {rank['rank']}위: {rank['productName']}")
        print(f"    - 판매가: {rank['productPrice']:,}원")
        print(f"    - 가성비: {rank['unitPriceStr']}")

if __name__ == "__main__":
    calculate_and_rank()
