# Timeline

원 연구의 진행 순서다. 공개한 산출물은 [상위 README](../README.md)의 파일 구성을 참고한다.

| Stage | Description | 이 저장소의 관련 파일 |
|---|---|---|
| 1. Data collection | BigKinds 뉴스와 DART 공시 수집, 기업 단위 연결 | 비공개 |
| 2. Company mapping | 기업명 이력과 기사 언급 연결 | `code/signals.py` (합성 별칭 태깅 축소판) |
| 3. Text preprocessing | 토큰화, 라벨링, 기사 단위 분석 행 구성 | 비공개 |
| 4. Sentiment scoring | SESTM, NB 점수 | `notebooks/02_sentiment_scoring_sanitized.ipynb`, `code/signals.py` |
| 5. Embedding regression | 기사 임베딩을 종목-월 신호로 집계 | 결과만 `output_sample/result_tables.md` |
| 6. Portfolio test | 분위 포트폴리오, 규모 통제, 알파 검증 | 결과만 `output_sample/result_tables.md` |
| 7. Intraday validation | 뉴스 이후 분 단위 가격 경로, 분위별 경로 | `notebooks/01_intraday_path_by_nb_quintile_sanitized.ipynb` |
| 8. Capacity and cost | 경매 거래대금 용량, 비용 민감도 | `notebooks/03_portfolio_capacity_and_costs_sanitized.ipynb`, `code/backtest.py` |
| 9. Investor channel | 개인·기관·외국인 활동과 발표 전 상승 주체 분석 | 결과만 `output_sample/result_tables.md` |
