import os
import pandas as pd
import vectorbt as vbt
from pathlib import Path

def run_ultimate_bollinger_backtest(ticker, window=20, std_dev=2):
    # 1. 데이터 로드
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent 
    data_dir = project_root / 'data' / 'chart'
    log_dir = project_root / 'data' / 'backtest' / 'bollingerband' / 'detail'
    os.makedirs(log_dir, exist_ok=True)

    files = list(data_dir.glob(f"*{ticker}*.parquet"))
    if not files: return None
    df = pd.read_parquet(files[0])
    close = df['Close']

    # 2. 지표 계산 (BB, RSI, Bandwidth)
    bbands = vbt.BBANDS.run(close, window=window, alpha=std_dev)
    rsi = vbt.RSI.run(close, window=14).rsi
    
    # [핵심] 밴드 폭(Bandwidth) 계산: (상단 - 하단) / 중단
    bandwidth = bbands.bandwidth
    # 스퀴즈(Squeeze) 조건: 현재 밴드 폭이 최근 100일 중 하위 20% 수준으로 좁아졌을 때
    is_squeeze = bandwidth < bandwidth.rolling(100).quantile(0.2)

    # 3. 전략별 신호 생성
    
    # 전략 1: 역추세 (RSI 필터) - 승률 중심
    mr_entries = close.vbt.crossed_above(bbands.lower) & (rsi < 30)
    mr_exits = close.vbt.crossed_below(bbands.upper)

    # 전략 2: 추세추종 (RSI 필터) - 수익성 중심
    tf_entries = close.vbt.crossed_above(bbands.upper) & (rsi > 50) & (rsi < 70)
    tf_exits = close.vbt.crossed_below(bbands.middle)

    # 전략 3: 변동성 돌파 (Squeeze + Breakout) - 손익비 중심
    # 밴드가 수축된 상태에서(is_squeeze) 상단을 돌파할 때만 진입
    vol_entries = close.vbt.crossed_above(bbands.upper) & is_squeeze
    vol_exits = close.vbt.crossed_below(bbands.middle)

    # 4. 백테스트 실행 (3개 전략 비교)
    strat_names = ['MR_RSI', 'TF_RSI', 'Vol_Breakout']
    entries = pd.concat([mr_entries, tf_entries, vol_entries], axis=1, keys=strat_names)
    exits = pd.concat([mr_exits, tf_exits, vol_exits], axis=1, keys=strat_names)

    pf = vbt.Portfolio.from_signals(
        close, entries, exits, 
        init_cash=10_000_000, fees=0.002, slippage=0.0005, freq='D'
    )

    # 5. 결과 리포트 출력
    print(f"\n" + "="*85)
    print(f" Ticker: {ticker} | 볼린저 밴드 통합 전략 리포트")
    print("="*85)
    
    for col in pf.wrapper.columns:
        s = pf[col].stats()
        print(f"\n[ 전략: {col} ]")
        print(f"  - 총 수익률 (Total Return)   : {s.get('Total Return [%]', 0):>10.2f}%")
        print(f"  - 최대 낙폭 (Max Drawdown)   : {s.get('Max Drawdown [%]', 0):>10.2f}%")
        print(f"  - 샤프 지수 (Sharpe Ratio)   : {s.get('Sharpe Ratio', 0):>10.2f}")
        print(f"  - 승률 (Win Rate)            : {s.get('Win Rate [%]', 0):>10.2f}%")
        print(f"  - 매매 횟수 (Total Trades)   : {int(s.get('Total Trades', 0)):>10}회")
    print("\n" + "="*85)

    return pf

if __name__ == "__main__":
    run_ultimate_bollinger_backtest("005930")