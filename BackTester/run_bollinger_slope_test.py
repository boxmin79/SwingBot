import os
import pandas as pd
from pathlib import Path
from datetime import datetime
# PYTHONPATH=. 설정으로 인해 루트 기준으로 임포트
from bollinger_trend_slope_backtester import BollingerTrendSlopeBacktester

def run_mass_backtest():
    project_root = Path(".") 
    ticker_csv = project_root / "data" / "tickers" / "filtered_tickers.csv"
    summary_dir = project_root / "data" / "backtest" / "bollingerband" / "summary"
    os.makedirs(summary_dir, exist_ok=True)

    if not ticker_csv.exists():
        print(f"[오류] 파일 없음: {ticker_csv}")
        return

    ticker_df = pd.read_csv(ticker_csv)
    tickers = ticker_df['code'].astype(str).str.zfill(6).tolist()
    
    results_summary = []
    
    for i, ticker in enumerate(tickers):
        try:
            tester = BollingerTrendSlopeBacktester(ticker)
            stats_dict = tester.run() # 이제 딕셔너리를 반환함
            
            if stats_dict:
                # 딕셔너리에서 안전하게 값 추출
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
        final_df = final_df.sort_values(by='Sharpe Ratio', ascending=False)
        
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_df.to_csv(summary_dir / f"slope_summary_{now}.csv", index=False, encoding='utf-8-sig')
        print(f"\n백테스트 완료. 요약 파일 저장됨.")

if __name__ == "__main__":
    run_mass_backtest()