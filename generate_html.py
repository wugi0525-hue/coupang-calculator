import json
import os
from jinja2 import Environment, FileSystemLoader

def generate_index_html():
    """
    정렬된 final_ranking.json 데이터를 읽어와 template.html에 주입하고,
    최종 결과물인 index.html을 생성하는 함수 (정적 사이트 생성, SSG 방식).
    """
    
    # 1. 정렬된 최종 결과 데이터 읽기
    data_file = 'final_ranking.json'
    
    if not os.path.exists(data_file):
        print(f"오류: {data_file} 파일을 찾을 수 없습니다.")
        print("먼저 calc_logic.py를 실행하여 데이터를 정렬해 주세요.")
        return

    with open(data_file, 'r', encoding='utf-8') as f:
        try:
            items = json.load(f)
        except json.JSONDecodeError:
            print("오류: JSON 파일 파싱 실패")
            return

    # 2. Jinja2 환경 설정 (templates 폴더 안의 템플릿 로딩)
    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template('template.html')

    # 3. 템플릿 렌더링 (데이터 주입)
    # 템플릿의 {% for item in items %} 영역에 파이썬 리스트 items가 전달됨
    rendered_html = template.render(items=items)

    # 4. 최종 index.html 파일 저장
    output_file = 'index.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(rendered_html)

    print(f"성공: {output_file} 가 생성되었습니다. (총 {len(items)}개 상품 반영)")
    print(f"생성된 index.html을 브라우저에서 열어 확인하세요!")

if __name__ == '__main__':
    generate_index_html()
