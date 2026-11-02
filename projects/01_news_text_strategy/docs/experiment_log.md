# Experiment Log

원 연구에서 시도한 실험과 결과를 요약한다. 수치의 표본 구분과 비용 반영 여부는 [상위 README](../README.md)에 있다.

| Experiment | Attempt | Outcome |
|---|---|---|
| Sentiment scoring | SESTM, NB 점수 (5년 롤링 학습창 기반 표본외 점수) | NB 점수를 투자자 수급·장중 경로 분석의 기본 신호로 사용 (`notebooks/02_sentiment_scoring_sanitized.ipynb`) |
| Embedding model | E5-Mistral, KURE 임베딩 (`body_200`)과 잔차화 단계(CAPM/FF3/FF6/JKP) | 잔차화한 모형이 원 임베딩보다 Sharpe가 높음. FF6 잔차 기준 KURE 1.9996, E5-Mistral 1.7007 (비용 전, OOS 228개월) |
| Portfolio formation | 분위 포트폴리오, 규모 통제, 장중 발표 마스크 | 점수 상위 분위에서 발표 전 상승과 익일 장중 반전이 관찰됨 (`notebooks/01_...`, `03_...`) |
| Capacity model | 20일 기준선, 구간 중앙값, ridge, HGB 평균, HGB 30% 분위 | HGB 평균이 기준선 대비 OOS 개선도 0.2076으로 최고. 분위 모형은 과대예측을 줄이는 대신 주문 규모가 작아짐 |
| Investor channel | 활동 비중·불균형 회귀 (일별 Fama-MacBeth) | 고점수 뉴스에서 개인 거래활동 증가, 개인 순매도 |
| Pre-runup actor | 발표 전 5일 수익률과 투자자 유형 | 발표 전 상승은 기관·외국인 순매수와 정합적이나 인과 증거는 아님 |
