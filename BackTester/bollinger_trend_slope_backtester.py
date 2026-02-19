import os
import pandas as pd
import vectorbt as vbt
from pathlib import Path

class BollingerTrendSlopeBacktester:
    def __init__(self, ticker, window=20, std_dev=2, slope_window=3):
        self.ticker = ticker
        self.window = window
        self.std_dev = std_dev
        self.slope_window = slope_window
        
        # 프로젝트 루트 경로 설정
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
        return pd.read_parquet(files[0])

    def run(self):
        if self.data is None or len(self.data) < self.window + self.slope_window:
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
        
        # 매매 내역 저장
        trade_history = self.pf.trades.records_readable
        if not trade_history.empty:
            # 수정된 부분: self.pf.trades 대신 trade_history(DataFrame)를 사용하여 저장합니다.
            trade_history.to_parquet(self.detail_log_dir / f"{self.ticker}.parquet", index=False)
            
        return self.pf.stats().to_dict()