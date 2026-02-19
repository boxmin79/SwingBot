import os
import pandas as pd
import vectorbt as vbt
from pathlib import Path

class BollingerTrendSlopeBacktester:
    def __init__(self, ticker, start_date=None, end_date=None, window=20, std_dev=2, slope_window=3):
        self.ticker = ticker
        self.window = window
        self.std_dev = std_dev
        self.slope_window = slope_window
        
        # 테스트 기간 설정 (None이면 전체 기간)
        self.start_date = start_date
        self.end_date = end_date
        
        self.project_root = Path(".") 
        self.data_dir = self.project_root / 'data' / 'chart'
        self.detail_log_dir = self.project_root / 'data' / 'backtest' / 'bollingerband' / 'detail'
        os.makedirs(self.detail_log_dir, exist_ok=True)
        
        self.data = self._load_data()
        self.pf = None

    def _load_data(self):
        files = list(self.data_dir.glob(f"*{self.ticker}*.parquet"))
        if not files:
            return None
        
        df = pd.read_parquet(files[0])
        
        # 인덱스가 Datetime 형식이 아닐 경우를 대비해 변환
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
            
        # 기간 필터링 로직 추가
        if self.start_date:
            df = df[df.index >= pd.to_datetime(self.start_date)]
        if self.end_date:
            df = df[df.index <= pd.to_datetime(self.end_date)]
            
        return df

    def run(self):
        # 데이터가 충분하지 않으면 중단
        if self.data is None or len(self.data) < self.window + self.slope_window:
            print(f"[{self.ticker}] 데이터 부족으로 테스트를 건너뜁니다.")
            return None

        close = self.data['Close']
        bbands = vbt.BBANDS.run(close, window=self.window, alpha=self.std_dev)
        sma = bbands.middle
        
        # 기울기 조건
        is_slope_up = sma > sma.shift(self.slope_window)

        # 전략 신호
        entries = close.vbt.crossed_above(bbands.upper) & is_slope_up
        exits = close.vbt.crossed_below(bbands.middle)

        self.pf = vbt.Portfolio.from_signals(            
            close, 
            entries, 
            exits,             
            init_cash=10_000_000,             
            fees=0.002, 
            slippage=0.0005, 
            freq='D',
            sl_stop=0.05        
        )
        
        trade_history = self.pf.trades.records_readable
        if not trade_history.empty:
            trade_history.to_parquet(self.detail_log_dir / f"{self.ticker}.parquet", index=False)
            
        return self.pf.stats().to_dict()

if __name__ == "__main__":
    # --- 사용 예시 ---
    # 최근 1년 데이터만 테스트하고 싶을 때
    backtester = BollingerTrendSlopeBacktester(
        ticker="005930", 
        start_date="2025-02-19", 
        end_date="2026-02-19"
    )
    stats = backtester.run()
    if stats:
        print(f"삼성전자 최근 1년 수익률: {stats['Total Return [%]']:.2f}%")