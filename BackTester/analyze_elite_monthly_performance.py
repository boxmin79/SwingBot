import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

def analyze_elite_monthly_performance(csv_path, detail_dir):
    # 1. 엘리트 종목 리스트 불러오기 (샤프 0.7 이상)
    elite_df = pd.read_csv(csv_path)
    # 티커를 6자리 문자열로 변환 (예: 210 -> 000210)
    elite_tickers = elite_df['ticker'].astype(str).str.zfill(6).tolist()
    
    all_trades = []
    
    print(f"총 {len(elite_tickers)}개 엘리트 종목의 상세 데이터 분석 중...")
    
    # 2. 각 종목의 상세 매매 데이터 로드
    for ticker in elite_tickers:
        file_path = Path(detail_dir) / f"{ticker}.parquet"
        if file_path.exists():
            df = pd.read_parquet(file_path)
            # 분석에 필요한 컬럼만 추출 (청산 시점과 수익률)
            df = df[['Exit Timestamp', 'Return']].copy()
            df['ticker'] = ticker
            all_trades.append(df)
    
    if not all_trades:
        print("상세 데이터를 찾을 수 없습니다.")
        return
    
    # 3. 모든 매매 데이터 통합 및 시간축 설정
    full_df = pd.concat(all_trades)
    full_df['Exit Timestamp'] = pd.to_datetime(full_df['Exit Timestamp'])
    full_df['Year'] = full_df['Exit Timestamp'].dt.year
    full_df['Month'] = full_df['Exit Timestamp'].dt.month
    
    # 4. 월별 평균 수익률 계산
    # 종목들이 동시에 매매될 수 있으므로, 월별로 각 종목의 수익률 합계를 구한 뒤 평균을 냅니다.
    monthly_grouped = full_df.groupby(['Year', 'Month', 'ticker'])['Return'].sum().reset_index()
    monthly_avg = monthly_grouped.groupby(['Year', 'Month'])['Return'].mean() * 100
    
    # 히트맵을 위한 피벗 테이블
    pivot_table = monthly_avg.unstack(fill_value=0)
    
    # 5. 시각화 (히트맵)
    plt.figure(figsize=(15, 10))
    sns.heatmap(pivot_table, annot=True, fmt=".1f", cmap="RdYlGn", center=0)
    plt.title("Elite Portfolio (Sharpe >= 0.7) Monthly Average Returns [%]", fontsize=16)
    plt.xlabel("Month")
    plt.ylabel("Year")
    plt.tight_layout()
    plt.savefig('elite_monthly_heatmap.png')
    
    # 6. 연도별 요약
    yearly_avg = monthly_avg.groupby(level=0).sum()
    print("\n--- 엘리트 포트폴리오 연도별 누적 수익률 요약 ---")
    print(yearly_avg)
    
    return pivot_table

# 실행 환경에 맞춰 경로를 설정하세요.
csv_file = 'elite_tickers_sharpe_07.csv'
detail_path = 'data/backtest/bollingerband/detail/'
result_pivot = analyze_elite_monthly_performance(csv_file, detail_path)