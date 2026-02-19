import os
import pandas as pd
import vectorbt as vbt
import talib
from pathlib import Path

def run_bb_stoch_filter_backtest(ticker, window=20, std_dev=2):
    # 1. 데이터 로드
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent 
    data_dir = project_root / 'data' / 'chart'
    
    files = list(data_dir.glob(f"*{ticker}*.parquet"))
    if not files: return None
    df = pd.read_parquet(files[0])
    high, low, close = df['High'], df['Low'], df['Close']

    # 2. 지표 계산 (TA-Lib 활용)
    bbands = vbt.BBANDS.run(close, window=window, alpha=std_dev)
    
    # Stochastic (5, 3, 3): 단기 매매에 유용한 설정
    slowk, slowd = talib.STOCH(high, low, close, 
                               fastk_period=5, slowk_period=3, slowk_matype=0, 
                               slowd_period=3, slowd_matype=0)
    slowk = pd.Series(slowk, index=df.index)
    slowd = pd.Series(slowd, index=df.index)
    
    bandwidth = bbands.bandwidth
    is_squeeze = bandwidth < bandwidth.rolling(100).quantile(0.2)

    # 3. 전략별 신호 생성 (Stochastic 필터 적용)
    
    # 전략 1: 역추세 (하단 돌파 + 스토캐스틱 침체권)
    mr_entries = (close.vbt.crossed_above(bbands.lower)) & (slowk < 20)
    mr_exits = close.vbt.crossed_below(bbands.upper)

    # 전략 2: 추세추종 (상단 돌파 + 스토캐스틱 50 이상 강세)
    tf_entries = (close.vbt.crossed_above(bbands.upper)) & (slowk > 50)
    tf_exits = close.vbt.crossed_below(bbands.middle)

    # 전략 3: 변동성 돌파 (스퀴즈 + 상단 돌파 + 스토캐스틱 골든크로스)
    vol_entries = (close.vbt.crossed_above(bbands.upper)) & is_squeeze & (slowk > slowd)
    vol_exits = close.vbt.crossed_below(bbands.middle)

    # 4. 백테스트 실행
    strat_names = ['MR_Stoch', 'TF_Stoch', 'Vol_Stoch']
    entries = pd.concat([mr_entries, tf_entries, vol_entries], axis=1, keys=strat_names)
    exits = pd.concat([mr_exits, tf_exits, vol_exits], axis=1, keys=strat_names)

    pf = vbt.Portfolio.from_signals(
        close, entries, exits, 
        init_cash=10_000_000, fees=0.002, slippage=0.0005, freq='D'
    )

    # 5. 결과 리포트
    print(f"\n" + "="*85)
    print(f" Ticker: {ticker} | 볼린저 밴드 + 스토캐스틱 필터 리포트")
    print("="*85)
    
    for col in pf.wrapper.columns:
        s = pf[col].stats()
        print(f"\n[ 전략: {col} ]")
        print(f"  - 총 수익률 (Total Return)   : {s.get('Total Return [%]', 0):>10.2f}%")
        print(f"  - 최대 낙폭 (Max Drawdown)   : {s.get('Max Drawdown [%]', 0):>10.2f}%")
        print(f"  - 승률 (Win Rate)            : {s.get('Win Rate [%]', 0):>10.2f}%")
        print(f"  - 매매 횟수 (Total Trades)   : {int(s.get('Total Trades', 0)):>10}회")
    print("\n" + "="*85)

    return pf

if __name__ == "__main__":
    run_bb_stoch_filter_backtest("005930")