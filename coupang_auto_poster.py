import sys
# Windows 환경 한글/이모지 출력 오류 방지 (가장 먼저 실행)
sys.stdout.reconfigure(encoding='utf-8')

import os
import time
import pyautogui
import json
import base64
import io
import logging
logging.basicConfig(level=logging.INFO, format='%(message)s', force=True)
import urllib.parse
import win32clipboard
from io import BytesIO
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

# .env 파일에서 환경변수 불러오기 (override=True 적용해서 최신값 보장)
load_dotenv(override=True)

# Gemini API 설정 (환경변수에서 읽어옴, 없으면 비어둠)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    client = genai
    print(f"✅ Gemini API 초기화 성공 (Key: {GEMINI_API_KEY[:4]}...)")
else:
    client = None
    print("❌ ERROR: 환경변수에서 GEMINI_API_KEY를 찾을 수 없습니다.")

class BlogPost(BaseModel):
    title: str
    content: str

# 1. 클립보드에 이미지 복사하는 마법의 함수 (PyWin32 & Pillow 활용)
def send_image_to_clipboard(filepath):
    """이미지 파일을 윈도우 클립보드에 'Ctrl+C' 한 것처럼 정확한 형식으로 복사합니다. (PowerShell 방식)"""
    import subprocess
    abs_path = os.path.abspath(filepath)
    # PowerShell을 이용해 이미지를 네이티브 .NET 비트맵 객체로 클립보드에 주입 (크롬 호환성 100%)
    ps_cmd = f"Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Clipboard]::SetImage([System.Drawing.Image]::FromFile('{abs_path}'))"
    
    subprocess.run(["powershell", "-sta", "-command", ps_cmd], capture_output=True)
    print(f"[{filepath}] 이미지를 클립보드에 안전하게 복사했습니다.")

# 2. 내 계산기 사이트 접속 & 화면 캡처 함수 (시각화)
def capture_website(driver, url, output_filename):
    """계산기 웹사이트에 접속하여 랭킹 화면을 캡처합니다."""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    print(f"[{url}] 본진 사이트로 이동하여 캡처를 준비합니다...")
    driver.get(url)
    
    # 렌더링(로딩) 기다리기
    time.sleep(3) 
    
    # 모바일 뷰어 느낌이 나도록 브라우저 창 크기를 스마트폰 비율로 줄임
    driver.set_window_size(400, 800)
    time.sleep(1)
    
    try:
        # main#product-container 요소를 찾아서 해당 부분만 캡처 (Dynamic Cropping)
        container = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "main#product-container"))
        )
        container.screenshot(output_filename)
        print(f"📸 캡처 완료 (크롭 됨)! 파일명: {output_filename}")
    except Exception as e:
        print(f"⚠️ 요소를 찾지 못해 전체 캡처로 대체합니다: {e}")
        driver.save_screenshot(output_filename)

# 3. 네이버 블로그 하이재킹 포스팅 함수 (글쓰기 패스 & 발행)
def write_naver_blog(driver, naver_id, title, content, image_path, target_link):
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
        # (이전에는 여기서 매번 새 탭을 열었지만, 이제는 루프 밖에서 한 번만 열고 재사용합니다.)
        
        naver_id = "wugi22"
        write_url = f"https://blog.naver.com/{naver_id}/postwrite"
        print(f"[{write_url}] 로 이동합니다...")
        
        driver.get(write_url)
        time.sleep(6) # 에디터 로딩 대기

        # ---------------------------------------------------------------------------------
        # 1. iframe 및 팝업 처리
        # ---------------------------------------------------------------------------------
        try:
            driver.switch_to.frame("mainFrame")
            print("✅ mainFrame 진입 성공")
        except Exception as e:
            print("⚠️ mainFrame 진입 실패 혹은 이미 들어왔습니다:", e)

        # 2. 팝업 제거 (도움말, 임시저장 등)
        try:
            cancel_btns = driver.find_elements(By.CSS_SELECTOR, "button.se-popup-button-cancel, .se-popup-button-cancel, .se-help-panel-close-button")
            for btn in cancel_btns:
                btn.click()
                time.sleep(0.5)
        except:
            pass

        ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        time.sleep(1)

        # ---------------------------------------------------------------------------------
        # 3. 제목 작성
        # ---------------------------------------------------------------------------------
        print("✍️ 제목 입력 중...")
        try:
            title_span = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "span.se-placeholder, .se-title-text p"))
            )
            ActionChains(driver).move_to_element(title_span).click().perform()
            time.sleep(0.5)
            ActionChains(driver).send_keys(title).perform()
            time.sleep(1)
            print("✅ 제목 입력 성공")
            logging.info("✅ 제목 입력 성공") 
        except Exception as e:
            logging.error(f"❌ 제목 입력 부분 실패: {e}") 
            raise e

        # ---------------------------------------------------------------------------------
        # 4. 본문 작성 및 클립보드 붙여넣기
        # ---------------------------------------------------------------------------------
        logging.info("✍️ 본문 입력 중...")
        try:
            # 제목칸에서 엔터를 치면 자연스럽게 본문 블록으로 넘어갑니다.
            ActionChains(driver).send_keys(Keys.ENTER).perform()
            time.sleep(0.5)
            ActionChains(driver).send_keys(content).perform() 
            time.sleep(2)
            logging.info("✅ 본문 텍스트 입력 성공")
        except Exception as e:
            logging.error(f"❌ 본문 입력 부분 실패: {e}") 
            raise e

        # 3. 캡처한 이미지 클립보드 붙여넣기 및 하이퍼링크 삽입
        logging.info("🖼️ 클립보드 사진 업로드 및 링크 삽입 시도...") 
        send_image_to_clipboard(image_path)
        time.sleep(1)
        
        action = ActionChains(driver)
        action.send_keys(Keys.ENTER).send_keys(Keys.ENTER).perform()
        
        # 이미지 붙여넣기: 브라우저 포커스를 잃지 않도록 Selenium ActionChains 사용
        ActionChains(driver).key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
        time.sleep(5.0) # 사진 렌더링 넉넉히 대기
        
        # [중요 고도화] 이미지가 커서 툴바가 가려지는 현상 방지. 방향키 위로 7번 스크롤.
        # 주의: 스크롤 속도가 너무 빠르면 씹히므로 딜레이 추가
        for _ in range(7):
            pyautogui.press('up')
            time.sleep(0.3) 
            
        logging.info("⏳ 스크롤 완료. 뷰포트 안정화를 위해 3초 대기합니다...")
        time.sleep(3.0) 
        
        # --- [유저 특별 요청] 크롬 창 강제 최상단(Foreground) 포커싱 ---
        try:
            import win32gui
            import win32con
            
            def window_enum_handler(hwnd, ctx):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if "스마트에디터" in title or "블로그" in title:
                        try:
                            # 최소화 되어있으면 풀고, 맨 앞으로 가져오기
                            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                            win32gui.SetForegroundWindow(hwnd)
                        except Exception:
                            pass
            win32gui.EnumWindows(window_enum_handler, None)
            time.sleep(1.5) # 창 전환 애니메이션 대기
            logging.info("🖥️ [포커스 락] 네이버 블로그 창을 강제로 최상단으로 끌어올렸습니다.")
        except Exception as e:
            logging.warning(f"⚠️ 창 강제 호출 실패: {e}")
        
        # --- [최강 무적: Gemini Vision API 스나이퍼 매크로 시작] ---
        logging.info(f"⌨️ Gemini Vision API 다이렉트 링크 (화면 분석) 대상 URL: {target_link}")
        
        # [👀 시각 검증 함수 정의]
        try:
            from google import genai
            from google.genai import types
            global GEMINI_API_KEY
            if not GEMINI_API_KEY:
                logging.error("❌ 전역 환경 변수에 GEMINI_API_KEY가 없습니다.")
                return
            vision_client = genai.Client(api_key=GEMINI_API_KEY)
        except ImportError as e:
            logging.error(f"❌ V2 SDK (google-genai) 임포트 실패: {e}")
            return

        def set_clipboard_text(text):
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.CF_UNICODETEXT, text)
            win32clipboard.CloseClipboard()
            
        def get_base64_from_image(img: Image.Image) -> str:
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            return base64.b64encode(buffered.getvalue()).decode('utf-8')

        def find_element_via_vision(target_element_desc: str, crop_box: tuple = None) -> tuple:
            logging.info(f"📸 화면 캡처 및 전송 대기 중... (타겟: {target_element_desc})")
            screen = pyautogui.screenshot()
            
            offset_x, offset_y = 0, 0
            if crop_box:
                # crop_box: (left, top, right, bottom)
                # 화면 바깥으로 나가지 않도록 보정
                left = max(0, int(crop_box[0]))
                top = max(0, int(crop_box[1]))
                right = min(screen.width, int(crop_box[2]))
                bottom = min(screen.height, int(crop_box[3]))
                
                logging.info(f"✂️ 다중 모니터 환각 방지를 위해 화면을 잘라냅니다: (L:{left}, T:{top}, R:{right}, B:{bottom})")
                screen = screen.crop((left, top, right, bottom))
                offset_x = left
                offset_y = top
                
            screen_width, screen_height = screen.size
            
            prompt = f"""
            You are a precise UI automation assistant with excellent spatial reasoning.
            I will provide a screenshot. Your task is to precisely locate the specific UI element 
            described below and output its 2D bounding box.
            
            Target Description:
            {target_element_desc}
            
            Output format MUST be a valid JSON dictionary with a "2d_bounding_box" key.
            Example: {{"2d_bounding_box": [ymin, xmin, ymax, xmax]}}
            Return ONLY the JSON. No markdown formatting.
            """
            
            try:
                response = vision_client.models.generate_content(
                    model='gemini-2.5-pro', # 2.5 Flash보다 공간 지각력이 월등히 뛰어난 PRO 모델 사용
                    contents=[prompt, screen],
                    config=types.GenerateContentConfig(temperature=0.0)
                )
                
                resp_text = response.text.replace("```json", "").replace("```", "").strip()
                result = json.loads(resp_text)
                
                if "2d_bounding_box" in result:
                    box = result["2d_bounding_box"]
                    ymin, xmin, ymax, xmax = box
                    cx = (xmin + xmax) / 2 / 1000.0
                    cy = (ymin + ymax) / 2 / 1000.0
                    
                    # 캡처된 영역 내에서의 좌표에 offset을 더해 실제 모니터 상의 절대 좌표로 변환
                    abs_x = int(screen_width * cx) + offset_x
                    abs_y = int(screen_height * cy) + offset_y
                    return (abs_x, abs_y)
                else:
                    return ()
                return ()
            except Exception as e:
                logging.error(f"⚠️ API 에러: {e}")
                return ()

        def verify_state_via_vision(target_state_desc: str, crop_box: tuple = None) -> bool:
            logging.info(f"👀 시각 검증 진행 중... (질문: {target_state_desc})")
            screen = pyautogui.screenshot()
            
            if crop_box:
                left = max(0, int(crop_box[0]))
                top = max(0, int(crop_box[1]))
                right = min(screen.width, int(crop_box[2]))
                bottom = min(screen.height, int(crop_box[3]))
                screen = screen.crop((left, top, right, bottom))
                
            prompt = f"""
            You are a rigorous QA automation assistant with excellent vision.
            I will provide a screenshot of a web application. 
            Your task is to carefully analyze the image and answer the following question with EXACTLY "YES" or "NO".
            
            Question to verify:
            {target_state_desc}
            
            Output ONLY the word YES or NO.
            """
            
            try:
                response = vision_client.models.generate_content(
                    model='gemini-2.5-pro',
                    contents=[prompt, screen],
                    config=types.GenerateContentConfig(temperature=0.0)
                )
                
                resp_text = response.text.strip().upper()
                if "YES" in resp_text:
                    logging.info("🟩 시각 검증 결과: 통과 (YES)")
                    return True
                else:
                    logging.warning(f"🟥 시각 검증 결과: 실패 (NO) - 답변: {resp_text}")
                    fail_path = f"error_vision_verify_{int(time.time())}.png"
                    screen.save(fail_path)
                    logging.warning(f"📸 실패 화면 저장됨: {fail_path}")
                    return False
            except Exception as e:
                logging.error(f"❌ Vision API 검증 호출 실패: {e}")
                fail_path = f"error_vision_verify_exception_{int(time.time())}.png"
                screen.save(fail_path)
                return False

        # 클립보드에 URL 준비
        time.sleep(0.5)

        try:
            # 0. 이미지를 확실히 1번 클릭해서 선택 상태로 만듭니다.
            desc_image = "The large diaper ranking image that was just pasted into the center of the post editor. Click its center."
            # 멀티 모니터 환경에서 우측 모니터(VS Code 등)의 요소를 오인하지 않도록 좌측 모니터(0,0 ~ 1920,1080)로 검색 영역 제한
            left_monitor_crop = (0, 0, 1920, 1080)
            coord_image = find_element_via_vision(desc_image, crop_box=left_monitor_crop)
            if coord_image:
                logging.info(f"🖼️ [이미지 본체] 발견 및 클릭! X:{coord_image[0]}, Y:{coord_image[1]}")
                pyautogui.click(coord_image[0], coord_image[1])
                time.sleep(1.0)
                
                # [👀 시각 검증 1: 이미지가 정상적으로 클릭되어 초록색 테두리가 생겼는가?]
                verify_img_desc = "Is there a distinctive GREEN rectangular border outlining the large product ranking image in the center? This indicates the image is currently selected."
                if not verify_state_via_vision(verify_img_desc, crop_box=left_monitor_crop):
                    logging.error("❌ [검증 실패] 이미지가 선택되지 않았습니다. 초록색 테두리가 보이지 않습니다.")
                    logging.error("❌ [검증 실패] 예상된 화면이 확인되지 않았습니다. 현재 포스트 이벤트를 중단합니다.")
                    return
                
            # 1. 툴바 내 링크 아이콘 타겟팅 (순수 PyAutoGUI 이미지 매칭 - 100% 확실)
            # DOM, React Synthetic Event, Vision API 좌표 왜곡 모두 실패하는 경우
            # 바탕화면에 저장된 "link_icon.png" 픽셀 패턴을 직접 찾아 클릭하는 가장 원시적이고 확실한 방법입니다.
            try:
                logging.info("🎯 [링크 팝업] 화면상 물리적인 link_icon.png 픽셀 패턴을 직접 탐색합니다...")
                time.sleep(0.5)
                
                # 확실히 에디터에 포커스를 맞추기 위해 메인 프레임으로 진입 시도
                try:
                    driver.switch_to.frame("mainFrame")
                except:
                    pass
                
                # link_icon.png 이미지를 화면에서 모두 찾아내기 (신뢰도 0.8)
                # 네이버 블로그에는 보통 2개의 링크 아이콘이 존재합니다 (1: 최상단 글로벌 툴바, 2: 대상 사진 바로 위의 플로팅 툴바)
                # 우리는 항상 화면상 더 아래에 위치한(y좌표가 큰) 플로팅 툴바의 아이콘을 원합니다.
                try:
                    all_icons = list(pyautogui.locateAllOnScreen('link_icon.png', confidence=0.8))
                    if all_icons:
                        # y좌표(top)가 가장 큰(화면에서 가장 아래에 있는) 아이콘을 타겟으로 선정
                        target_box = max(all_icons, key=lambda box: box.top)
                        icon_location = pyautogui.center(target_box)
                    else:
                        icon_location = None
                except Exception as e:
                    logging.warning(f"이미지 매칭 과정 다중 탐색 실패: {e}")
                    icon_location = None
                    
                if icon_location:
                    logging.info(f"🔗 [링크 아이콘] 화면 물리 좌표 발견! (최하단 타겟팅) X:{icon_location.x}, Y:{icon_location.y}")
                    pyautogui.moveTo(icon_location.x, icon_location.y, duration=0.2)
                    time.sleep(0.1)
                    pyautogui.mouseDown()
                    time.sleep(0.1)
                    pyautogui.mouseUp()
                    
                    # [증거 수집] URL 물리 클릭 직후 스크린샷 캡처
                    pyautogui.screenshot('evidence_url_icon_clicked.png')
                    logging.info("✅ URL 아이콘 클릭 증거 사진 (evidence_url_icon_clicked.png) 저장 완료!")
                    
                    time.sleep(1.5) # 팝업 창이 뜰 시간을 넉넉히 줍니다
                else:
                    logging.error("❌ 화상에서 link_icon.png 패턴을 찾지 못했습니다. 대체 옵션으로 Ctrl+K를 주입합니다...")
                    pyautogui.hotkey('ctrl', 'k')
                    pyautogui.screenshot('evidence_url_icon_clicked.png')
                    time.sleep(1.5)
                    
            except Exception as e:
                logging.error(f"❌ [검증 실패] 단축키 혹은 아이콘 클릭 중 오류 발생: {e}")
                return

            # [👀 시각 검증 2: 링크 입력 팝업창이 떴는가?]
            verify_popup_desc = "Right below the green toolbar, is there a small white popup box with a text input field? It often says 'URL을 입력하세요'. Did the floating link input popup appear?"
            if not verify_state_via_vision(verify_popup_desc, crop_box=left_monitor_crop):
                logging.error("❌ [검증 실패] 링크 입력 팝업창이 나타나지 않았습니다.")
                logging.error("❌ [검증 실패] 예상된 화면이 확인되지 않았습니다. 현재 포스트 이벤트를 중단합니다.")
                return

                
            # --- [궁극의 커서 탐색 로직 (I-Beam 범용 스캔)] ---
            logging.info("🔍 마우스 커서 변화 감지: 팝업 입력창을 찾습니다...")
            
            # iframe 오프셋 보정이 복잡하므로 팝업창의 고유 DOM을 직접 찾아냅니다. 
            try:
                # 팝업 입력창 강제 DOM 제어 (루트 요소)
                url_input = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//input[contains(@class, 'se-custom-layer-link-input')]"))
                )
                
                logging.info("🎯 [URL 입력창] DOM 트리 발견! 강제로 포커스 및 값 주입...")
                
                # 팝업에 포커스가 없어서 본문에 URL이 타이핑되는 대참사를 완벽 방지하는 React Hack
                # React 16+ 환경에서는 단순히 element.value = '...' 로 값을 넣으면 상태(State)가 감지하지 못함.
                # 원시 HTMLInputElement의 setter를 훔쳐서 값을 주입하고 이벤트를 강제로 발생시킴.
                try:
                    driver.execute_script("""
                        var input = arguments[0];
                        var nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                        nativeInputValueSetter.call(input, arguments[1]);
                        var ev2 = new Event('input', { bubbles: true});
                        input.dispatchEvent(ev2);
                    """, url_input, target_link)
                    logging.info("💉 [React Hack] 입력창 포커스 무관하게 URL 컴포넌트 내부 State 자체에 직접 주입 완료!")
                    time.sleep(0.5)
                except Exception as e:
                    logging.warning(f"⚠️ React Hack 주입 실패, fallback 진행: {e}")
                    # 최후의 보루: ActionChains로 클릭 후 주입 시도
                    ActionChains(driver).move_to_element(url_input).click().pause(0.2).send_keys(target_link).perform()
                    
                time.sleep(1.0)
                
                logging.info("✅ URL 값 주입 완료!")
                
                # [증거 수집] URL 입력 완료 직후 스크린샷 캡처
                pyautogui.screenshot('evidence_url_typed.png')
                # [👀 시각 검증 3: URL이 정상적으로 입력되었는가?]
                # 본문에 거대한 카드(OG Link)가 생겼는지, 팝업창에 잘 들어갔는지 육안 검사
                verify_url_desc = "Look at the small white popup text field exactly where it says 'URL을 입력하세요'. Is the Coupang Partner URL text physically typed INSIDE that small box? Note: Answer NO if a giant web-preview link card appeared in the main editor instead."
                if not verify_state_via_vision(verify_url_desc, crop_box=left_monitor_crop):
                    logging.error("❌ [검증 실패] URL이 정상 팝업창이 아닌 엉뚱한 곳에 입력되었습니다 (예: 본문에 OG 카드 생성됨).")
                    logging.error("❌ [검증 실패] 포스트를 저장하지 않고 이벤트를 중단합니다.")
                    return
                
                # [적용 버튼 DOM 클릭]
                apply_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'se-custom-layer-link-apply-button')]"))
                )
                driver.execute_script("arguments[0].click();", apply_btn)
                logging.info("👉 [확인 버튼] 적용 완료!")
                time.sleep(2)
                
                # 본문 iframe 복귀
                driver.switch_to.default_content()
                try:
                    driver.switch_to.frame("mainFrame")
                except:
                    pass
                
            except Exception as e:
                fail_path = f"error_dom_input_failure_{int(time.time())}.png"
                pyautogui.screenshot(fail_path)
                logging.error(f"❌ DOM 셀렉터로 팝업 내 URL 입력에 실패했습니다: {e}")
                logging.warning(f"📸 디버깅 스크린샷 저장됨: {fail_path}")
                return
            logging.info("✅ 사진 다이렉트 링크 (이미지 본체 하이퍼링크) 삽입 완전 성공!")
            
            # --- [유저 특별 요청] Selenium DOM 검증 (가장 확실한 방법) ---
            logging.info("🤖 DOM 구조 검증: 에디터 내부 HTML을 분석하여 링크 삽입 상태를 팩트 체크합니다.")
            try:
                # 현재 mainFrame 내부에 있으므로 페이지 소스를 가져옵니다.
                editor_html = driver.page_source
                
                # 1. 원치 않는 링크 프리뷰 카드(OG Link 컴포넌트)가 생성되었는지 확인
                if "se-oglink" in editor_html or "se-module-oglink" in editor_html:
                    logging.error("❌ [DOM 검증 실패] 경고! 원치 않는 '링크 프리뷰 카드(OG Link)'가 에디터 본문에 생성되었습니다.")
                    
                # 2. 본문에 생 URL 텍스트가 덩그러니 들어갔는지 확인
                if ">http" in editor_html:
                    logging.error("❌ [DOM 검증 실패] 경고! 본문 텍스트 중에 'http'로 시작하는 날것의 URL이 삽입되었습니다.")
                    
                # 3. 에디터 내의 이미지 컴포넌트가 <a> 태그(하이퍼링크)로 감싸져 있는지 확인
                if target_link in editor_html and "se-module-image-link" in editor_html:
                    logging.info("🌟 [DOM 검증 통과] 완벽합니다! 이미지 컴포넌트에 하이퍼링크가 정상적으로 바인딩된 것을 HTML DOM에서 확인했습니다.")
                else:
                    logging.warning("⚠️ [DOM 검증 유보] HTML 상에서 명시적인 이미지-링크 바인딩 클래스(se-module-image-link)를 찾지 못했습니다. DOM 구조가 일시적으로 다를 수 있습니다.")
                    
            except Exception as dom_e:
                logging.warning(f"⚠️ DOM 검증 중 오류 발생: {dom_e}")
        
        except Exception as vision_e:
            err_img = f"error_vision_fail_{int(time.time())}.png"
            pyautogui.screenshot(err_img)
            logging.error(f"🚨 Vision 매크로 치명적 오류 발생! 화면 캡처 저장됨: {err_img}")
            logging.error(f"오류 내용: {vision_e}")
            
            # [유저 요청 완벽 반영] 에러 화면을 AI가 직접 보고 원인 파악 (셀프 진단)
            try:
                logging.info("🧠 봇이 에러 상황을 스스로 분석 중입니다... 잠시만 기다리세요.")
                error_img_pil = Image.open(err_img)
                
                diagnosis_prompt = """
                    I was trying to automate inserting a hyperlink into an image on a Naver Blog editor, 
                    but I failed to find the target (either the 'chain link' icon or the url input field).
                    Please look at this screenshot of the exact moment it failed.
                    
                    Explain to me WHY it might have failed.
                    1. Is the Naver Blog Smart Editor actually visible on screen?
                    2. Are there any overlapping windows, popups, or terminal windows covering the browser?
                    3. Write a short, single-paragraph explanation in Korean (한국어) summarizing the visual situation and why the automation couldn't find the buttons.
                """
                diag_response = vision_client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[diagnosis_prompt, error_img_pil]
                )
                logging.error(f"\n============================================\n🤖 봇의 화면 상황 셀프 진단 결과 🤖\n{diag_response.text.strip()}\n============================================\n")
            except Exception as diag_e:
                logging.error(f"⚠️ 자체 진단 중 오류 발생: {diag_e}")
            finally:
                # [유저 요청 완벽 반영] 진단이 끝난 후 스크린샷 캡처 파일 (임시) 자동 삭제
                try:
                    if os.path.exists(err_img):
                        os.remove(err_img)
                        logging.info(f"🗑️ 자체 진단용 임시 스크린샷({err_img}) 삭제 완료.")
                except Exception as del_e:
                    logging.error(f"⚠️ 스크린샷 삭제 실패: {del_e}")

            logging.warning("⚠️ 이미지 링크 삽입을 건너뛰고 포스팅을 계속 진행합니다.")


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
            # 최종 '발행' 확인 버튼!
            # 오버레이 상에서 발행 버튼은 publish_btn 클래스 또는 tpb.publish 속성을 가짐
            driver.switch_to.default_content() # 확실하게 팝업 레이어 조작을 위해 스위치
            time.sleep(1)
            final_confirm_script = """
               let btns = document.querySelectorAll('button[class*="publish_btn"]');
               if(btns.length > 0) {
                   btns[btns.length - 1].click();
               }
            """
            driver.execute_script(final_confirm_script)
            print("최종 대망의 발행 버튼 클릭 완료!")
        except Exception as e:
            print("⚠️ 발행 버튼을 찾지 못했습니다 ->", e)

        print("[성공] 네이버 블로그 작성 로직 완료!")

    except Exception as e:
        print(f"❌ 네이버 블로그 작성 중 오류 발생:\n{e}")

# 4. Gemini API를 이용한 단일 상품 블로그 제목 및 본문 자동 생성
def generate_single_item_blog_content(item_data, calc_target_url):
    """
    개별 상품 데이터(dict)를 읽어서
    Gemini 모델이 담백한 리뷰 스타일의 제목과 본문을 자동 작성합니다.
    """
    if not client:
         return "기저귀 단가 비교 정보", "최저가를 확인하세요!"

    from datetime import datetime
    today_str = datetime.now().strftime("%y년 %m월 %d일")
    
    prompt = f"""
    당신은 쿠팡에서 생필품(예: 기저귀)을 구매할 때, 광고와 추천 상품에 밀려 '진짜 1개당 최저가'를 찾기 힘든 것에 답답함을 느껴 직접 최저가 단가 리스트를 정리하는 일반 소비자입니다.
    
    다음은 당신이 오늘({today_str}) 확인한 특정 상품의 단가 정보입니다.
    이 단일 상품의 단가 정보를 공유하는 네이버 블로그 포스팅용 [제목]과 [본문]을 작성해 주세요.
    
    정보:
    - 작성 기준일: {today_str}
    - 상품 카테고리: {item_data.get('category', '미분류')}
    - 상품명: {item_data.get('name', '상품명 없음')}
    - 현재 총 가격: {item_data.get('price', '0')}원
    - 1개(장)당 단가: {item_data.get('unit_price', '0')}원
    
    [작성 가이드라인 - 매우 중요]
    1. 과장된 홍보 멘트, 이모지 남발, '맘블리' 같은 가상의 페르소나 인사말은 싹 다 빼고 **아주 담백하고 진정성 있는 톤앤매너**로 작성하세요. (사실과 정보 전달, 그리고 내가 필요해서 직접 찾는다는 서사만 유지)
    2. 본문에는 **반드시** 아래의 내용을 자연스럽게 포함하세요:
       - "같은 주부(또는 소비자)로서 일반 공산품은 가장 저렴한 단가로 사고 싶으나, 쿠팡에서는 최저가 순으로 검색해도 실제 개당 최저가 순으로 나오지 않고 중간에 광고와 추천 상품이 뜹니다. 그래서 내가 정말로 보고 싶은 정보가 안 나와서 답답했습니다."
       - "그래서 필요에 의해 직접 개당 최저가 리스트를 찾아서 만들었고, 변동이 생길 때마다 ({today_str} 기준) 업데이트를 하고 있습니다."
    3. [제목] 작성 규칙: 
       - 반드시 "{today_str} 기준, {item_data.get('name', '')} 실제 1개당 최저가 단가 정보" 형태로 작성하세요.
    4. 본문 내용 규칙:
       - 위에서 언급한 진정성 있는 서사 뒤에, 오늘자({today_str}) 기준으로 확인한 해당 상품의 총 가격과 1개당 단가를 명확히 적어주세요.
       - "상세한 전체 단가 순위표와 구매 링크는 아래 표(이미지)를 클릭해서 확인하세요." 라는 문구를 포함하세요.
    5. (중요) 본문 내에는 어떠한 형태의 웹사이트 URL이나 쿠팡 링크도 직접 쓰지 마세요. HTML 태그도 빼고 순수 텍스트 줄바꿈으로만 출력.
    6. (중요) 공정위 제휴 문구("이 포스팅은 쿠팡 파트너스 활동의 일환으로...")는 절대 본문에 포함하지 마세요.
    
    출력 형식 가이드 (중요):
    [제목]
    (여기에 제목 작성)
    
    [본문]
    (여기에 본문 작성)
    """

    print(f"🤖 Gemini API로 [{item_data.get('name', '')}] 원고 자동 생성 중...")
    try:
        model_name = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
        ai_model = client.GenerativeModel(model_name)
        
        response = ai_model.generate_content(prompt)
        text_resp = response.text.strip()
        
        title, content = "기저귀 단가 비교 정보", "최저가를 확인하세요!"
        
        clean_resp = text_resp.replace("**", "").replace("##", "")
        idx_title = clean_resp.find("[제목]")
        idx_content = clean_resp.find("[본문]")
        
        if idx_title != -1 and idx_content != -1:
            title_part = clean_resp[idx_title+4 : idx_content].strip()
            content_part = clean_resp[idx_content+4 :].strip()
            title = title_part
            content = content_part
            
        return title, content
    except Exception as e:
        print("❌ 블로그 원고 생성 실패 자세한 오류:", e)
        return "기저귀 단가 비교 정보", "최저가를 확인하세요!"

import sys

import asyncio
import random
from urllib.parse import quote

async def run_auto_poster(status_callback=None):
    """
    모든 카테고리에 대한 캡처 및 포스팅 봇의 메인 루프를 실행합니다.
    status_callback이 주어지면 진행 상황을 외부(예: 텔레그램 봇)로 전달합니다.
    """
    async def report(msg):
        print(msg)
        if status_callback:
            await status_callback(msg)

    logging.basicConfig(level=logging.INFO, format='%(message)s')
    await report("=== 🤖 쿠팡 랭킹 자동 포스팅 공장 가동 (텔레그램 연동) ===")
    
    # data.json 파일 존재 확인 (루프 밖)
    if not os.path.exists("data.json"):
        await report("❌ data.json 파일이 없습니다! 포스팅 봇을 중단합니다.")
        return False
        
    try:
        with open("data.json", 'r', encoding='utf-8') as f:
            total_data = json.load(f)
    except Exception as e:
        await report(f"❌ 데이터 로드 실패: {e}")
        return False

    # 개별 아이템 포스팅 단위로 루프 변경
    await report(f"총 {len(total_data)}개의 유효 상품 데이터를 발견했습니다. 단일 상품 자동 포스팅 루프를 시작합니다.")
    
    # --- 로컬용 정적 파일 서버 (캡처용 HTML) 띄우기 ---
    # Python 기본 http.server 사용, Thread로 백그라운드 실행
    PORT = random.randint(8000, 9000)
    import http.server
    import socketserver
    
    Handler = http.server.SimpleHTTPRequestHandler
    httpd = socketserver.TCPServer(("", PORT), Handler)
    
    import threading
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()
    await report(f"🌍 로컬 캡처용 브라우저 서버 가동 (Port: {PORT})...")

    # URL 조합 (예: http://127.0.0.1:8080/index.html)
    LOCAL_HTML_URL = f"http://127.0.0.1:{PORT}/index.html"
    
    # 💡 [핵심] 9224번 포트(뒷문)가 열린 현존 크롬 창을 강제 조종 (하이재킹)
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9224")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        await report("✅ 살아있는 크롬(Chrome) 브라우저 하이재킹 성공! (기존 세션 재사용)")
    except Exception as e:
        await report("❌ 오류: 크롬 브라우저가 실행되어 있지 않거나, 9224 디버그 모드로 열리지 않았습니다.")
        await report("❗ 반드시 launch_chrome.py 를 먼저 실행하여 크롬을 띄워주세요. (혹은 run_chrome_debugger.bat 실행)")
        httpd.shutdown()
        return False

    # --- 충돌 방지: 네이버 전용 탭 1개 재사용 ---
    try:
        driver.execute_script("window.open('about:blank', '_blank');")
        driver.switch_to.window(driver.window_handles[-1])
    except Exception as e:
        await report("⚠️ 경고: 새 탭 생성 실패, 현재 탭 사용")

    # 내 계산기 웹사이트 접속 주소 (블로그 본문 첨부용)
    CALC_URL = "https://wugi0525-hue.github.io/coupang-calculator/"
    # 네이버 아이디 (실제 띄워진 브라우저의 로그인 아이디)
    NAVER_ID = "wugi22"

    for idx, item in enumerate(total_data):
        item_name = item.get("name", "Unknown Item")
        # 해당 아이템이 속한 전체 카테고리 필터링 값 생성
        cat_key = f"{item.get('brand','')} {item.get('line','')} {item.get('type','')} {item.get('stage','')} {item.get('gender','')}".strip()
        encoded_category = quote(cat_key)

        await report(f"\n=============================================")
        await report(f"▶ [{idx+1}/{len(total_data)}] 단일 포스팅: '{item_name}' 준비 중...")
        
        # 1. 대상 카테고리를 표시하는 캡처용 브릿지 URL (화면엔 해당 카테고리 랭킹이 뜸)
        target_local_url = f"{LOCAL_HTML_URL}?category={encoded_category}"
        
        capture_img = "ranking_capture.png"
        await report("📸 단계 1: 화면 다이나믹 캡처 엔진 가동...")
        capture_website(driver, target_local_url, capture_img)
        
        # 2. 자동 포스팅 봇 모듈 동작 시작 (AI 원고 단일 생성)
        public_target_url = f"{CALC_URL}?category={encoded_category}"
        await report(f"🤖 단계 2: AI 원고 크리에이터 엔진 기동 (Item: {item_name})...")
        blog_title, blog_content = generate_single_item_blog_content(item, public_target_url)
        await report(f"✅ 생성된 제목: {blog_title}")
        
        # 3. 네이버 블로그 포스팅 진행
        await report("📝 단계 3: 네이버 블로그 하이재킹 포스팅 엔진 진입...")
        write_naver_blog(driver, NAVER_ID, blog_title, blog_content, os.path.abspath(capture_img), public_target_url)
        
        # 쿨다운 
        await report("⏳ 네이버 어뷰징 방지를 위한 대기모드 전환 (10초)...")
        await asyncio.sleep(10)
        
    await report("\n🎉 완료! 전체 데이터 리스트(단일 항목별) 포스팅 작업이 성공적으로 끝났습니다.")
    
    # 서버 닫기
    httpd.shutdown()
    return True

if __name__ == "__main__":
    # 터미널에서 단독 배치 스크립트로 실행 시
    asyncio.run(run_auto_poster())
