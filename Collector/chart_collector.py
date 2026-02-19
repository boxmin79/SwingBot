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
        
        # 시장 구분 맵핑 (KOSPI/KOSDAQ 판단용)
        self.market_map = self._get_market_map()
        
        # 저장 폴더 생성
        if not os.path.exists(self.save_path):
            os.makedirs(self.save_path)
            print(f"[정보] 폴더 생성 완료: {self.save_path}")

    def _get_market_map(self):
        """KOSPI, KOSDAQ 종목 리스트를 가져와 {종목코드: 시장명} 딕셔너리 생성"""
        print("[정보] 시장 구분 데이터를 동기화 중입니다...")
        try:
            df_kospi = fdr.StockListing('KOSPI')[['Code', 'Market']]
            df_kosdaq = fdr.StockListing('KOSDAQ')[['Code', 'Market']]
            combined = pd.concat([df_kospi, df_kosdaq])
            # { '005930': 'KOSPI', '091990': 'KOSDAQ' } 형태의 딕셔너리 반환
            return dict(zip(combined['Code'], combined['Market']))
        except Exception as e:
            print(f"[경고] 시장 구분 획득 실패: {e}")
            return {}

    def collect_10_years(self):
        if not os.path.exists(self.ticker_path):
            print(f"[오류] 필터링된 종목 리스트가 없습니다.")
            return

        tickers_df = pd.read_csv(self.ticker_path, dtype={'code': str})
        
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=365 * 10)).strftime('%Y-%m-%d')
        
        total = len(tickers_df)
        print(f"[시작] {total}개 종목의 데이터 수집을 시작합니다.")

        for i, row in tickers_df.iterrows():
            code = row['code']
            name = row['name']
            
            # 1. 시장 구분 확인 (KOSPI, KOSDAQ, 혹은 Unknown)
            market_prefix = self.market_map.get(code, "UNKNOWN")
            
            # 2. 파일명 생성 (예: KOSPI_005930.parquet)
            file_name = f"{market_prefix}_{code}.parquet"
            full_path = os.path.join(self.save_path, file_name)

            if os.path.exists(full_path):
                continue

            try:
                df = fdr.DataReader(code, start_date, end_date)

                if not df.empty:
                    df.to_parquet(full_path, engine='pyarrow', compression='snappy')
                    print(f"[{i+1}/{total}] {market_prefix} | {name}({code}) 저장 완료")
                else:
                    print(f"[{i+1}/{total}] {name}({code}) 데이터 없음")

                time.sleep(0.05)

            except Exception as e:
                print(f"[{i+1}/{total}] {name}({code}) 오류: {e}")
                continue

        print("\n[완료] 모든 데이터 수집 및 저장이 끝났습니다.")

if __name__ == '__main__':
    collector = ChartCollector()
    collector.collect_10_years()