import os
import json
import re
from google import genai
from dotenv import load_dotenv
import sys

# Windows 콘솔 인코딩 회피용
sys.stdout.reconfigure(encoding='utf-8')

# .env 파일 로드
load_dotenv()

# Gemini API 설정
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("오류: .env 파일에 GEMINI_API_KEY가 없습니다.")
    exit()

client = genai.Client(api_key=api_key)

def process_product_data(product):
    """
    단일 상품 데이터를 받아 Gemini API로 단위 정보를 추출합니다.
    """
    prompt = f"""
    당신은 상품명 분석 전문가입니다. 아래 쿠팡 상품 정보를 분석하여 '1매당' 또는 '1g당' 혹은 '1ml당' 등 기본 단위의 가격을 구하기 위한 총 수량(개수, 용량 등)과 단위를 추출하세요.

    상품명: {product['productName']}
    가격: {product['productPrice']}

    다음 JSON 형식으로만 응답하세요 (다른 말은 절대 하지 마세요).
    {{
        "total_quantity": 숫자 (총 매수, 총 g, 총 ml 등. 예: 기저귀 3팩에 각 40매면 120),
        "unit": "문자열" (매, g, ml, 개 등)
    }}
    """

    try:
        # 사용자님이 말씀하신 3.1 프로 모델 적용 (정확한 API 명칭: gemini-3.1-pro-preview)
        response = client.models.generate_content(
            model='gemini-3.1-pro-preview',
            contents=prompt,
        )
        
        # JSON 텍스트 파싱
        response_text = response.text.strip()
        # 마크다운 코드 블록 제거
        if response_text.startswith("```json"):
            response_text = response_text[7:-3]
        elif response_text.startswith("```"):
            response_text = response_text[3:-3]
            
        parsed = json.loads(response_text)
        return parsed['total_quantity'], parsed['unit']

    except Exception as e:
        print(f"[{product['productName']}] API 파싱 오류: {e}")
        return None, None

def calculate_and_rank():
    # 1. raw_data.json 읽어오기
    with open('raw_data.json', 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
        
    # 2. LLM(또는 Mock)을 통한 상품명 분석 -> 퓨어한 갯수/무게 값 추출
    print("⏳ 데이터 전처리 시작...")
    parsed_items = []
    
    for item in raw_data:
        total_q, unit = process_product_data(item)
        if total_q and unit:
            parsed_items.append({
                "productName": item["productName"],
                "productPrice": item["productPrice"],
                "productUrl": item["productUrl"],
                "productImage": item.get("productImage", ""),
                "total_quantity": total_q,
                "unit": unit
            })
        else:
            print(f"⚠️ [{item['productName']}] 데이터 추출 실패로 제외됩니다.")

    print("\n🧮 1단위 리터럴당 단가 계산 중...")
    results = []
    for item in parsed_items:
        price = item['productPrice']
        total_q = float(item['total_quantity'])
        
        # 1단위 (예: 1매, 1g, 1ml) 당 가격
        unit_price = price / total_q
        
        # 가독성을 위해 10단위 가격 등을 문자열로 저장 (선택 사항)
        # 쿠팡은 주로 10g당 가격을 보여주므로 이를 흉내냄
        unit_price_str = f"10{item['unit']}당 {int(unit_price * 10)}원"
        
        results.append({
            "productName": item['productName'],
            "productPrice": item['productPrice'],
            "productUrl": item['productUrl'],
            "productImage": item['productImage'],
            "totalQuantity": f"{int(total_q)}{item['unit']}",
            "unitPriceStr": unit_price_str,
            "unitPriceVal": unit_price
        })

    # 4. 단가를 기준으로 오름차순 정렬 (가장 싼 것이 1등)
    results = sorted(results, key=lambda x: x['unitPriceVal'])
    
    # 5. 랭킹 순위 부여해서 새 리스트 생성
    final_ranking = []
    for i, res in enumerate(results):
        res['rank'] = i + 1
        final_ranking.append(res)
        
    # 6. JSON 파일로 결과 저장
    output_file = 'final_ranking.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(final_ranking, f, ensure_ascii=False, indent=2)
        
    print(f"\n✅ 계산 완료! 총 {len(final_ranking)}개 상품의 가성비 랭킹이 '{output_file}'에 저장되었습니다.")
    
    # 테스트 출력
    for rank in final_ranking[:3]:
        print(f"🥇 {rank['rank']}위: {rank['productName']}")
        print(f"    - 판매가: {rank['productPrice']:,}원")
        print(f"    - 가성비: {rank['unitPriceStr']}")

if __name__ == "__main__":
    calculate_and_rank()
