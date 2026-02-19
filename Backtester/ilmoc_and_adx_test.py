import os
import pandas as pd
import vectorbt as vbt
import talib
from pathlib import Path

def run_ichimoku_adx_backtest(ticker):
    # 1. 데이터 로드
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent 
    data_dir = project_root / 'data' / 'chart'
    
    files = list(data_dir.glob(f"*{ticker}*.parquet"))
    if not files: return None
    df = pd.read_parquet(files[0])
    
    high, low, close = df['High'], df['Low'], df['Close']

    # 2. 지표 계산 (TA-Lib 및 직접 계산)
    # ADX: 추세의 강도 (25 이상이면 강한 추세)
    adx = talib.ADX(high, low, close, timeperiod=14)
    
    # 일목균형표 구성 요소
    # 전환선 (Tenkan-sen): (9일간 최고가 + 9일간 최저가) / 2
    # 기준선 (Kijun-sen): (26일간 최고가 + 26일간 최저가) / 2
    nine_high = high.rolling(window=9).max()
    nine_low = low.rolling(window=9).min()
    tenkan_sen = (nine_high + nine_low) / 2

    twenty_six_high = high.rolling(window=26).max()
    twenty_six_low = low.rolling(window=26).min()
    kijun_sen = (twenty_six_high + twenty_six_low) / 2

    # 선행스팬 A/B (구름대)
    senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(26)
    fifty_two_high = high.rolling(window=52).max()
    fifty_two_low = low.rolling(window=52).min()
    senkou_span_b = ((fifty_two_high + fifty_two_low) / 2).shift(26)

    # 3. 전략 신호 생성
    # 전략 1: 구름대 돌파 (Cloud Breakout)
    # 종가가 구름대(Span A, B) 위에 있고, ADX가 25 이상으로 추세가 강할 때만 진입
    cloud_top = pd.concat([senkou_span_a, senkou_span_b], axis=1).max(axis=1)
    cloud_bottom = pd.concat([senkou_span_a, senkou_span_b], axis=1).min(axis=1)
    
    ichimoku_entries = (close.vbt.crossed_above(cloud_top)) & (adx > 25)
    ichimoku_exits = close.vbt.crossed_below(kijun_sen) # 기준선 이탈 시 매도

    # 전략 2: 전환선/기준선 골든크로스 + ADX 필터
    cross_entries = (tenkan_sen.vbt.crossed_above(kijun_sen)) & (close > cloud_top) & (adx > 20)
    cross_exits = tenkan_sen.vbt.crossed_below(kijun_sen)

    # 4. 백테스트 실행
    strat_names = ['Cloud_Breakout', 'TK_Cross']
    entries = pd.concat([ichimoku_entries, cross_entries], axis=1, keys=strat_names)
    exits = pd.concat([ichimoku_exits, cross_exits], axis=1, keys=strat_names)

    pf = vbt.Portfolio.from_signals(
        close, entries, exits, 
        init_cash=10_000_000, fees=0.002, slippage=0.0005, freq='D'
    )

    # 5. 결과 출력
    print(f"\n" + "="*85)
    print(f" Ticker: {ticker} | 일목균형표 + ADX 필터 리포트")
    print("="*85)
    
    for col in pf.wrapper.columns:
        s = pf[col].stats()
        print(f"\n[ 전략: {col} ]")
        print(f"  - 총 수익률 (Total Return)   : {s.get('Total Return [%]', 0):>10.2f}%")
        print(f"  - 최대 낙폭 (Max Drawdown)   : {s.get('Max Drawdown [%]', 0):>10.2f}%")
        print(f"  - 승률 (Win Rate)            : {s.get('Win Rate [%]', 0):>10.2f}%")
        print(f"  - 매매 횟수 (Total Trades)   : {int(s.get('Total Trades', 0)):>10}회")
    
    return pf

if __name__ == "__main__":
    run_ichimoku_adx_backtest("005930")