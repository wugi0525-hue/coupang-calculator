# -*- coding: utf-8 -*-
import os
import time
import json
import base64
import io
import win32clipboard
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

import google.generativeai as genai
from pydantic import BaseModel
from dotenv import load_dotenv

# .env 파일에서 환경변수 불러오기
load_dotenv()

# Gemini API 설정 (환경변수에서 읽어옴, 없으면 비어둠)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    client = genai
else:
    client = None

class BlogPost(BaseModel):
    title: str
    content: str

# 1. 클립보드에 이미지 복사하는 마법의 함수 (PyWin32 & Pillow 활용)
def send_image_to_clipboard(filepath):
    """이미지 파일을 윈도우 클립보드에 'Ctrl+C' 한 것처럼 복사합니다."""
    image = Image.open(filepath)
    output = io.BytesIO()
    image.convert("RGB").save(output, "BMP")
    data = output.getvalue()[14:]
    output.close()
    
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
    win32clipboard.CloseClipboard()
    print(f"[{filepath}] 이미지를 클립보드에 복사했습니다.")

# 2. 내 계산기 사이트 접속 & 화면 캡처 함수 (시각화)
def capture_website(driver, url, output_filename):
    """계산기 웹사이트에 접속하여 랭킹 화면을 캡처합니다."""
    print(f"[{url}] 본진 사이트로 이동하여 캡처를 준비합니다...")
    driver.get(url)
    
    # 렌더링(로딩) 기다리기
    time.sleep(3) 
    
    # 모바일 뷰어 느낌이 나도록 브라우저 창 크기를 스마트폰 비율로 줄임
    driver.set_window_size(400, 800)
    time.sleep(1)
    
    # 현재 화면 전체 캡처
    driver.save_screenshot(output_filename)
    print(f"📸 캡처 완료! 파일명: {output_filename}")

# 3. 네이버 블로그 하이재킹 포스팅 함수 (글쓰기 패스 & 발행)
def write_naver_blog(driver, naver_id, title, content, image_path):
    """
    네이버 블로그 스마트에디터 ONE에 접근하여 제목과 본문을 작성합니다.
    (기존 로그인된 세션을 재사용하므로 별도의 로그인 과정 생략)
    """
    try:
        # 네이버 블로그 글쓰기 URL 진입
        # 사용자님의 블로그 ID에 맞게 수정이 필요할 수 있으나, 기본 글쓰기 팝업 경로는 보통 동일합니다.
        print("✍️ 네이버 블로그 스마트 에디터 ONE(글쓰기) 페이지로 이동...")
        # (주의: 실제 사용자 블로그 ID는 나중에 동적으로 입력받거나 환경변수로 빼야 합니다)
        driver.get(f"https://blog.naver.com/{naver_id}/postwrite")
        time.sleep(8) # 에디터 무거운 스크립트들이 로딩될 때까지 충분한 대기

        # 최신 스마트에디터 ONE은 iframe 없이 메인 DOM에 에디터가 렌더링될 수 있습니다.
        # 혹시 몰라 기존 구형 에디터 iframe(mainFrame)이 있다면 스위칭하고, 없으면 그냥 패스합니다.
        try:
            print("🔍 에디터 iframe 존재 여부 확인...")
            iframes = driver.find_elements(By.ID, "mainFrame")
            if len(iframes) > 0:
                driver.switch_to.frame("mainFrame")
                print("✅ mainFrame (구형) 진입 성공")
            else:
                print("✅ iframe 없음 (최신 에디터 DOM 구조 확인)")
            time.sleep(2)
        except Exception as e:
            print("⚠️ iframe 탐색 패스:", e)

        # ---------------------------------------------------------------------------------
        # 2.5 팝업 제거 (이전 글 불러오기 안내창 등)
        # ---------------------------------------------------------------------------------
        print("🔍 방해꾼 팝업(작성중인 글 여부 등)이 있는지 확인합니다...")
        try:
            # 팝업의 취소 버튼 클릭 시도
            cancel_btns = driver.find_elements(By.CSS_SELECTOR, "button.se-popup-button-cancel, .se-popup-button-cancel")
            if cancel_btns:
                cancel_btns[0].click()
                print("✅ [취소] 버튼 팝업을 성공적으로 닫았습니다.")
                time.sleep(1)
        except Exception as e:
            pass
            
        # 추가적으로 화면의 dim(회색 배경)을 클릭해서 닫거나 ESC 키 전송
        try:
            ActionChains(driver).send_keys(Keys.ESCAPE).perform()
            time.sleep(1)
        except:
            pass

        # ---------------------------------------------------------------------------------
        # 3. 제목 작성
        # ---------------------------------------------------------------------------------
        print("✍️ 제목 입력 중...")
        try:
            # 제목 입력 칸 (물리적 포커싱 강제)
            title_area = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".se-title-text p, span.se-placeholder"))
            )
            ActionChains(driver).move_to_element(title_area).click().perform()
            time.sleep(0.5)
            ActionChains(driver).send_keys(title).perform()
            time.sleep(1)
        except Exception as e:
            print("❌ 제목 입력 실패:", e)
            raise e

        # ---------------------------------------------------------------------------------
        # 4. 본문 작성 및 캡처한 이미지(클립보드) 붙여넣기
        # ---------------------------------------------------------------------------------
        print("✍️ 본문 입력 중...")
        try:
            # 본문 입력 칸
            content_area = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".se-main-container .se-text-paragraph, p.se-text-paragraph"))
            )
            ActionChains(driver).move_to_element(content_area).click().perform()
            time.sleep(0.5)
            ActionChains(driver).send_keys(content).perform()
            time.sleep(1)

        except Exception as e:
            print("❌ 본문 입력 실패:", e)
            raise e

        # 3. 캡처한 이미지 클립보드 붙여넣기 및 하이퍼링크 삽입
        print("🖼️ 클립보드 사진 업로드 및 링크 삽입 시도...")
        send_image_to_clipboard(image_path)
        time.sleep(1)
        
        action = ActionChains(driver)
        action.send_keys(Keys.ENTER).send_keys(Keys.ENTER).perform()
        # 이미지 붙여넣기
        action.key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
        time.sleep(5) # 사진 업로드 렌더링 대기
        
        try:
            # 이미지 선택 후 링크 삽입 (Shift + Left 로 선택 후 Ctrl + K)
            action.key_down(Keys.SHIFT).send_keys(Keys.ARROW_LEFT).key_up(Keys.SHIFT).perform()
            time.sleep(1)
            action.key_down(Keys.CONTROL).send_keys('k').key_up(Keys.CONTROL).perform()
            time.sleep(1)
            action.send_keys("https://wugi0525-hue.github.io/coupang-calculator/").send_keys(Keys.ENTER).perform()
            time.sleep(1)
            # 커서 원상복구 (오른쪽으로 이동 후 엔터 두번)
            action.send_keys(Keys.ARROW_RIGHT).send_keys(Keys.ENTER).send_keys(Keys.ENTER).perform()
        except:
            pass

        # 5. 발행 팝업 열기 (우측 상단 '발행' 버튼 클릭)
        print("🚀 [발행] 팝업 열기...")
        try:
            publish_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'publish_btn')]"))
            )
            publish_btn.click()
            time.sleep(2)
            print("발행 팝업창 클릭 성공! (실제 최종 발행 버튼은 아직 보호차원에서 주석처리)")
            time.sleep(3)
            # 최종 '발행' 확인 버튼! (실제 테스트 완료 전까지는 아래 줄을 주석으로 두는 것이 안전합니다)
            # final_confirm = driver.find_element(By.XPATH, "//button[contains(@class, 'btn_confirm')]")
            # final_confirm.click()
        except Exception as e:
            print("⚠️ 발행 버튼을 찾지 못했습니다 ->", e)

        print("[성공] 네이버 블로그 작성 로직 테스트 완료!")

    except Exception as e:
        print(f"❌ 네이버 블로그 작성 중 오류 발생:\n{e}")

# 4. Gemini API를 이용한 블로그 제목 및 본문 자동 생성
def generate_blog_content(data_filepath, calc_url):
    """
    정제된 기저귀 단가 데이터(data.json)를 읽어서
    Gemini 모델이 육아 블로그 스타일의 제목과 본문을 자동 작성합니다.
    """
    if not client:
        print("⚠️ Gemini API 키가 없어 기본 텍스트를 반환합니다.")
        return "기저귀 가성비 랭킹 특가 정보", "기저귀 가성비 랭킹을 알아보세요!"

    try:
        with open(data_filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
         print("❌ data.json 불러오기 실패:", e)
         return "기저귀 가성비 랭킹 특가 정보", "기저귀 가성비 랭킹을 알아보세요!"

    if not data:
        return "기저귀 가성비 랭킹 특가 정보", "기저귀 가성비 랭킹을 알아보세요!"

    # 첫번째 아이템으로 메인 테마 추출
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
    반드시 아래와 같은 정확한 JSON 포맷으로만 답변을 생성해주세요. 마크다운 기호(```json)나 다른 설명은 일절 추가하지 마세요.
    {{
      "title": "여기에 블로그 제목 작성",
      "content": "여기에 블로그 본문 작성 (HTML 태그는 절대 사용하지 말고, 줄바꿈은 \\n 으로 처리)"
    }}
    """

    print("🤖 Gemini API로 블로그 원고 자동 생성 중...")
    try:
        model_name = os.getenv('GEMINI_MODEL', 'gemini-1.5-pro')
        ai_model = client.GenerativeModel(model_name)
        
        response = ai_model.generate_content(
            prompt,
            generation_config={
                'response_mime_type': 'application/json',
            }
        )
        
        parsed_data = json.loads(response.text)
        return parsed_data.get('title', '제목 생성 실패'), parsed_data.get('content', '본문 생성 실패')
    except Exception as e:
        print("❌ 블로그 원고 생성 실패:", e)
        return "기저귀 가성비 랭킹 특가 정보", "기저귀 가성비 랭킹을 알아보세요!"

import sys

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    print("=== 🤖 하이브리드 자동 포스팅 봇 가동 ===")
    
    # 네이버 아이디 (실제 띄워진 브라우저의 로그인 아이디)
    NAVER_ID = "wugi22"
    
    # 내 계산기 웹사이트 접속 주소 (블로그 본문 첨부용)
    CALC_URL = "https://wugi0525-hue.github.io/coupang-calculator/"
    
    # 💡 캡처용 로컬 파일 주소 (인터넷 배포 전 최신 화면 캡처용)
    LOCAL_HTML_URL = f"file:///{os.path.abspath('index.html')}"
    
    CAPTURE_IMG = "ranking_capture.png"
    
    # 💡 [핵심] 9224번 포트(뒷문)가 열린 현존 크롬 창을 강제 조종 (하이재킹)
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9224")
    
    print("📡 뒷문 포트(9224)를 통해 진짜 크롬 브라우저 제어권 획득 시도 중...")
    try:
        driver = webdriver.Chrome(options=chrome_options)
        print("✅ 투명 브라우저 하이재킹 성공! (로그인 캡챠 무력화 됨)")
    except Exception as e:
        print("❌ 실패: 'python launch_chrome.py' 을 먼저 실행해서 봇 전용 크롬을 켜두세요!")
        exit(1)
        
    # --- 봇 시나리오 실행 ---
    # 1. 최신 기저귀 랭킹 화면 캡처하기 (로컬 index.html)
    capture_website(driver, LOCAL_HTML_URL, CAPTURE_IMG)
    print("🎉 자동화 캡처 완료.")
    
    # 3. 자동 포스팅 봇 모듈 동작 시작 (AI 원고 생성)
    blog_title, blog_content = generate_blog_content("data.json", CALC_URL)
    print(f"✅ 생성된 제목: {blog_title}")
    
    # 네이버 블로그 포스팅 함수 실행 (캡처된 이미지 및 AI 생성 정제 텍스트 전달)
    write_naver_blog(driver, NAVER_ID, blog_title, blog_content, CAPTURE_IMG)
    print("\n🎉 자동화 스크립트 뼈대 세팅 완료.")
    print("네이버 스마트에디터 구조 파악 전이므로 안전을 위해 주석 해제는 잠시 멈춰두었습니다.")
