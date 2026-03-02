import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import pyperclip
from PIL import Image
import win32clipboard
import io

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
        # 3. 제목 작성
        # ---------------------------------------------------------------------------------
        print("✍️ 제목 입력 중...")
        try:
            # 제목 입력 칸 (클래스명에 title이 포함된 영역)
            title_area = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".se-title-text p, .se-title-text span, .se-title-text"))
            )
            title_area.click()
            time.sleep(1)
            
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
            # 본문 입력 칸 (본문 영역 클릭 활성화)
            content_area = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".se-main-container .se-text-paragraph, .se-component.se-text"))
            )
            content_area.click()
            time.sleep(1)
            
            # 본문 텍스트 타이핑
            ActionChains(driver).send_keys(content).perform()
            time.sleep(1)

        except Exception as e:
            print("❌ 본문 입력 실패:", e)
            raise e

        # 3. 캡처한 이미지 업로드 로직 (사진 버튼 누르고 파일 대화창 제어는 복잡하므로 클립보드 붙여넣기 꼼수 활용)
        print("🖼️ 클립보드에서 사진 본문에 붙여넣기 시도...")
        send_image_to_clipboard(CAPTURE_IMG)
        time.sleep(1)
        # 본문 끝에서 엔터 두 번 치고 공간 확보 후 이미지 붙여넣기
        action = ActionChains(driver) # Re-initialize action chains if needed, or ensure it's in scope
        action.send_keys(Keys.ENTER).send_keys(Keys.ENTER).perform()
        action.key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
        time.sleep(5) # 사진 업로드 렌더링 딜레이 대기

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

import sys

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    print("=== 🤖 하이브리드 자동 포스팅 봇 가동 ===")
    
    # 네이버 아이디 (실제 띄워진 브라우저의 로그인 아이디)
    NAVER_ID = "wugi22"
    
    # 내 계산기 웹사이트 주소 (GitHub Pages)
    CALC_URL = "https://wugi0525-hue.github.io/coupang-calculator/"
    CAPTURE_IMG = "ranking_capture.png"
    
    # 💡 [핵심] 9222번 포트(뒷문)가 열린 현존 크롬 창을 강제 조종 (하이재킹)
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    
    print("📡 뒷문 포트(9222)를 통해 진짜 크롬 브라우저 제어권 획득 시도 중...")
    try:
        driver = webdriver.Chrome(options=chrome_options)
        print("✅ 투명 브라우저 하이재킹 성공! (로그인 캡챠 무력화 됨)")
    except Exception as e:
        print("❌ 실패: 'python launch_chrome.py' 을 먼저 실행해서 봇 전용 크롬을 켜두세요!")
        exit(1)
        
    # --- 봇 시나리오 실행 ---
    # 1. 내 웹사이트 캡처하기
    capture_website(driver, CALC_URL, CAPTURE_IMG)
    print("🎉 자동화 스크립트 캡처 완료.")
    
    # 3. 자동 포스팅 봇 모듈 동작 시작
    test_title = "[가성비 필수확인] 2026년 3월 하기스/팸퍼스 기저귀 1장당 진짜 최저가는?"
    test_content = (
        "안녕하세요! 육아 필수품인 '기저귀', 겉보기 가격에 속지 마세요!\n"
        "매일매일 1장당 진짜 단가를 계산해드리는 가성비 봇입니다.\n\n"
        "오늘의 가장 저렴한 로켓배송 기저귀 순위를 공개합니다! (단백질 파우더 아님 🙅‍♀️)\n\n"
        "자세한 기저귀 순위와 실시간 1장당 단가는 아래 사진 혹은 사이트를 클릭해 확인해주세요!\n"
        f"👉 우리 아이 기저귀 최저가 계산기 바로가기: {CALC_URL}\n"
    )
    
    # 네이버 블로그 포스팅 함수 실행 (캡처된 이미지 및 텍스트 전달)
    write_naver_blog(driver, NAVER_ID, test_title, test_content, CAPTURE_IMG)
    print("\n🎉 자동화 스크립트 뼈대 세팅 완료.")
    print("네이버 스마트에디터 구조 파악 전이므로 안전을 위해 주석 해제는 잠시 멈춰두었습니다.")
