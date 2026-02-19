import pandas as pd
import numpy as np
from pathlib import Path

def validate_recent_year_performance(elite_csv, detail_dir):
    # 1. 엘리트 종목 리스트 로드
    elite_df = pd.read_csv(elite_csv)
    tickers = elite_df['ticker'].astype(str).str.zfill(6).tolist()
    
    results = []
    
    # 분석 기간 설정 (최근 1년)
    end_date = pd.Timestamp('2026-02-19')
    start_date = end_date - pd.DateOffset(years=1)
    
    print(f"분석 기간: {start_date.date()} ~ {end_date.date()}")
    
    for ticker in tickers:
        file_path = Path(detail_dir) / f"{ticker}.parquet"
        if not file_path.exists():
            continue
            
        # 상세 매매 데이터 로드
        df = pd.read_parquet(file_path)
        df['Exit Timestamp'] = pd.to_datetime(df['Exit Timestamp'])
        
        # 최근 1년 거래만 필터링
        recent_trades = df[df['Exit Timestamp'] >= start_date].copy()
        
        if len(recent_trades) > 0:
            # 최근 1년 지표 계산
            recent_return = recent_trades['Return'].sum() * 100
            recent_mdd = recent_trades['PnL'].expanding().max() - recent_trades['PnL'] # 단순화된 계산
            # 실제 샤프지수 계산을 위해서는 일별 수익률이 필요하므로 여기선 거래별 수익률로 대체
            recent_sharpe = recent_trades['Return'].mean() / recent_trades['Return'].std() if len(recent_trades) > 1 else 0
            
            results.append({
                'ticker': ticker,
                '10Y_Return': elite_df[elite_df['ticker'] == int(ticker)]['Total Return [%]'].values[0],
                '1Y_Return': recent_return,
                '1Y_Trades': len(recent_trades),
                '1Y_Sharpe_Proxy': recent_sharpe
            })
            
    recent_summary = pd.DataFrame(results)
    
    # 10년 성과 대비 최근 1년 비중 확인
    recent_summary['1Y_Contribution'] = (recent_summary['1Y_Return'] / recent_summary['10Y_Return']) * 100
    
    # 결과 저장
    recent_summary.to_csv('recent_1y_validation.csv', index=False)
    
    print("\n--- 최근 1년 성과 검증 요약 ---")
    print(recent_summary.sort_values('1Y_Return', ascending=False).head(10))
    
    return recent_summary

# 사용법:
if __name__ == "__main__":
    elite_tickers_sharpe_file = "data/elite_tickers_sharpe_07.csv"
    validate_recent_year_performance(elite_tickers_sharpe_file, 'data/backtest/bollingerband/detail/')