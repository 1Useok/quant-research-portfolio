# News Text Strategy Evidence

원 연구 결과를 표로 옮긴 것이다. 표본외·비용 구분은 [상위 README](../README.md) 참고. 임베딩 포트폴리오는 OOS 228개월 월별 롱숏의 비용 전 값, 용량 모형 R2는 20일 기준선 대비 개선도(OOS 2019~2025, 70,952건), 수급 채널과 발표 전 상승은 일별 Fama-MacBeth 계수다.

## Embedding Portfolio Results

| Model | Key Result |
|---|---:|
| `e5_body200` + `ff6_residual_embedding_msrr` Sharpe | 1.7007 |
| `e5_body200` + `ff6_residual_embedding_msrr` annualized excess return | 2.2458 |
| `e5_body200` + `ff6_residual_embedding_msrr` annualized vol | 1.3205 |
| `e5_body200` + `ff6_residual_embedding_msrr` t-stat | 7.4133 |
| `kure_body200` + `ff6_residual_embedding_msrr` Sharpe | 1.9996 |

## Capacity Model Results

| Model | OOS R2 | Log RMSE |
|---|---:|---:|
| HGB mean | 0.2076 | 1.1220 |
| Ridge | 0.1077 | not listed |
| HGB q30 | 0.1214 | not listed |

Event sample after merging auction, price, and market-cap data: 94,230 events.

## Investor Activity Channel

| Channel | Coef | t-stat |
|---|---:|---:|
| Individual activity share | 1.169 | 35.53 |
| Individual buy / trading value | 0.988 | 25.56 |
| Individual sell / trading value | 1.350 | 34.66 |
| Individual buy-sell imbalance | -0.0039 | -8.65 |
| Institution activity share | -0.464 | -19.13 |
| Foreign activity share | -0.641 | -28.99 |

## Pre-Runup Findings

| Finding | Result |
|---|---:|
| `NB_score_z` predicting t-5 to t-1 return | 79.38bp, t=35.00 |
| Q1 pre-news return / event-day return | -0.12% / -0.32% |
| Q5 pre-news return / event-day return | 2.47% / 1.82% |

