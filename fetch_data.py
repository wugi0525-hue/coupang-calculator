import os
import json
from dotenv import load_dotenv

# 로컬 환경변수(.env) 로드
load_dotenv()

class CoupangAPI:
    def __init__(self):
        self.access_key = os.environ.get('COUPANG_ACCESS_KEY')
        self.secret_key = os.environ.get('COUPANG_SECRET_KEY')
    
    def search_products(self, keyword, limit=20):
        # API 뚫리기 전까지는 임시 Mock 데이터를 반환 (우회 방안)
        if not self.access_key or self.access_key == 'YOUR_ACCESS_KEY':
            print("⚠️ [개발 모드] API 키가 감지되지 않아 로컬 mock_data.json을 불러옵니다.")
            with open('mock_data.json', 'r', encoding='utf-8') as f:
                return json.load(f)
                
        print(f"✅ 실제 API 호출 진행 중... 키워드: {keyword}")
        # 실제 API 호출 로직은 향후 API Key 발급 확정 시 반영
        return []

if __name__ == "__main__":
    # 첫 번째 타겟 품목: 단백질 보충제
    target_keyword = "단백질 보충제"
    
    api = CoupangAPI()
    data = api.search_products(target_keyword)
    
    # 향후 파이프라인(계산 모듈)으로 넘겨질 순수 raw 데이터 저장
    with open('raw_data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    print(f"✅ {target_keyword} 검색 완료 -> raw_data.json 갱신 완료 (총 {len(data)}건)")
