import os
import subprocess

chrome_paths = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
]

chrome_path = next((path for path in chrome_paths if os.path.exists(path)), None)

if chrome_path:
    print("=========================================================")
    print("🚀 봇 전용 크롬 브라우저를 엽니다...")
    print("👉 이 크롬 창에서 [네이버에 로그인] 한 뒤 창을 끄지 말고 계속 켜두세요!")
    print("=========================================================")
    
    # 디버깅 포트 9222로 크롬 실행
    subprocess.Popen([
        chrome_path,
        "--remote-debugging-port=9222",
        r"--user-data-dir=C:\ChromeBot" # 봇 전용 별도 프로필 사용
    ])
else:
    print("❌ 크롬 브라우저가 설치된 경로를 찾을 수 없습니다.")
