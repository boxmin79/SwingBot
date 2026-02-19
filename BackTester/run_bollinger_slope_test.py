import os
import pandas as pd
from pathlib import Path
from datetime import datetime
# PYTHONPATH=. 설정으로 인해 루트 기준으로 임포트
from bollinger_trend_slope_backtester import BollingerTrendSlopeBacktester

def run_mass_backtest(start_date=None, end_date=None):
    project_root = Path(".") 
    # 사용자님의 환경에 맞춰 파일명이나 경로를 확인하세요 (예: filtered_tickers.csv)
    ticker_csv = project_root / "data" / "tickers" / "filtered_tickers.csv"
    summary_dir = project_root / "data" / "backtest" / "bollingerband" / "summary"
    os.makedirs(summary_dir, exist_ok=True)

    if not ticker_csv.exists():
        print(f"[오류] 파일 없음: {ticker_csv}")
        return

    ticker_df = pd.read_csv(ticker_csv)
    # 컬럼명이 'code'인 경우와 'ticker'인 경우를 모두 대응하기 위해 수정
    ticker_col = 'code' if 'code' in ticker_df.columns else 'ticker'
    tickers = ticker_df[ticker_col].astype(str).str.zfill(6).tolist()
    
    results_summary = []
    
    # 분석 기간 출력
    period_str = f"{start_date if start_date else '전체'} ~ {end_date if end_date else '현재'}"
    print(f"매스 백테스트 시작 (기간: {period_str})")
    
    for i, ticker in enumerate(tickers):
        try:
            # 클래스 생성 시 날짜 파라미터 전달
            tester = BollingerTrendSlopeBacktester(
                ticker, 
                start_date=start_date, 
                end_date=end_date
            )
            stats_dict = tester.run() 
            
            if stats_dict:
                summary_data = {
                    'ticker': ticker,
                    'Total Return [%]': stats_dict.get('Total Return [%]', 0),
                    'Max Drawdown [%]': stats_dict.get('Max Drawdown [%]', 0),
                    'Sharpe Ratio': stats_dict.get('Sharpe Ratio', 0),
                    'Win Rate [%]': stats_dict.get('Win Rate [%]', 0),
                    'Total Trades': stats_dict.get('Total Trades', 0)
                }
                results_summary.append(summary_data)
                
                if (i + 1) % 10 == 0:
                    print(f"[{i+1}/{len(tickers)}] {ticker} 완료")
                    
        except Exception as e:
            print(f"[에러] {ticker} 테스트 중 문제 발생: {e}")

    if results_summary:
        final_df = pd.DataFrame(results_summary)
        # 샤프 지수 기준으로 정렬
        final_df = final_df.sort_values(by='Sharpe Ratio', ascending=False)
        
        # 파일명에 기간 정보를 포함하면 나중에 관리하기 좋습니다.
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"slope_summary_{now}.csv"
        if start_date:
            file_name = f"slope_summary_from_{start_date.replace('-', '')}_{now}.csv"
            
        final_df.to_csv(summary_dir / file_name, index=False, encoding='utf-8-sig')
        print(f"\n백테스트 완료. 결과 저장됨: {file_name}")

if __name__ == "__main__":
    # 1. 최근 1년치만 돌리고 싶을 때
    run_mass_backtest(start_date="2025-02-19", end_date="2026-02-19")
    
    # 2. 전체 기간을 돌리고 싶을 때
    # run_mass_backtest()