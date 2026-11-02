# 11. ASVI Dividend Attention

## Summary

네이버 데이터랩의 배당 관련 검색량(`배당`, `배당금`)으로 ASVI(Abnormal Search Volume Index)를 만들고, 한국 고배당 포트폴리오의 수익률 예측력과 개인 순매수 수급 관계를 검증한 연구 프로젝트입니다. 2인 공저 논문 초안(서강대 경제학과, 2025-12)이 기준이며 이 저장소에는 논문 PDF와 원천 데이터는 포함하지 않습니다.

## Research Question

배당 검색 관심도가 높아지는 시점에 개인 투자자 수급과 고배당주 수익률은 어떻게 달라지는가?

## Data And Signal

| Item | Description |
|---|---|
| Search data | Naver DataLab 월별 SVI, 2016-02 ~ 2025-12 |
| Equity data | DataGuide 수정주가, DPS (KOSPI, KOSDAQ), Carhart 4요인, VKOSPI, term spread |
| Investor flow | 개인/외국인/기관 순매수 (시가총액 대비 강도) |
| Main signal | `ASVI` = ln(SVI_t) - ln(SVI_t-1), 월 더미 회귀 잔차로 계절성 제거 |

## Headline Results (논문 초안 기준, 전체 표본 in-sample 회귀)

| Result | Value | 구분 |
|---|---|---|
| ASVI 1개월 후 고배당 L/S 비정상수익률 예측 (h=1) | beta -0.0401, t=-2.66, N=118 | in-sample 예측회귀, 다른 horizon(h=0,2~6)은 비유의 |
| ASVI와 개인 순매수 강도 | +0.4525 (t=1.75, 10% 유의), 외국인 -0.3850 (t=-1.90) | in-sample 회귀 |
| ASVI 타이밍 전략 (ASVI<=0이면 고배당, 아니면 CD91) | 연 5.61%, 변동성 5.01%, Sharpe 1.121, MDD -5.3% (82개월) | 요인 헤지 후, 비용 미반영(gross), 신호 방향은 같은 표본의 회귀 결과에서 정함 |
| 비교: 고배당 포트폴리오 / 요인 헤지 포트폴리오 | Sharpe 0.603 / 0.658 | 동일 82개월, gross |

해석: 배당 검색량 증가는 지속되는 정보 효과가 아니라 개인 매수에 따른 단기 수요 충격이며, 1개월 후 반전으로 이어진다는 결과입니다. 타이밍 전략의 Sharpe 개선은 방향 선택과 평가가 같은 기간이라 과대평가되었을 수 있고, 표본 밖(out-of-sample) 검증은 수행하지 않았습니다. 포트폴리오 수준 분석이며 거래비용을 반영하지 않았습니다.

## Methodology

1. 배당 관련 검색량 변화율(ASVI) 계산, 월 더미 회귀로 계절성 제거
2. 연 1회(6월 말) 배당수익률 5분위 포트폴리오 구성, Carhart 4요인 60개월 rolling 회귀로 비정상수익률 산출
3. h개월 후 비정상수익률에 대한 예측회귀
4. 개인/외국인/기관 순매수 강도와 ASVI 관계 분석
5. ASVI 기반 타이밍 전략과 요인 헤지 성과 비교

추가 확장(노트북 `01`): 종목별 배당 관심도 베타 `beta_divatt`와 `beta_mkt`로 5x5 포트폴리오를 만들고 Fama-MacBeth로 위험가격을 보는 분석입니다. 이 확장 분석의 결과 수치는 공개하지 않았습니다.

## Project Artifacts (이 폴더에 포함된 파일)

| File | Role |
|---|---|
| `notebooks/00_public_sample_workflow.ipynb` | 합성 검색량 샘플 workflow (실행 결과 저장) |
| `notebooks/01_beta_div_daily_report_sanitized.ipynb` | beta_divatt 5x5 / Fama-MacBeth 보고 노트북, 참고용 사본 |
| `notebooks/02_svi_construction_sanitized.ipynb` | SVI/ASVI 구성 노트북, 참고용 사본 |
| `notebooks/03_portfolio_analysis_sanitized.ipynb` | 배당 포트폴리오, 비정상수익률, 헤지 노트북, 참고용 사본 |
| `input_sample/` | 합성 검색량, 배당 panel |
| `output_sample/sample_regression_summary.csv` | 합성 회귀표 형식 예시 (실제 결과 아님) |

참고용 사본은 비공개 데이터가 있어야 실행됩니다.

## Trading Relevance

테마 검색량과 관심도 급증이 개인 수급과 단기 반전으로 이어지는 경로를 다루므로, 관심도 기반 과열 신호나 이벤트 전략의 사고방식과 연결됩니다.

## 원본에서 공개하지 않은 것

원본 xlsx/csv 데이터, 논문 PDF/초안, DataGuide 등 유료 데이터에서 파생된 원자료.
