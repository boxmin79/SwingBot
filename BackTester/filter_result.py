import pandas as pd
import numpy as np

def filter_backtest_results(input_file, output_file):
    """
    백테스팅 결과에서 최우량 종목(Elite Tickers)을 필터링하는 함수입니다.
    
    필터링 기준:
    1. 총 수익률 (Total Return) >= 195.6% (10년 코스피 지수 수익률)
    2. 샤프 지수 (Sharpe Ratio) >= 0.7 (리스크 대비 수익 효율성)
    3. 거래 횟수 (Total Trades) >= 10 (통계적 유의성 확보)
    """
    
    # 1. 데이터 로드
    print(f"데이터 로딩 중: {input_file}")
    df = pd.read_csv(input_file)
    
    # 2. 데이터 전처리
    # 거래가 한 번이라도 발생한 종목만 대상
    df_active = df[df['Total Trades'] > 0].copy()
    
    # 샤프 지수의 inf 값을 NaN으로 변환하고 숫자형으로 강제 변환
    df_active['Sharpe Ratio'] = pd.to_numeric(df_active['Sharpe Ratio'].replace([np.inf, -np.inf], np.nan), errors='coerce')
    
    # 3. 필터링 기준 설정
    market_benchmark = 112.5 # 1년 코스피 수익률 #195.6 10년치 코스피 수익률 근사치
    min_sharpe = 0.7
    min_trades = 10
    
    # 4. 필터 적용
    filtered_df = df_active[
        (df_active['Total Return [%]'] >= market_benchmark) &
        (df_active['Sharpe Ratio'] >= min_sharpe) # &
        # (df_active['Total Trades'] >= min_trades)
    ].copy()
    
    # 5. 결과 정렬 (수익률 높은 순)
    filtered_df = filtered_df.sort_values('Total Return [%]', ascending=False)
    
    # 6. 결과 저장
    filtered_df.to_csv(output_file, index=False)
    
    # 7. 요약 통계 출력
    print("\n" + "="*50)
    print(f" 필터링 완료: {len(filtered_df)}개 종목 선정")
    print("="*50)
    
    if not filtered_df.empty:
        print(f"평균 수익률: {filtered_df['Total Return [%]'].mean():.2f}%")
        print(f"평균 샤프지수: {filtered_df['Sharpe Ratio'].mean():.2f}")
        print(f"평균 MDD: {filtered_df['Max Drawdown [%]'].mean():.2f}%")
        print(f"평균 거래횟수: {filtered_df['Total Trades'].mean():.1f}회")
        print("-" * 50)
        print("상위 10개 종목 리스트:")
        print(filtered_df[['ticker', 'Total Return [%]', 'Sharpe Ratio', 'Max Drawdown [%]']].head(10))
    else:
        print("조건을 만족하는 종목이 없습니다.")
        
    return filtered_df

# 실행부
if __name__ == "__main__":
    # 파일명은 실제 파일명에 맞게 수정하여 사용하세요.
    input_filename = 'data/backtest/bollingerband/summary/slope_summary_from_20250219_20260219_182347.csv'
    output_filename = 'data/backtest/bollingerband/elite_tickers_sharpe_07.csv'
    
    elite_list = filter_backtest_results(input_filename, output_filename)