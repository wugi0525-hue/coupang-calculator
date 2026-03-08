import asyncio
import json
import os
import sys
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel(os.environ.get("GEMINI_MODEL", "gemini-1.5-pro"))

def generate_single_item_blog_content(item_data, current_date):
    """
    단일 상품에 대한 블로그 원고를 생성하는 프롬프트 (테스트용)
    """
    prompt = f"""
    당신은 쿠팡에서 생필품(예: 기저귀)을 구매할 때, 광고와 추천 상품에 밀려 '진짜 1개당 최저가'를 찾기 힘든 것에 답답함을 느껴 직접 최저가 단가 리스트를 정리하는 일반 소비자입니다.
    
    다음은 당신이 오늘({current_date}) 확인한 특정 상품의 단가 정보입니다.
    이 단일 상품의 단가 정보를 공유하는 네이버 블로그 포스팅용 [제목]과 [본문]을 작성해 주세요.
    
    정보:
    - 작성 기준일: {current_date}
    - 상품 카테고리: {item_data['category']}
    - 상품명: {item_data['name']}
    - 현재 총 가격: {item_data['price']}원
    - 1개(장)당 단가: {item_data['unit_price']}원
    
    [작성 가이드라인 - 매우 중요]
    1. 과장된 홍보 멘트, 이모지 남발, '맘블리' 같은 가상의 페르소나 인사말은 싹 다 빼고 **아주 담백하고 진정성 있는 톤앤매너**로 작성하세요. (사실과 정보 전달, 그리고 내가 필요해서 직접 찾는다는 서사만 유지)
    2. 본문에는 **반드시** 아래의 내용을 자연스럽게 포함하세요:
       - "같은 주부(또는 소비자)로서 일반 공산품은 가장 저렴한 단가로 사고 싶으나, 쿠팡에서는 최저가 순으로 검색해도 실제 개당 최저가 순으로 나오지 않고 중간에 광고와 추천 상품이 뜹니다. 그래서 내가 정말로 보고 싶은 정보가 안 나와서 답답했습니다."
       - "그래서 필요에 의해 직접 개당 최저가 리스트를 찾아서 만들었고, 변동이 생길 때마다 ({current_date} 기준) 업데이트를 하고 있습니다."
    3. [제목] 작성 규칙: 
       - 반드시 "{current_date} 기준, {item_data['name']} 실제 1개당 최저가 단가 정보" 형태로 작성하세요.
    4. 본문 내용 규칙:
       - 위에서 언급한 진정성 있는 서사 뒤에, 오늘자({current_date}) 기준으로 확인한 해당 상품의 총 가격과 1개당 단가를 명확히 적어주세요.
       - "상세한 전체 단가 순위표와 구매 링크는 아래 표(이미지)를 클릭해서 확인하세요." 라는 문구를 포함하세요. (직접적인 쿠팡 링크 URL이나 공정위 문구는 넣지 마세요).
    
    출력 형식:
    [제목]
    (여기에 제목 작성)
    
    [본문]
    (여기에 본문 작성)
    """
    
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        print(f"✅ 생성 성공")
        return text
    except Exception as e:
        print(f"❌ 생성 실패: {e}")
        return ""

test_item = {
    "category": "kids",
    "name": "팸퍼스 베이비드라이 팬티형 5단계 (남녀공용)",
    "price": "50000",
    "unit_price": "250",
    "unit": "1장당"
}

today_str = datetime.now().strftime("%y년 %m월 %d일")
print(f"테스트 데이터 생성 완료. AI 원고 작성 시작... (기준일: {today_str})")

result_text = generate_single_item_blog_content(test_item, today_str)

with open('test_result_output.txt', 'w', encoding='utf-8') as f:
    f.write(result_text)

print("결과가 test_result_output.txt 파일에 저장되었습니다.")
