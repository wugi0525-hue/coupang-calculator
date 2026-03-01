import os
from google import genai
from dotenv import load_dotenv
import sys

# Windows 콘솔 인코딩
sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("API KEY가 없습니다.")
    exit()

try:
    client = genai.Client(api_key=api_key)
    print("사용 가능한 제미나이 모델 목록을 구글 서버에서 가져옵니다...\n")
    
    # 모델 목록 조회
    for model in client.models.list():
        # 이름에 'gemini'가 들어가는 주요 모델만 출력
        if 'gemini' in model.name:
            print(model.name)
            
except Exception as e:
    print("에러 발생:", e)
