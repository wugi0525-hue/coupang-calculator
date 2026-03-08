import os
import sys
import json
from dotenv import load_dotenv
import google.generativeai as genai

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv(override=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    client = genai
    print("API Key loaded:", GEMINI_API_KEY[:4] + "...")
else:
    print("No API Key")
    client = None

def test_generate():
    data_filepath = "temp_category.json"
    calc_url = "https://wugi0525-hue.github.io/coupang-calculator"
    
    try:
        with open(data_filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print("Failed to load file", e)
        return
        
    theme_item = data[0]
    brand = theme_item.get("brand", "인기")
    line = theme_item.get("line", "")
    type_ = theme_item.get("type", "팬티형")
    stage = theme_item.get("stage", "")
    gender = theme_item.get("gender", "남녀공용")
    product_theme = f"{brand} {line} {type_} {stage} {gender}".strip()

    prompt = f"""
    당신은 네이버 블로그 육아/육아템 전문 리뷰어이자 가성비 특가 알리미입니다.
    이번 주제는 '{product_theme}' 단일 상품에 대한 패키지 매수별 장당 진짜 가격(단가) 랭킹입니다.

    다음 기저귀 단가 랭킹 데이터를 바탕으로, 엄마들이 클릭하고 싶어지는 블로그 포스팅 제목과 본문을 작성해주세요.
    
    데이터:
    {json.dumps(data, ensure_ascii=False, indent=2)}

    작성 가이드라인:
    1. 친근하고 공감가는 육아맘/육아대디 말투를 사용하세요. 가독성을 위해 이모지를 적절히(너무 많지 않게) 사용하세요.
    2. '{product_theme}' 기저귀가 인기가 많은 이유를 가볍게 언급하세요.
    3. 눈에 보이는 전체 가격보다 '1장당 단가'를 계산해보고 사는 것이 왜 중요한지 팩트를 짚어주세요.
    4. 랭킹 데이터에서 1위(가장 장당 단가가 저렴한 패키지) 상품을 강조해서 '당장 쟁여야 할 딜'로 추천하세요.
    5. 본문 중하단 쯤에는 반드시 "더 자세한 기저귀별 장당 최저가 순위와 구매 링크는 아래 계산기 사이트에서 확인하세요!\\n👉 {calc_url}" 문구를 포함시켜주세요. (캡처된 이미지도 함께 보여질 것이라 언급하면 좋습니다)
    6. 본문 제일 하단에는 공정위 문구 "이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."를 포함하세요.

    출력 형식 가이드 (중요): 
    반드시 아래와 같은 정확한 텍스트 포맷으로만 답변을 생성해주세요. 다른 설명은 일절 추가하지 마세요.
    
    [제목]
    여기에 블로그 제목 작성
    
    [본문]
    여기에 블로그 본문 작성 (HTML 태그는 절대 사용하지 말고, 줄바꿈은 그냥 엔터로 처리)
    """

    print("🤖 Gemini API로 블로그 원고 자동 생성 중...")
    try:
        model_name = os.getenv('GEMINI_MODEL', 'gemini-1.5-pro')
        ai_model = client.GenerativeModel(model_name)
        
        response = ai_model.generate_content(prompt)
        text_resp = response.text.strip()
        
        print("\n=== AI 원문 디버그 ===")
        print(text_resp)
        print("======================\n")
        
    except Exception as e:
        print("❌ 오류:", e)

test_generate()
