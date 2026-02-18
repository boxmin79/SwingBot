import os
import pandas as pd
import time
from API import KiwoomAPI

class StockListManager(KiwoomAPI):
    def __init__(self):
        super().__init__()
        self.base_path = os.path.join(os.getcwd(), 'data', 'tickers')
        
        if not os.path.exists(self.base_path):
            os.makedirs(self.base_path)
            print(f"[정보] 폴더 생성 완료: {self.base_path}")

    def save_market_tickers(self, market_code, market_name):
        """시장별 종목 리스트 수집 및 저장"""
        api_id = "ka10099" 
        args = {
            "mrkt_tp": market_code, 
            "cont_yn": "N", 
            "next_key": ""
        }

        print(f"\n[요청] {market_name} 종목 리스트를 가져오는 중...")
        time.sleep(1.0)  # 429 에러 방지
        response = self._get_response(api_id, **args)

        if response and response.get('return_code') == 0:
            df = pd.DataFrame(response['list'])
            file_path = os.path.join(self.base_path, f"{market_name}_tickers.csv")
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            print(f"[성공] {market_name} 리스트 저장 완료: {len(df)}종목")
            return True
        return False

    def run_ticker_filter(self):
        """marketName 및 auditInfo를 포함한 정밀 필터링 로직"""
        kospi_path = os.path.join(self.base_path, "KOSPI_tickers.csv")
        kosdaq_path = os.path.join(self.base_path, "KOSDAQ_tickers.csv")

        if not os.path.exists(kospi_path) or not os.path.exists(kosdaq_path):
            print("[오류] 원본 CSV 파일이 없습니다.")
            return

        # 1. 데이터 로드 (코드는 문자열로 처리하여 앞의 0 보존)
        kospi = pd.read_csv(kospi_path, dtype={'code': str})
        kosdaq = pd.read_csv(kosdaq_path, dtype={'code': str})
        df = pd.concat([kospi, kosdaq], ignore_index=True)
        initial_count = len(df)

        # 2. marketName 필터링: '거래소'와 '코스닥'만 포함 (ETN 등 제외)
        valid_markets = ['거래소', '코스닥']
        df = df[df['marketName'].isin(valid_markets)]

        # 3. [추가됨] auditInfo 필터링: "정상" 종목만 추출
        # '투자주의환기종목' 등 비정상 종목을 제거합니다.
        df = df[df['auditInfo'] == '정상']

        # 4. 종목코드 규칙 필터링: 보통주만 선택 (끝자리 '0')
        df = df[df['code'].str.endswith('0')]

        # 5. 상태 및 기업구분 필터링
        # - 관리/주의 종목 제외
        df = df[~df['state'].str.contains('관리|주의', na=False)]
        # - 스팩 및 외국기업 제외
        df = df[~df['companyClassName'].str.contains('스팩|외국기업', na=False)]

        # 6. 가격 필터링: 1,000원 미만 동전주 제외
        df['lastPrice_int'] = pd.to_numeric(df['lastPrice'], errors='coerce')
        df = df[df['lastPrice_int'] >= 1000]

        # 7. 최종 결과 저장
        filtered_path = os.path.join(self.base_path, "filtered_tickers.csv")
        df.to_csv(filtered_path, index=False, encoding='utf-8-sig')
        
        print(f"\n[최종 필터링 완료]")
        print(f"- 원본 합계: {initial_count}개")
        print(f"- '정상' 종목 필터 후: {len(df)}개")
        print(f"- 제거된 종목 수: {initial_count - len(df)}개")
        print(f"- 저장 완료: {filtered_path}")

if __name__ == '__main__':
    manager = StockListManager()
    if manager.save_market_tickers("0", "KOSPI"):
        manager.save_market_tickers("10", "KOSDAQ")
    manager.run_ticker_filter()