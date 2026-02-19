import pandas as pd
import vectorbt as vbt
import talib
from pathlib import Path

def run_flexible_bb_backtest(ticker):
    # 1. 데이터 로드
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent 
    data_dir = project_root / 'data' / 'chart'
    
    files = list(data_dir.glob(f"*{ticker}*.parquet"))
    if not files: return None
    df = pd.read_parquet(files[0])
    
    high, low, close, volume = df['High'], df['Low'], df['Close'], df['Volume']

    # 2. 보조 지표 계산
    bbands = vbt.BBANDS.run(close, window=20, alpha=2)
    rsi = talib.RSI(close, timeperiod=14)
    mfi = talib.MFI(high, low, close, volume, timeperiod=14)
    adx = talib.ADX(high, low, close, timeperiod=14)
    macd, macdsignal, _ = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
    obv = talib.OBV(close, volume)

    # 3. 전략별 유연한(OR) 신호 생성
    
    # [전략 1: 역추세 유연화] - BB 하단 돌파 + (RSI < 30 또는 MFI < 30)
    # 둘 중 하나만 과매도권이어도 "에너지가 충분히 낮다"고 판단
    mr_entries = (close.vbt.crossed_above(bbands.lower)) & ((rsi < 30) | (mfi < 30))
    mr_exits = close.vbt.crossed_below(bbands.upper)

    # [전략 2: 추세추종 유연화] - BB 상단 돌파 + (ADX > 20 또는 MACD 골든크로스 상태)
    # ADX 기준을 20으로 낮추고, MACD가 정배열이면 진입 허용
    tf_entries = (close.vbt.crossed_above(bbands.upper)) & ((adx > 20) | (macd > macdsignal))
    tf_exits = close.vbt.crossed_below(bbands.middle)

    # [전략 3: 변동성 돌파 유연화] - 스퀴즈 상태 + BB 상단 돌파 + (OBV 상승 또는 가격 상승세)
    is_squeeze = bbands.bandwidth < bbands.bandwidth.rolling(100).quantile(0.2)
    vol_entries = (close.vbt.crossed_above(bbands.upper)) & is_squeeze & ((obv > obv.shift(1)) | (close > close.shift(1)))
    vol_exits = close.vbt.crossed_below(bbands.middle)

    # 4. 백테스트 실행
    strat_names = ['MR_Flexible', 'TF_Flexible', 'Vol_Flexible']
    entries = pd.concat([mr_entries, tf_entries, vol_entries], axis=1, keys=strat_names)
    exits = pd.concat([mr_exits, tf_exits, vol_exits], axis=1, keys=strat_names)

    pf = vbt.Portfolio.from_signals(
        close, entries, exits, 
        init_cash=10_000_000, fees=0.002, slippage=0.0005, freq='D'
    )

    # 5. 결과 리포트
    print(f"\n" + "="*85)
    print(f" Ticker: {ticker} | 볼린저 밴드 유연화 전략 (OR 조건) 리포트")
    print("="*85)
    
    for col in pf.wrapper.columns:
        s = pf[col].stats()
        print(f"\n[ 전략: {col} ]")
        print(f"  - 수익률 (Total Return)  : {s.get('Total Return [%]', 0):>10.2f}%")
        print(f"  - 낙폭 (Max Drawdown)    : {s.get('Max Drawdown [%]', 0):>10.2f}%")
        print(f"  - 승률 (Win Rate)        : {s.get('Win Rate [%]', 0):>10.2f}%")
        print(f"  - 매매 횟수 (Trades)     : {int(s.get('Total Trades', 0)):>10}회")
    
    return pf

if __name__ == "__main__":
    run_flexible_bb_backtest("005930")