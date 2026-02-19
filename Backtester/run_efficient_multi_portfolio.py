import os
import pandas as pd
import vectorbt as vbt
import numpy as np
from pathlib import Path

def run_refined_top_portfolio(csv_path, rsi_window=14, rsi_entry=50):
    # 1. 데이터 로드 및 통합
    if not os.path.exists(csv_path):
        print(f"파일을 찾을 수 없습니다: {csv_path}")
        return
    
    ticker_df = pd.read_csv(csv_path)
    ticker_list = ticker_df['code'].astype(str).str.zfill(6).tolist()
    data_dir = Path('data/chart')
    
    close_dict = {}
    print(f"데이터 로드 중... (대상: {len(ticker_list)}개 종목)")
    
    for ticker in ticker_list:
        files = list(data_dir.glob(f"*{ticker}*.parquet"))
        if files:
            df = pd.read_parquet(files[0])
            # 데이터가 너무 짧으면 지표 계산 불가하므로 100일 이상만
            if len(df) > 100:
                close_dict[ticker] = df['Close']
    
    if not close_dict:
        print("조건을 만족하는 데이터가 없습니다.")
        return

    close_df = pd.DataFrame(close_dict).ffill()
    print(f"데이터 통합 완료: {close_df.shape[1]}개 종목, {len(close_df)}일치 데이터")

    # 2. 지표 계산 (인덱스 에러 방지용 컬럼 덮어쓰기 포함)
    bbands = vbt.BBANDS.run(close_df, window=20, alpha=2)
    rsi = vbt.RSI.run(close_df, window=rsi_window).rsi
    
    bb_upper = bbands.upper
    bb_upper.columns = close_df.columns
    
    bb_middle = bbands.middle
    bb_middle.columns = close_df.columns
    
    rsi_clean = rsi
    rsi_clean.columns = close_df.columns

    # 3. 신호 생성
    entries = (close_df.vbt.crossed_above(bb_upper)) & (rsi_clean > rsi_entry)
    exits = close_df.vbt.crossed_below(bb_middle)

    # 4. 개별 종목 성과 측정
    pf = vbt.Portfolio.from_signals(
        close_df, entries, exits, 
        init_cash=10_000_000, fees=0.002, slippage=0.0005, freq='D'
    )
    
    # [수정 완료] pf.total_trades() 대신 pf.trades.count() 사용
    total_return = pf.total_return()
    sharpe_ratio = pf.sharpe_ratio()
    max_drawdown = pf.max_drawdown()
    total_trades = pf.trades.count()  # <--- 이 부분이 수정되었습니다.
    
    stats_df = pd.DataFrame({
        'Total Return [%]': total_return * 100,
        'Max Drawdown [%]': max_drawdown * 100,
        'Sharpe Ratio': sharpe_ratio,
        'Total Trades': total_trades
    })
    
    # 5. [필터링] 우량 종목 선별
    # - 매매 횟수 10회 이상 (통계적 유의성 확보)
    # - 샤프 지수가 유효한 값 (inf/nan 제외)
    # - 수익률 > 0 (손실 종목 제외)
    clean_mask = (stats_df['Total Trades'] >= 10) & \
                 (np.isfinite(stats_df['Sharpe Ratio'])) & \
                 (stats_df['Total Return [%]'] > 0)
    
    clean_stats = stats_df[clean_mask].sort_values(by='Sharpe Ratio', ascending=False)

    print("\n[ 검증된 상위 10개 종목 리스트 ]")
    print(clean_stats.head(10))

    # 6. 상위 30개 종목으로 '정예 포트폴리오' 구성
    top_30_tickers = clean_stats.index[:30].tolist()
    
    if not top_30_tickers:
        print("조건을 만족하는 종목이 없습니다. 필터 조건을 완화해 보세요.")
        return

    # 정예 종목 통합 백테스트
    elite_pf = vbt.Portfolio.from_signals(
        close_df[top_30_tickers], 
        entries[top_30_tickers], 
        exits[top_30_tickers],
        init_cash=10_000_000, 
        fees=0.002, 
        slippage=0.0005, 
        freq='D',
        cash_sharing=True,
        group_by=True
    )

    # 7. 최종 통합 성과 출력
    print("\n" + "="*85)
    print(f" 🏆 [정예 상위 {len(top_30_tickers)}개 종목 통합 포트폴리오 성과] ")
    print("="*85)
    s = elite_pf.stats()
    print(f"  - 총 수익률 (Total Return)   : {s.get('Total Return [%]', 0):>10.2f}%")
    print(f"  - 최대 낙폭 (Max Drawdown)   : {s.get('Max Drawdown [%]', 0):>10.2f}%")
    print(f"  - 샤프 지수 (Sharpe Ratio)   : {s.get('Sharpe Ratio', 0):>10.2f}")
    print(f"  - 승률 (Win Rate)            : {s.get('Win Rate [%]', 0):>10.2f}%")
    print(f"  - 매매 횟수 (Total Trades)   : {int(s.get('Total Trades', 0)):>10}회")
    print(f"  - 기대 수익 (Expectancy)     : {s.get('Expectancy', 0):>10.2f}")
    print("="*85)

    return elite_pf

if __name__ == "__main__":
    csv_path = "data/tickers/filtered_tickers.csv"
    run_refined_top_portfolio(csv_path)