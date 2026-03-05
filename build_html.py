import os
import sys
import json
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

# 윈도우 콘솔 한글 인코딩 에러 방지 (UTF-8 강제)
sys.stdout.reconfigure(encoding='utf-8')

def build():
    # 1. 랭킹 데이터 불러오기
    try:
        with open('data.json', 'r', encoding='utf-8') as f:
            rankings = json.load(f)
    except FileNotFoundError:
        print("❌ data.json 파일이 없습니다. calc_logic.py를 먼저 실행하세요.")
        return

    # Jinja2 템플릿에서 사용할 수 있도록 포맷팅된 데이터 준비는 더 이상 파이썬에서 안 해도 됨 (JS로 위임)
    # 대표 타이틀 
    dynamic_title = "🔥 실시간 기저귀 1장당 진짜 단가 랭킹 🔥"
        
    # Jinja2 환경 셋팅
    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template('template.html')

    # 오늘 날짜
    today_str = datetime.now().strftime("%Y년 %m월 %d일 오전 (매일 자동 갱신)")

    # HTML 렌더링 (전체 데이터를 JSON 문자열로 주입)
    context = {
        "title": dynamic_title,
        "update_date": today_str,
        "items_json": json.dumps(rankings, ensure_ascii=False)
    }
    output_html = template.render(context)

    # 4. 결과물을 index.html로 추출 (GitHub Pages가 읽을 수 있도록 Root에 저장)
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(output_html)
        
    print("✅ 성공적으로 index.html 파일이 빌드되었습니다! (Jinja2 SSG)")

if __name__ == "__main__":
    build()
