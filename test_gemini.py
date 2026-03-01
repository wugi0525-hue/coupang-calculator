import os
from dotenv import load_dotenv
from google import genai

# .env 파일 로드
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    print("Error: GEMINI_API_KEY not found in .env")
else:
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model='gemini-2.5-pro',
            contents='test',
        )
        print("SUCCESS:", response.text)
    except Exception as e:
        print("API ERROR:", str(e))
