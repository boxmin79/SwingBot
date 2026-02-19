import os
import pandas as pd
import vectorbt as vbt
import talib
from pathlib import Path

def run_cci_enhanced_backtest(ticker, window=20, std_dev=2):
    # 1. 데이터 로드
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent 
    data_dir = project_root / 'data' / 'chart'
    
    files = list(data_dir.glob(f"*{ticker}*.parquet"))
    if not files: return None
    df = pd.read_parquet(files[0])
    high, low, close, volume = df['High'], df['Low'], df['Close'], df['Volume']

    # 2. 지표 계산 (TA-Lib 활용)
    bbands = vbt.BBANDS.run(close, window=window, alpha=std_dev)
    
    # CCI (14일 기준): +100 이상은 과매수, -100 이하는 과매도
    cci = talib.CCI(high, low, close, timeperiod=14)
    cci = pd.Series(cci, index=df.index)
    
    # OBV: 거래량의 유입/유출 확인
    obv = talib.OBV(close, volume)
    obv = pd.Series(obv, index=df.index)
    
    bandwidth = bbands.bandwidth
    is_squeeze = bandwidth < bandwidth.rolling(100).quantile(0.2)

    # 3. 전략별 신호 생성
    
    # 전략 1: 역추세 (CCI 과매도 필터)
    # 주가가 하단 밴드 위로 올라오면서 CCI가 바닥(-100)을 치고 올라올 때
    mr_entries = close.vbt.crossed_above(bbands.lower) & (cci < -100)
    mr_exits = close.vbt.crossed_below(bbands.upper)

    # 전략 2: 추세추종 (CCI 강세 필터 + OBV 상승)
    # 상단 밴드 돌파 시 CCI가 100 이상이며, 전날보다 거래량 유입(OBV)이 있을 때
    tf_entries = close.vbt.crossed_above(bbands.upper) & (cci > 100) & (obv > obv.shift(1))
    tf_exits = close.vbt.crossed_below(bbands.middle)

    # 전략 3: 변동성 돌파 (Squeeze + CCI)
    # 밴드가 좁아진 상태에서 상단 돌파 시 CCI가 0선을 돌파하며 에너지가 붙을 때
    vol_entries = close.vbt.crossed_above(bbands.upper) & is_squeeze & (cci > 0)
    vol_exits = close.vbt.crossed_below(bbands.middle)

    # 4. 백테스트 실행
    strat_names = ['MR_CCI', 'TF_CCI', 'Vol_Squeeze_CCI']
    entries = pd.concat([mr_entries, tf_entries, vol_entries], axis=1, keys=strat_names)
    exits = pd.concat([mr_exits, tf_exits, vol_exits], axis=1, keys=strat_names)

    pf = vbt.Portfolio.from_signals(
        close, entries, exits, 
        init_cash=10_000_000, fees=0.002, slippage=0.0005, freq='D'
    )

    # 5. 결과 리포트
    print(f"\n" + "="*85)
    print(f" Ticker: {ticker} | 볼린저 밴드 + CCI 필터 전략 리포트")
    print("="*85)
    
    for col in pf.wrapper.columns:
        s = pf[col].stats()
        print(f"\n[ 전략: {col} ]")
        print(f"  - 총 수익률 (Total Return)   : {s.get('Total Return [%]', 0):>10.2f}%")
        print(f"  - 최대 낙폭 (Max Drawdown)   : {s.get('Max Drawdown [%]', 0):>10.2f}%")
        print(f"  - 승률 (Win Rate)            : {s.get('Win Rate [%]', 0):>10.2f}%")
        print(f"  - 매매 횟수 (Total Trades)   : {int(s.get('Total Trades', 0)):>10}회")
        print(f"  - 손익비 (Profit Factor)     : {s.get('Profit Factor', 0):>10.2f}")
    print("\n" + "="*85)

    return pf

if __name__ == "__main__":
    run_cci_enhanced_backtest("005930")