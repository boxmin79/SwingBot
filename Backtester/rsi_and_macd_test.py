import os
import pandas as pd
import vectorbt as vbt
import talib
from pathlib import Path

def run_rsi_macd_ultimate_backtest(ticker):
    # 1. 데이터 로드
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent 
    data_dir = project_root / 'data' / 'chart'
    
    files = list(data_dir.glob(f"*{ticker}*.parquet"))
    if not files: return None
    df = pd.read_parquet(files[0])
    close = df['Close']

    # 2. 지표 계산 (TA-Lib 활용)
    # RSI (14일)
    rsi = talib.RSI(close, timeperiod=14)
    rsi = pd.Series(rsi, index=df.index)
    
    # MACD (12, 26, 9)
    macd, macdsignal, macdhist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
    macd = pd.Series(macd, index=df.index)
    macdsignal = pd.Series(macdsignal, index=df.index)

    # 3. 전략별 신호 생성
    
    # 전략 1: RSI 진입 + MACD 추세 홀딩 (TF_RSI_MACD)
    # 진입: RSI가 50을 돌파하며 상승 탄력이 붙을 때
    # 매도: MACD가 시그널선을 하향 돌파(데드크로스)할 때까지 홀딩
    tf_entries = (rsi.vbt.crossed_above(50)) & (macd > macdsignal)
    tf_exits = macd.vbt.crossed_below(macdsignal)

    # 전략 2: RSI 과매도 반등 + MACD 확인 (MR_RSI_MACD)
    # 진입: RSI가 30 이하에서 탈출 + MACD 히스토그램 상승 반전
    mr_entries = (rsi.vbt.crossed_above(30)) & (macdhist > macdhist.shift(1))
    mr_exits = (rsi > 70) | (macd.vbt.crossed_below(macdsignal))

    # 4. 백테스트 실행
    strat_names = ['TF_RSI_MACD', 'MR_RSI_MACD']
    entries = pd.concat([tf_entries, mr_entries], axis=1, keys=strat_names)
    exits = pd.concat([tf_exits, mr_exits], axis=1, keys=strat_names)

    pf = vbt.Portfolio.from_signals(
        close, entries, exits, 
        init_cash=10_000_000, fees=0.002, slippage=0.0005, freq='D'
    )

    # 5. 결과 리포트
    print(f"\n" + "="*85)
    print(f" Ticker: {ticker} | RSI(진입) + MACD(홀딩) 전략 리포트")
    print("="*85)
    
    for col in pf.wrapper.columns:
        s = pf[col].stats()
        print(f"\n[ 전략: {col} ]")
        print(f"  - 총 수익률 (Total Return)   : {s.get('Total Return [%]', 0):>10.2f}%")
        print(f"  - 최대 낙폭 (Max Drawdown)   : {s.get('Max Drawdown [%]', 0):>10.2f}%")
        print(f"  - 샤프 지수 (Sharpe Ratio)   : {s.get('Sharpe Ratio', 0):>10.2f}")
        print(f"  - 승률 (Win Rate)            : {s.get('Win Rate [%]', 0):>10.2f}%")
        print(f"  - 매매 횟수 (Total Trades)   : {int(s.get('Total Trades', 0)):>10}회")
        print(f"  - 평균 보유 기간 (Avg Duration) : {s.get('Avg Holding Period', 'N/A')}")
    print("\n" + "="*85)

    return pf

if __name__ == "__main__":
    run_rsi_macd_ultimate_backtest("005930")