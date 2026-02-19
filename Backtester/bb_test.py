import os
import sys
import pandas as pd
import vectorbt as vbt
import numpy as np
from pathlib import Path

def run_bollinger_backtest_multi(ticker, window=20, std_dev=2):
    # 1. 경로 설정 (절대 경로 기준)
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent 
    data_dir = project_root / 'data' / 'chart'
    
    # 기록을 위한 폴더 경로 설정
    log_dir = project_root / 'data' / 'backtest' / 'bollingerband' / 'detail'
    os.makedirs(log_dir, exist_ok=True)

    # 2. 데이터 파일 찾기 및 로드
    files = list(data_dir.glob(f"*{ticker}*.parquet"))
    if not files:
        print(f"[오류] {ticker} 데이터 파일을 찾을 수 없습니다.")
        return None
    
    df = pd.read_parquet(files[0])
    close = df['Close']

    # 3. 지표 계산
    bbands = vbt.BBANDS.run(close, window=window, alpha=std_dev)

    # 4. 전략별 신호 생성 (멀티 인덱스 구성)
    # 역추세(Mean Reversion) 신호
    mr_entries = close.vbt.crossed_above(bbands.lower)
    mr_exits = close.vbt.crossed_below(bbands.upper)

    # 추세추종(Trend Following) 신호
    tf_entries = close.vbt.crossed_above(bbands.upper)
    tf_exits = close.vbt.crossed_below(bbands.middle) # middle 사용

    # 두 전략의 신호를 가로로 결합 (keys 인자가 멀티 인덱스의 이름이 됨)
    entries = pd.concat([mr_entries, tf_entries], axis=1, keys=['Mean_Reversion', 'Trend_Following'])
    exits = pd.concat([mr_exits, tf_exits], axis=1, keys=['Mean_Reversion', 'Trend_Following'])

    # 5. 포트폴리오 생성 (단 한 번의 호출로 두 전략 동시 계산)
    pf = vbt.Portfolio.from_signals(
        close, 
        entries, 
        exits, 
        init_cash=10_000_000, 
        fees=0.002, 
        slippage=0.0005,
        freq='D'
    )

    # 6. 매매 내역 추출 및 단일 파일 저장
    # 멀티 인덱스 결과의 records_readable에는 'Column' 컬럼에 전략명이 자동으로 들어갑니다.
    trade_history = pf.trades.records_readable
    
    if not trade_history.empty:
        output_path = log_dir / f"{ticker}.parquet"
        trade_history.to_parquet(output_path, index=False)
        print(f"[기록 완료] 통합 매매 내역 저장: {output_path}")
    else:
        print(f"[정보] {ticker} 종목은 생성된 매매 신호가 없습니다.")

    # 7. 결과 비교 출력
    print(f"\n" + "="*70)
    print(f" Ticker: {ticker} | 전략별 상세 통계 리포트")
    print("="*70)
    
    for col in pf.wrapper.columns:
        s = pf[col].stats()
        
        print(f"\n[ 전략: {col} ]")
        # .get()을 사용하여 이름이 다를 경우에도 에러 방지
        print(f"  - 총 수익률 (Total Return)   : {s.get('Total Return [%]', 0):>10.2f}%")
        print(f"  - 벤치마크 수익률            : {s.get('Benchmark Return [%]', 0):>10.2f}%")
        print(f"  - 최대 낙폭 (Max Drawdown)   : {s.get('Max Drawdown [%]', 0):>10.2f}%")
        print(f"  - 샤프 지수 (Sharpe Ratio)   : {s.get('Sharpe Ratio', 0):>10.2f}")
        print(f"  - 승률 (Win Rate)            : {s.get('Win Rate [%]', 0):>10.2f}%")
        print(f"  - 매매 횟수 (Total Trades)   : {int(s.get('Total Trades', 0)):>10}회")
        
        # 보유 기간은 버전마다 이름이 다를 수 있어 후보군을 체크합니다.
        duration = s.get('Avg Holding Period') or s.get('Avg Duration') or "N/A"
        print(f"  - 평균 보유 기간             : {duration:>10}")
    
    print("\n" + "="*70)



    pf['Mean_Reversion'].plot().show()
    pf['Trend_Following'].plot().show()



    return pf

if __name__ == "__main__":
    # 삼성전자 테스트
    pf = run_bollinger_backtest_multi("005930")
    print(pf)