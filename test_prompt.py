import asyncio
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
from coupang_auto_poster import generate_blog_content
from dotenv import load_dotenv

load_dotenv()

# 임시 테스트 JSON 파일 생성
test_data = [
  {
    "category": "kids",
    "name": "팸퍼스 베이비드라이 팬티형 5단계",
    "url": "https://www.coupang.com/",
    "price": "50000",
    "unit_price": "250",
    "unit": "1장당",
    "brand": "팸퍼스",
    "type": "팬티형",
    "size": "5단계",
    "gender": "남녀공용"
  },
  {
    "category": "kids",
    "name": "하기스 매직팬티 5단계",
    "url": "https://www.coupang.com/",
    "price": "60000",
    "unit_price": "300",
    "unit": "1장당",
    "brand": "하기스",
    "type": "팬티형",
    "size": "5단계",
    "gender": "남녀공용"
  }
]

with open('test_prompt_data.json', 'w', encoding='utf-8') as f:
    json.dump(test_data, f, ensure_ascii=False, indent=2)

print("테스트 데이터 생성 완료. AI 원고 작성 시작...")
title, content = generate_blog_content('test_prompt_data.json', 'http://example.com/?category=kids')

with open('test_result_output.txt', 'w', encoding='utf-8') as f:
    f.write(f"[제목]\n{title}\n\n[본문]\n{content}")

print("결과가 test_result_output.txt 파일에 저장되었습니다.")
