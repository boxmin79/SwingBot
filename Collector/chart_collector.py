import os
import pandas as pd
import FinanceDataReader as fdr
from datetime import datetime, timedelta
import time

class ChartCollector:
    def __init__(self):
        # 경로 설정
        self.ticker_path = os.path.join('data', 'tickers', 'filtered_tickers.csv')
        self.save_path = os.path.join('data', 'chart')
        
        # 저장 폴더 생성
        if not os.path.exists(self.save_path):
            os.makedirs(self.save_path)
            print(f"[정보] 폴더 생성 완료: {self.save_path}")

    def collect_10_years(self):
        # 1. 필터링된 종목 리스트 읽기
        if not os.path.exists(self.ticker_path):
            print(f"[오류] 필터링된 종목 리스트가 없습니다. 먼저 필터링을 진행하세요.")
            return

        tickers_df = pd.read_csv(self.ticker_path, dtype={'code': str})
        
        # 2. 수집 기간 설정 (오늘부터 10년 전)
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=365 * 10)).strftime('%Y-%m-%d')
        
        total = len(tickers_df)
        print(f"[시작] {total}개 종목의 {start_date} ~ {end_date} 데이터를 수집합니다.")

        for i, row in tickers_df.iterrows():
            code = row['code']
            name = row['name']
            file_name = f"{code}.parquet"
            full_path = os.path.join(self.save_path, file_name)

            # 이미 파일이 존재하면 건너뛰기 (이어받기 기능)
            if os.path.exists(full_path):
                continue

            try:
                # 3. 데이터 수집 (FinanceDataReader 사용)
                # 수정주가가 기본으로 반영됩니다.
                df = fdr.DataReader(code, start_date, end_date)

                if not df.empty:
                    # 4. Parquet 파일로 저장
                    # index(날짜)를 포함하여 저장
                    df.to_parquet(full_path, engine='pyarrow', compression='snappy')
                    print(f"[{i+1}/{total}] {name}({code}) 저장 완료 - {len(df)}행")
                else:
                    print(f"[{i+1}/{total}] {name}({code}) 데이터가 비어있습니다.")

                # 웹 크롤링 차단 방지를 위한 미세 대기
                time.sleep(0.05)

            except Exception as e:
                print(f"[{i+1}/{total}] {name}({code}) 수집 중 오류 발생: {e}")
                continue

        print("\n[완료] 모든 데이터 수집 및 Parquet 변환이 끝났습니다.")

if __name__ == '__main__':
    collector = ChartCollector()
    collector.collect_10_years()