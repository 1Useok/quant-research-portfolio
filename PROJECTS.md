# Projects

번호는 [README](README.md)의 표와 같습니다. 실행 코드가 있는 프로젝트는 `code/`에서 데모와 테스트를 돌릴 수 있습니다.

## Trading Strategy Research

| No. | Project | 실행 코드 | Summary |
|---|---|---|---|
| 01 | [News Text Strategy](projects/01_news_text_strategy/README.md) | ✓ | 뉴스/공시 텍스트를 감성, 임베딩, 수급, 장중 가격 경로와 연결한 이벤트 전략 |
| 02 | [IOF Long-Short](projects/02_iof_longshort/README.md) | ✓ | 기관 순매도(IOF)와 시총 변화로 만든 롱숏, 익일 시가 체결과 비용·대차료 반영 장부 |
| 03 | [Cointegration Breakdown](projects/03_cointegration_breakdown/README.md) | ✓ | KOSPI200 공적분 쌍의 괴리 경보를 다중검정 보정과 비용 후 성과로 검증 |
| 04 | [JKP ML Long-Short](projects/04_jkp_ml_longshort/README.md) | ✓ | JKP 기업특성의 시점 정렬과 연도별 XGBoost 학습으로 월별 롱숏 구성 |
| 06 | [Factor Strategy Research](projects/06_factor_strategy_research/README.md) | 스크립트 | 대규모 팩터 풀에서 조합 전략을 탐색하고 상관·성과 기준으로 선별 |

## Portfolio Construction And Replication

| No. | Project | 실행 코드 | Summary |
|---|---|---|---|
| 05 | [JKP Portfolio-ML](projects/05_jkp_portfolio_ml/README.md) | ✓ | Jensen·Kelly·Malamud·Pedersen의 Portfolio-ML을 국내 주식에 적용, 비용 반영 학습과 구현 가능한 효율적 프런티어 |
| 07 | [Quant Model Replication](projects/07_quant_model_replication/README.md) | ✓ | 공개 퀀트 모델의 팩터 비중 대입과 자체 예측을 분리해 종목 일치율 검산 |

## Market Data Engineering

| No. | Project | 실행 코드 | Summary |
|---|---|---|---|
| 08 | [Market Data Registry](projects/08_market_data_registry/README.md) | ✓ | 날짜 없는 수급 파일의 거래일 확정, 증분 등록부, 중복·충돌 처리와 롤백 |
| 09 | [Market Data Operations: alba](projects/09_market_data_operations_alba/README.md) | | KRX/KIS 데이터를 Airflow로 자동 수집하고 품질 검증하는 팀 운영 시스템 |

## Risk And Anomaly Research

| No. | Project | 실행 코드 | Summary |
|---|---|---|---|
| 10 | [Industry Shock Wave](projects/10_industry_shock_wave/README.md) | | 산업연관표, 공급망, OpenDART로 테마/산업 충격을 기업 위험으로 구조화 |
| 11 | [ASVI Dividend Attention](projects/11_asvi_dividend_attention/README.md) | | 배당 검색량으로 투자자 관심도 신호를 만들고 고배당주 수익률과 수급을 검증 |
| 12 | [PER Anomaly](projects/12_per_anomaly/README.md) | | 회귀와 XGBoost로 적정 PER/PE를 추정하고 밸류에이션 괴리를 분석 |
| 13 | [Idiosyncratic Volatility In Korea](projects/13_ivol_korea_market/README.md) | | 한국 주식시장에서 idiosyncratic volatility 이상현상을 검증 |
| 14 | [CRASHP](projects/14_crashp_tail_risk/README.md) | | 급락/급등 확률과 꼬리위험 변수를 이용한 리스크/주식 선택 연구 |

## Product

| No. | Project | 실행 코드 | Summary |
|---|---|---|---|
| 15 | [Quant Subscription Platform](projects/15_quant_subscription_platform/README.md) | 스크립트 | 퀀트 전략 성과와 환급 구조를 시각화하는 구독형 웹 애플리케이션 |
