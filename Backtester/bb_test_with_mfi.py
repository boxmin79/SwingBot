import os
import pandas as pd
import vectorbt as vbt
import talib
from pathlib import Path

def run_mfi_with_stops(ticker, window=20, std_dev=2, tp=0.15, sl=0.07):
    # 1. 데이터 로드
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent 
    data_dir = project_root / 'data' / 'chart'
    
    files = list(data_dir.glob(f"*{ticker}*.parquet"))
    if not files: return None
    df = pd.read_parquet(files[0])
    
    high, low, close, volume = df['High'], df['Low'], df['Close'], df['Volume']

    # 2. 지표 계산
    bbands = vbt.BBANDS.run(close, window=window, alpha=std_dev)
    mfi = pd.Series(talib.MFI(high, low, close, volume, timeperiod=14), index=df.index)
    
    bandwidth = bbands.bandwidth
    is_squeeze = bandwidth < bandwidth.rolling(100).quantile(0.2)

    # 3. 진입 신호 (Exits는 Portfolio 단계에서 Stop으로 제어하므로 기본 신호만 생성)
    mr_entries = (close.vbt.crossed_above(bbands.lower)) & (mfi < 30) # 과매도 기준 30으로 완화
    tf_entries = (close.vbt.crossed_above(bbands.upper)) & (mfi > 50)
    vol_entries = (close.vbt.crossed_above(bbands.upper)) & is_squeeze

    strat_names = ['MR_MFI', 'TF_MFI', 'Vol_Breakout']
    entries = pd.concat([mr_entries, tf_entries, vol_entries], axis=1, keys=strat_names)

    # 4. 백테스트 실행 (손절/익절 파라미터 추가)
    # tp_stop: 익절 비율, sl_stop: 손절 비율
    pf = vbt.Portfolio.from_signals(
        close, 
        entries, 
        exits=None, # 매도 신호 대신 Stop 로직 우선 사용 가능
        init_cash=10_000_000, 
        fees=0.002, 
        slippage=0.0005, 
        freq='D',
        tp_stop=tp,   # 15% 익절
        sl_stop=sl,   # 7% 손절
        stop_entry_price='price' # 진입 가격 기준으로 스탑 계산
    )

    # 5. 결과 출력
    print(f"\n" + "="*85)
    print(f" Ticker: {ticker} | 리스크 관리 추가 (익절 {tp*100}%, 손절 {sl*100}%)")
    print("="*85)
    
    for col in pf.wrapper.columns:
        s = pf[col].stats()
        print(f"\n[ 전략: {col} ]")
        print(f"  - 총 수익률 (Total Return)   : {s.get('Total Return [%]', 0):>10.2f}%")
        print(f"  - 최대 낙폭 (Max Drawdown)   : {s.get('Max Drawdown [%]', 0):>10.2f}%")
        print(f"  - 승률 (Win Rate)            : {s.get('Win Rate [%]', 0):>10.2f}%")
        print(f"  - 매매 횟수 (Total Trades)   : {int(s.get('Total Trades', 0)):>10}회")
        print(f"  - 기대 수익 (Expectancy)     : {s.get('Expectancy', 0):>10.2f}")
    
    return pf

if __name__ == "__main__":
    run_mfi_with_stops("005930")