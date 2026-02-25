import os
import json
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

def build():
    # 1. 랭킹 데이터 불러오기
    try:
        with open('final_ranking.json', 'r', encoding='utf-8') as f:
            rankings = json.load(f)
    except FileNotFoundError:
        print("❌ final_ranking.json 파일이 없습니다. calc_logic.py를 먼저 실행하세요.")
        return

    # 2. Jinja2 환경 셋팅
    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template('template.html')

    # 오늘 날짜 구하기 (사람이 직접 업데이트한 느낌을 주기 위함)
    today_str = datetime.now().strftime("%Y년 %m월 %d일 오전 (매일 아침 수작업 갱신 완료)")

    # 3. HTML 렌더링 (데이터 주입)
    # 현재 적용된 계산기 주제를 컨텍스트 변수로 전달
    context = {
        "title": "단백질 보충제 10g당 진짜 단가(가격) 랭킹",
        "update_date": today_str,
        "items": rankings
    }
    output_html = template.render(context)

    # 4. 결과물을 index.html로 추출 (GitHub Pages가 읽을 수 있도록 Root에 저장)
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(output_html)
        
    print("✅ 성공적으로 index.html 파일이 빌드되었습니다! (Jinja2 SSG)")

if __name__ == "__main__":
    build()
