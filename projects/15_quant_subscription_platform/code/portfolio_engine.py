"""
포트폴리오 계산 엔진 (공개용 정리본)

구독 플랫폼 백엔드에서 쓰던 계산 로직을 pandas/numpy만으로 돌아가도록 정리한 사본입니다.
원본에서 제거한 것: parquet/DB/네트워크 접근, 운영 데이터 경로, API 서버 연동.
입력은 `input_sample/`의 합성 CSV(가격 + 전략 점수)이며, `python portfolio_engine.py`로 실행됩니다.

- NAV 계산
- 성과지표 산출 (CAGR, MDD, Sharpe, 변동성, 기간별 수익률)
- 환급 시뮬레이션 (손실 기간 판정; 상품 로직 예시이며 실제 환급 약속이 아님)
- 벤치마크 비교 (선택)

사용자 파라미터:
- n_stocks: 종목 수
- strategy: 전략 이름 (표시용)
- size_decile_min/max: 시가총액 분위수 범위
- rebalance_day: 리밸런싱 기준일
- position: 롱(1)/숏(-1)/롱숏(0)
- refund_period: 환급 판단 기간 ('monthly', 'quarterly', 'yearly')
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import json

# ==========================================
# 데이터 로드
# ==========================================

def build_panel(prices: pd.DataFrame, scores: pd.DataFrame) -> pd.DataFrame:
    """
    long 형식 가격(date, ticker, close)과 전략 점수(date, ticker, strategy_score, size_decile)를
    엔진 입력 패널(Date, Ticker, daily_ret, strategy_score, Size Decile)로 변환한다.
    점수는 발표일 이후 다음 점수가 나올 때까지 종목별로 forward-fill (미래 정보 사용 없음).
    """
    px = prices.rename(columns={'date': 'Date', 'ticker': 'Ticker'}).copy()
    px['Date'] = pd.to_datetime(px['Date'])
    px = px.sort_values(['Ticker', 'Date'])
    px['daily_ret'] = px.groupby('Ticker')['close'].pct_change()

    sc = scores.rename(columns={'date': 'Date', 'ticker': 'Ticker', 'size_decile': 'Size Decile'}).copy()
    sc['Date'] = pd.to_datetime(sc['Date'])

    panel = px.merge(sc, on=['Date', 'Ticker'], how='left').sort_values(['Ticker', 'Date'])
    panel[['strategy_score', 'Size Decile']] = panel.groupby('Ticker')[['strategy_score', 'Size Decile']].ffill()
    return panel.sort_values(['Date', 'Ticker']).reset_index(drop=True)


def load_sample_panel(sample_dir: Optional[str] = None) -> pd.DataFrame:
    """`input_sample/`의 합성 CSV로 패널을 만든다."""
    base = Path(sample_dir) if sample_dir else Path(__file__).resolve().parent.parent / 'input_sample'
    prices = pd.read_csv(base / 'sample_prices.csv')
    scores = pd.read_csv(base / 'sample_strategy_scores.csv')
    return build_panel(prices, scores)


def load_benchmark(csv_path: str) -> pd.Series:
    """벤치마크 일간 수익률 CSV(첫 열 날짜, 두 번째 열 수익률) 로드. 선택 사항."""
    bench = pd.read_csv(csv_path, index_col=0, parse_dates=True)
    bench.index.name = 'Date'
    bench_ret = bench.iloc[:, 0]
    bench_ret.name = 'benchmark_ret'
    return bench_ret


# ==========================================
# 리밸런싱 날짜 계산 
# ==========================================

def get_rebalance_dates(df: pd.DataFrame, rebalance_day: int) -> List[pd.Timestamp]:
    """
    각 월별로 리밸런싱 날짜를 찾는 함수
    rebalance_day에 가장 가까운 날짜를 선택 (해당 월에 그 날짜가 없으면 월말)
    """
    df = df.copy()
    df['Date'] = pd.to_datetime(df['Date'])
    df['year_month'] = df['Date'].dt.to_period('M')
    df['day'] = df['Date'].dt.day

    rebalance_dates = []
    
    for ym in df['year_month'].unique():
        month_data = df[df['year_month'] == ym]
        month_days = month_data['day'].unique()
        
        # rebalance_day와 같거나 큰 날짜 중 가장 작은 것
        valid_days = month_days[month_days >= rebalance_day]
        if len(valid_days) > 0:
            selected_day = valid_days.min()
        else:
            # rebalance_day보다 작으면 그 달의 마지막 날
            selected_day = month_days.max()
        
        selected_date = month_data[month_data['day'] == selected_day]['Date'].iloc[0]
        rebalance_dates.append(selected_date)
    
    return sorted(rebalance_dates)


# ==========================================
# 포트폴리오 일간 수익률 계산 
# ==========================================

def calculate_daily_portfolio_returns_optimized(
    df: pd.DataFrame, 
    rebalance_dates: List[pd.Timestamp], 
    strategy_col: str, 
    n_stocks: int, 
    position: int,
    size_decile_min: Optional[int] = None,
    size_decile_max: Optional[int] = None
) -> pd.Series:
    """
    포트폴리오 일별 수익률 계산 (성능 최적화)
    
    Parameters:
    - df: 데이터프레임
    - rebalance_dates: 리밸런싱 날짜 목록
    - strategy_col: 전략 컬럼명
    - n_stocks: 종목 수
    - position: 1(롱), -1(숏), 0(롱숏)
    - size_decile_min/max: 시가총액 분위수 필터
    
    Returns:
    - 일별 수익률 Series
    """
    # 전체 데이터에 대해 pivot을 미리 수행
    daily_ret_pivot = df.pivot_table(
        index='Date', columns='Ticker', values='daily_ret', aggfunc='first'
    )
    
    all_daily_returns = []
    
    for i in range(len(rebalance_dates)):
        rebal_date = rebalance_dates[i]
        
        # 다음 리밸런싱 날짜
        if i < len(rebalance_dates) - 1:
            next_rebal_date = rebalance_dates[i + 1]
        else:
            next_rebal_date = df['Date'].max()
        
        # 리밸런싱일에 종목 선정
        rebal_data = df[df['Date'] == rebal_date]
        
        # Size Decile 범위 필터링
        if size_decile_min is not None and size_decile_max is not None and 'Size Decile' in rebal_data.columns:
            rebal_data = rebal_data[
                (rebal_data['Size Decile'] >= size_decile_min) & 
                (rebal_data['Size Decile'] <= size_decile_max)
            ]
        
        # 결측치 제거
        rebal_data = rebal_data.dropna(subset=[strategy_col])
        
        if len(rebal_data) == 0:
            continue
        
        # Position에 따른 종목 선정
        if position == 1:
            selected_tickers = rebal_data.nlargest(n_stocks, strategy_col)['Ticker'].tolist()
        elif position == -1:
            selected_tickers = rebal_data.nsmallest(n_stocks, strategy_col)['Ticker'].tolist()
        elif position == 0:
            long_tickers = rebal_data.nlargest(n_stocks, strategy_col)['Ticker'].tolist()
            short_tickers = rebal_data.nsmallest(n_stocks, strategy_col)['Ticker'].tolist()
        
        # 보유 기간 데이터
        period_data = daily_ret_pivot.loc[
            (daily_ret_pivot.index >= rebal_date) & 
            (daily_ret_pivot.index <= next_rebal_date)
        ]
        
        if len(period_data) == 0:
            continue
        
        # Position에 따른 일별 수익률 계산
        if position == 0:  # Long-Short
            long_pivot = period_data[long_tickers].fillna(0)
            short_pivot = period_data[short_tickers].fillna(0)
            
            # 올바른 방법: 일별 수익률의 평균을 직접 계산
            # 롱 포트폴리오: 일별 수익률의 동일가중 평균
            long_daily_returns = long_pivot.mean(axis=1)
            # 숏 포트폴리오: 일별 수익률의 동일가중 평균 (부호 반전)
            short_daily_returns = short_pivot.mean(axis=1)
            
            # 롱숏 = 롱 수익률 - 숏 수익률 (숏은 하락시 수익)
            period_returns = long_daily_returns - short_daily_returns
            # 첫날 제거 (리밸런싱일)
            period_returns = period_returns.iloc[1:]
        else:
            if position == 1:
                selected_pivot = period_data[selected_tickers].fillna(0)
                period_returns = ((selected_pivot + 1).cumprod().mean(axis=1)).pct_change().dropna()
            else:  # position == -1
                selected_pivot = period_data[selected_tickers].fillna(0)
                period_returns = -((selected_pivot + 1).cumprod().mean(axis=1)).pct_change().dropna()
        
        all_daily_returns.append(period_returns)
    
    # 모든 기간의 일별 수익률 합치기
    if len(all_daily_returns) > 0:
        daily_returns = pd.concat(all_daily_returns).sort_index()
        daily_returns.name = 'daily_return'
        return daily_returns
    else:
        return pd.Series(name='daily_return')


# ==========================================
# NAV 계산
# ==========================================

def calculate_nav(
    daily_returns: pd.Series, 
    start_nav: float = 1000.0
) -> pd.DataFrame:
    """
    일간 수익률로부터 NAV 히스토리 계산
    
    Returns:
    - DataFrame with columns: date, nav_value, daily_return, cumulative_return, drawdown
    """
    if daily_returns.empty:
        return pd.DataFrame()
    
    # 누적 수익률 계산
    cumulative_factor = (1 + daily_returns).cumprod()
    nav_values = start_nav * cumulative_factor
    
    # NAV DataFrame 생성
    nav_df = pd.DataFrame({
        'date': daily_returns.index,
        'nav_value': nav_values.values,
        'daily_return': (daily_returns * 100).values,  # 퍼센트로 변환
    })
    nav_df['date'] = pd.to_datetime(nav_df['date'])
    
    # 누적 수익률 (시작점 대비)
    nav_df['cumulative_return'] = ((nav_df['nav_value'] / start_nav) - 1) * 100
    
    # Drawdown 계산
    rolling_max = nav_df['nav_value'].cummax()
    nav_df['drawdown'] = ((nav_df['nav_value'] - rolling_max) / rolling_max) * 100
    
    return nav_df


def calculate_benchmark_nav(
    kospi_ret: pd.Series,
    date_range: Tuple[pd.Timestamp, pd.Timestamp],
    start_nav: float = 1000.0
) -> pd.DataFrame:
    """벤치마크 NAV 계산"""
    start_date, end_date = date_range
    
    # 날짜 범위 필터링
    mask = (kospi_ret.index >= start_date) & (kospi_ret.index <= end_date)
    filtered_ret = kospi_ret[mask]
    
    if filtered_ret.empty:
        return pd.DataFrame()
    
    # NAV 계산
    cumulative_factor = (1 + filtered_ret).cumprod()
    nav_values = start_nav * cumulative_factor
    
    # DataFrame 생성
    bench_df = pd.DataFrame({
        'date': filtered_ret.index,
        'benchmark_nav': nav_values.values,
        'benchmark_daily_return': (filtered_ret * 100).values,
    })
    bench_df['date'] = pd.to_datetime(bench_df['date'])
    
    # 누적 수익률
    bench_df['benchmark_cumulative_return'] = ((bench_df['benchmark_nav'] / start_nav) - 1) * 100
    
    # Drawdown
    rolling_max = bench_df['benchmark_nav'].cummax()
    bench_df['benchmark_drawdown'] = ((bench_df['benchmark_nav'] - rolling_max) / rolling_max) * 100
    
    return bench_df


# ==========================================
# 성과 지표 계산
# ==========================================

def calculate_performance_metrics(
    nav_df: pd.DataFrame,
    trading_days_per_year: int = 252,
    risk_free_rate: float = 0.035
) -> Dict[str, float]:
    """
    성과 지표 계산
    
    Returns:
    - monthlyReturn: 당월 수익률
    - monthlyAvgReturn: 월 평균 수익률 (복리 환산)
    - yearlyAvgReturn: 연 평균 수익률 (CAGR)
    - cumulativeReturn: 누적 수익률
    - maxDrawdown: 최대 낙폭 (MDD)
    - sharpeRatio: 샤프 비율
    - volatility: 연환산 변동성
    """
    if nav_df.empty or len(nav_df) < 2:
        return {
            'monthlyReturn': 0.0,
            'monthlyAvgReturn': 0.0,
            'yearlyAvgReturn': 0.0,
            'cumulativeReturn': 0.0,
            'maxDrawdown': 0.0,
            'sharpeRatio': 0.0,
            'volatility': 0.0,
        }
    
    first_nav = nav_df['nav_value'].iloc[0]
    latest_nav = nav_df['nav_value'].iloc[-1]
    
    # 1. 당월 수익률 (최근 22영업일)
    month_ago_idx = max(0, len(nav_df) - 22)
    month_ago_nav = nav_df['nav_value'].iloc[month_ago_idx]
    monthly_return = ((latest_nav - month_ago_nav) / month_ago_nav) * 100
    
    # 2. 기간 계산
    first_date = pd.to_datetime(nav_df['date'].iloc[0])
    last_date = pd.to_datetime(nav_df['date'].iloc[-1])
    total_days = (last_date - first_date).days
    total_years = max(total_days / 365, 0.01)
    total_months = total_years * 12
    
    # 3. 누적 수익률
    cumulative_return = ((latest_nav - first_nav) / first_nav) * 100
    
    # 4. CAGR (연평균 수익률)
    total_return_factor = latest_nav / first_nav
    cagr = (pow(total_return_factor, 1 / total_years) - 1) * 100
    
    # 5. 월 평균 수익률 (복리 환산)
    monthly_avg_return = (pow(total_return_factor, 1 / total_months) - 1) * 100
    
    # 6. MDD (최대 낙폭)
    max_drawdown = nav_df['drawdown'].min()
    
    # 7. 샤프 비율
    daily_returns = nav_df['daily_return'] / 100  # 퍼센트를 소수로 변환
    daily_std = daily_returns.std()
    annualized_volatility = daily_std * np.sqrt(trading_days_per_year) * 100
    
    if annualized_volatility > 0:
        sharpe_ratio = (cagr / 100 - risk_free_rate) / (annualized_volatility / 100)
    else:
        sharpe_ratio = 0.0
    
    return {
        'monthlyReturn': round(monthly_return, 2),
        'monthlyAvgReturn': round(monthly_avg_return, 2),
        'yearlyAvgReturn': round(cagr, 2),
        'cumulativeReturn': round(cumulative_return, 2),
        'maxDrawdown': round(max_drawdown, 2),
        'sharpeRatio': round(sharpe_ratio, 2),
        'volatility': round(annualized_volatility, 2),
    }


def calculate_period_returns(
    nav_df: pd.DataFrame
) -> List[Dict[str, Any]]:
    """기간별 수익률 계산 (3개월, 6개월, 1년, 2년, 5년)"""
    if nav_df.empty:
        return [{'period': p, 'value': 0.0} for p in ['3개월', '6개월', '1년', '2년', '5년']]
    
    latest_nav = nav_df['nav_value'].iloc[-1]
    latest_date = pd.to_datetime(nav_df['date'].iloc[-1])
    
    periods = [
        ('3개월', 66),
        ('6개월', 132),
        ('1년', 252),
        ('2년', 504),
        ('5년', 1260),
    ]
    
    results = []
    for label, days in periods:
        start_idx = max(0, len(nav_df) - days)
        start_nav = nav_df['nav_value'].iloc[start_idx]
        return_pct = ((latest_nav - start_nav) / start_nav) * 100
        results.append({
            'period': label,
            'value': round(return_pct, 2)
        })
    
    return results


# ==========================================
# 환급 시뮬레이션
# ==========================================

def calculate_refund_simulation(
    nav_df: pd.DataFrame,
    rebalance_dates: List[pd.Timestamp],
    refund_period: str = 'quarterly'
) -> List[Dict[str, Any]]:
    """
    환급 시뮬레이션 계산
    
    Parameters:
    - nav_df: NAV 데이터프레임
    - rebalance_dates: 리밸런싱 날짜 목록
    - refund_period: 환급 판단 기간 ('monthly', 'quarterly', 'yearly')
    
    Returns:
    - 환급 시뮬레이션 결과 리스트
    """
    if nav_df.empty or len(rebalance_dates) < 2:
        return []
    
    nav_df = nav_df.copy()
    nav_df['date'] = pd.to_datetime(nav_df['date'])
    nav_df = nav_df.set_index('date')
    
    # 환급 판단 주기 설정
    period_months = {
        'monthly': 1,
        'quarterly': 3,
        'yearly': 12
    }
    interval = period_months.get(refund_period, 3)
    
    refund_results = []
    
    # 리밸런싱 날짜를 환급 판단 기간으로 묶기
    i = 0
    while i < len(rebalance_dates) - interval:
        period_start = rebalance_dates[i]
        period_end_idx = min(i + interval, len(rebalance_dates) - 1)
        period_end = rebalance_dates[period_end_idx]
        
        # 해당 기간의 NAV 찾기
        try:
            # 시작일에 가장 가까운 NAV
            start_nav_row = nav_df[nav_df.index >= period_start].iloc[0] if len(nav_df[nav_df.index >= period_start]) > 0 else None
            # 종료일에 가장 가까운 NAV
            end_nav_row = nav_df[nav_df.index <= period_end].iloc[-1] if len(nav_df[nav_df.index <= period_end]) > 0 else None
            
            if start_nav_row is not None and end_nav_row is not None:
                start_nav = start_nav_row['nav_value']
                end_nav = end_nav_row['nav_value']
                return_rate = ((end_nav - start_nav) / start_nav) * 100
                
                refund_results.append({
                    'period': f"{period_start.strftime('%Y-%m-%d')} ~ {period_end.strftime('%Y-%m-%d')}",
                    'startDate': period_start.strftime('%Y-%m-%d'),
                    'endDate': period_end.strftime('%Y-%m-%d'),
                    'returnRate': round(return_rate, 2),
                    'isRefund': bool(return_rate < 0),  # 손실 시 환급, Python bool로 변환
                })
        except Exception as e:
            pass
        
        i += interval
    
    # 마지막 미완료 기간 추가 (최근 미완료 기)
    if len(rebalance_dates) > 0:
        last_complete_idx = (len(rebalance_dates) - 1) // interval * interval
        if last_complete_idx < len(rebalance_dates) - 1:
            period_start = rebalance_dates[last_complete_idx]
            period_end = rebalance_dates[-1]
            
            try:
                start_nav_row = nav_df[nav_df.index >= period_start].iloc[0] if len(nav_df[nav_df.index >= period_start]) > 0 else None
                end_nav_row = nav_df.iloc[-1]  # 마지막 NAV 사용
                
                if start_nav_row is not None:
                    start_nav = start_nav_row['nav_value']
                    end_nav = end_nav_row['nav_value']
                    return_rate = ((end_nav - start_nav) / start_nav) * 100
                    
                    refund_results.append({
                        'period': f"{period_start.strftime('%Y-%m-%d')} ~ {nav_df.index[-1].strftime('%Y-%m-%d')}",
                        'startDate': period_start.strftime('%Y-%m-%d'),
                        'endDate': nav_df.index[-1].strftime('%Y-%m-%d'),
                        'returnRate': round(return_rate, 2),
                        'isRefund': bool(return_rate < 0),  # Python bool로 변환
                        'isIncomplete': True,  # 미완료 기간 표시
                    })
            except Exception:
                pass
    
    return refund_results


def calculate_refund_probability(refund_results: List[Dict]) -> float:
    """환급 확률 계산 (환급되지 않을 확률 = 수익 기간 / 전체 기간)"""
    if not refund_results:
        return 0.0
    
    # 완료된 기간만 사용 (미완료 기간 제외)
    complete_periods = [r for r in refund_results if not r.get('isIncomplete', False)]
    
    if not complete_periods:
        return 0.0
    
    profitable_periods = sum(1 for r in complete_periods if not r['isRefund'])
    total_periods = len(complete_periods)
    
    # 환급되지 않을 확률 = 수익 기간 비율
    return round((profitable_periods / total_periods) * 100, 1)


# ==========================================
# 기간 필터링
# ==========================================

def filter_data_by_period(
    nav_df: pd.DataFrame,
    rebalance_dates: List[pd.Timestamp],
    n_months: int = 120,
    current_date: Optional[datetime] = None
) -> Tuple[pd.DataFrame, List[pd.Timestamp], pd.Timestamp]:
    """
    분석 기간에 맞게 데이터 필터링
    
    Parameters:
    - nav_df: NAV 데이터프레임
    - rebalance_dates: 전체 리밸런싱 날짜
    - n_months: 분석할 개월 수 (기본 120개월 = 10년)
    - current_date: 현재 날짜 (None이면 오늘)
    
    Returns:
    - 필터링된 NAV DataFrame
    - 필터링된 리밸런싱 날짜
    - 마지막 완료된 리밸런싱 날짜
    """
    if current_date is None:
        current_date = datetime.now()
    
    if isinstance(current_date, str):
        current_date = pd.to_datetime(current_date)
    
    # 마지막 완료된 리밸런싱 날짜 찾기 (현재 날짜 이전 중 가장 최근)
    past_rebalance_dates = [d for d in rebalance_dates if d <= current_date]
    if not past_rebalance_dates:
        return nav_df, rebalance_dates, rebalance_dates[-1] if rebalance_dates else current_date
    
    last_complete_date = past_rebalance_dates[-1]
    
    # 시작 날짜 계산 (n_months 전의 리밸런싱 날짜)
    start_idx = max(0, len(past_rebalance_dates) - n_months)
    start_date = past_rebalance_dates[start_idx]
    
    # 데이터 필터링
    nav_df = nav_df.copy()
    nav_df['date'] = pd.to_datetime(nav_df['date'])
    filtered_nav = nav_df[(nav_df['date'] >= start_date) & (nav_df['date'] <= current_date)]
    
    # 리밸런싱 날짜 필터링
    filtered_rebalance = [d for d in rebalance_dates if start_date <= d <= current_date]
    
    return filtered_nav, filtered_rebalance, last_complete_date


# ==========================================
# 메인 계산 함수
# ==========================================

def calculate_portfolio_data(
    n_stocks: int = 20,
    strategy: str = "demo",
    size_decile_min: int = 1,
    size_decile_max: int = 10,
    rebalance_day: int = 1,
    position: int = 1,
    refund_period: str = 'quarterly',
    n_months: int = 120,
    current_date: Optional[str] = None,
    panel: Optional[pd.DataFrame] = None,
    benchmark_ret: Optional[pd.Series] = None,
    strategy_col: str = "strategy_score",
) -> Dict[str, Any]:
    """
    포트폴리오 데이터 계산 메인 함수
    
    Parameters:
    - n_stocks: 종목 수
    - strategy: 전략 이름 (표시용)
    - size_decile_min/max: 시가총액 분위수 범위
    - rebalance_day: 리밸런싱 기준일
    - position: 롱(1)/숏(-1)/롱숏(0)
    - refund_period: 환급 판단 기간
    - n_months: 분석 개월 수
    - current_date: 현재 날짜 (YYYY-MM-DD 형식)
    - panel: build_panel() 결과 (None이면 input_sample의 합성 데이터)
    - benchmark_ret: 벤치마크 일간 수익률 Series (None이면 벤치마크 생략)
    - strategy_col: 종목 선정에 쓰는 점수 컬럼
    
    Returns:
    - 프론트엔드용 데이터 딕셔너리
    """
    # 현재 날짜 설정
    if current_date is None:
        current_date = datetime.now()
    else:
        current_date = pd.to_datetime(current_date)
    
    # 데이터 로드 (파일/DB 접근 없음)
    df = panel if panel is not None else load_sample_panel()
    kospi_ret = benchmark_ret if benchmark_ret is not None else pd.Series(dtype=float)
    
    # 리밸런싱 날짜 계산
    all_rebalance_dates = get_rebalance_dates(df, rebalance_day)
    
    # 포트폴리오 일간 수익률 계산
    portfolio_daily = calculate_daily_portfolio_returns_optimized(
        df, 
        all_rebalance_dates, 
        strategy_col, 
        n_stocks, 
        position,
        size_decile_min=size_decile_min,
        size_decile_max=size_decile_max
    )
    
    # NAV 계산
    nav_df = calculate_nav(portfolio_daily, start_nav=1000.0)
    
    if nav_df.empty:
        return {"error": "No data available for the specified parameters"}
    
    # 기간 필터링 (최근 n_months 개월)
    nav_df, filtered_rebalance_dates, last_complete_date = filter_data_by_period(
        nav_df, all_rebalance_dates, n_months, current_date
    )
    
    # NAV 값을 시작점 기준으로 정규화 (필터링된 범위의 첫 번째 값 = 1000)
    if not nav_df.empty:
        first_nav = nav_df['nav_value'].iloc[0]
        nav_df['nav_value'] = (nav_df['nav_value'] / first_nav) * 1000
        nav_df['cumulative_return'] = ((nav_df['nav_value'] / 1000) - 1) * 100
        
        # Drawdown 재계산
        rolling_max = nav_df['nav_value'].cummax()
        nav_df['drawdown'] = ((nav_df['nav_value'] - rolling_max) / rolling_max) * 100
    
    # 벤치마크 NAV 계산
    date_range = (nav_df['date'].min(), nav_df['date'].max())
    if kospi_ret.empty:
        benchmark_df = pd.DataFrame()
    else:
        benchmark_df = calculate_benchmark_nav(kospi_ret, date_range, start_nav=1000.0)
    
    # NAV와 벤치마크 병합
    if not benchmark_df.empty:
        nav_df = nav_df.merge(
            benchmark_df[['date', 'benchmark_nav', 'benchmark_daily_return', 'benchmark_cumulative_return', 'benchmark_drawdown']],
            on='date',
            how='left'
        )
        nav_df['benchmark_nav'] = nav_df['benchmark_nav'].ffill()
        nav_df['benchmark_primary_value'] = nav_df['benchmark_nav']
    else:
        nav_df['benchmark_primary_value'] = 1000.0
        nav_df['benchmark_nav'] = 1000.0
    
    # 성과 지표 계산 (마지막 완료된 기간까지만)
    metrics_nav_df = nav_df[nav_df['date'] <= last_complete_date].copy()
    metrics = calculate_performance_metrics(metrics_nav_df)
    
    # 기간별 수익률
    period_returns = calculate_period_returns(metrics_nav_df)
    
    # 벤치마크 성과 지표
    if not benchmark_df.empty:
        bench_metrics_df = benchmark_df[benchmark_df['date'] <= last_complete_date].copy()
        bench_metrics_df = bench_metrics_df.rename(columns={
            'benchmark_nav': 'nav_value',
            'benchmark_daily_return': 'daily_return',
            'benchmark_drawdown': 'drawdown'
        })
        benchmark_metrics = calculate_performance_metrics(bench_metrics_df)
    else:
        benchmark_metrics = calculate_performance_metrics(pd.DataFrame())
    
    # 환급 시뮬레이션
    refund_simulation = calculate_refund_simulation(nav_df, filtered_rebalance_dates, refund_period)
    refund_probability = calculate_refund_probability(refund_simulation)
    
    # 차트 데이터 생성
    chart_data = []
    for _, row in nav_df.iterrows():
        chart_data.append({
            'date': row['date'].strftime('%Y-%m-%d'),
            'strategy': round(row['cumulative_return'], 2),
            'benchmark_primary': round(row.get('benchmark_cumulative_return', 0) or 0, 2),
            'benchmark_secondary': 0,  # 보조 벤치마크 (현재 미사용)
        })
    
    # NAV 히스토리 데이터
    nav_history = []
    for _, row in nav_df.iterrows():
        nav_history.append({
            'id': f"nav-{row['date'].strftime('%Y%m%d')}",
            'portfolio_id': f"portfolio-{strategy}",
            'date': row['date'].strftime('%Y-%m-%d'),
            'nav_value': round(row['nav_value'], 2),
            'daily_return': round(row['daily_return'], 2),
            'cumulative_return': round(row['cumulative_return'], 2),
            'benchmark_primary_value': round(row.get('benchmark_primary_value', 1000) or 1000, 2),
            'benchmark_secondary_value': None,
            'drawdown': round(row['drawdown'], 2),
            'created_at': datetime.now().isoformat(),
        })
    
    # 결과 반환
    return {
        'params': {
            'n_stocks': n_stocks,
            'strategy': strategy,
            'size_decile_min': size_decile_min,
            'size_decile_max': size_decile_max,
            'rebalance_day': rebalance_day,
            'position': position,
            'refund_period': refund_period,
        },
        'metrics': {
            **metrics,
            'periodReturns': period_returns,
            'benchmark': {
                'primary': benchmark_metrics,
                'secondary': benchmark_metrics,  # 보조 벤치마크도 동일하게
            },
            'refundProbability': refund_probability,
        },
        'navHistory': nav_history,
        'chartData': chart_data,
        'refundSimulation': refund_simulation,
        'lastCompleteDate': last_complete_date.strftime('%Y-%m-%d'),
        'analysisRange': {
            'start': nav_df['date'].min().strftime('%Y-%m-%d'),
            'end': nav_df['date'].max().strftime('%Y-%m-%d'),
        }
    }


def save_to_json(data: Dict, output_path: str = "portfolio_data.json"):
    """결과를 JSON 파일로 저장"""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Data saved to {output_path}")


# ==========================================
# CLI 실행: 합성 샘플로 엔진을 돌려본다
# ==========================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Portfolio engine demo on synthetic sample data')
    parser.add_argument('--n-stocks', type=int, default=2, help='Number of stocks per leg')
    parser.add_argument('--position', type=int, default=1, help='1=long, -1=short, 0=long-short')
    parser.add_argument('--refund-period', type=str, default='monthly', help='monthly|quarterly|yearly')
    parser.add_argument('--output', type=str, default=None, help='Optional output JSON path')
    args = parser.parse_args()

    result = calculate_portfolio_data(
        n_stocks=args.n_stocks,
        position=args.position,
        refund_period=args.refund_period,
        n_months=12,
        current_date='2025-06-30',
    )
    if 'error' in result:
        raise SystemExit(result['error'])
    summary = {k: float(v) for k, v in result['metrics'].items() if k not in ('periodReturns', 'benchmark')}
    print('analysisRange :', result['analysisRange'])
    print('metrics       :', summary)
    print('refund periods:', [(r['period'], float(r['returnRate']), bool(r['isRefund'])) for r in result['refundSimulation']])
    if args.output:
        save_to_json(result, args.output)
