# Results Interpretation

배당 검색량 기반 투자자 관심도가 고배당 포트폴리오 수익률과 수급에 주는 정보를 검토한 프로젝트입니다.

## What To Look At

- `README.md`의 Headline Results: 논문 초안 기준 핵심 결과 (in-sample, gross)
- `notebooks/02_svi_construction_sanitized.ipynb`: SVI/ASVI 구성
- `notebooks/03_portfolio_analysis_sanitized.ipynb`: 포트폴리오, 비정상수익률, 헤지
- `notebooks/01_beta_div_daily_report_sanitized.ipynb`: beta_divatt 확장 분석
- `input_sample/sample_search_volume.csv`, `output_sample/sample_regression_summary.csv`: 합성 형식 예시

## Interpretation

ASVI 증가는 개인 순매수 증가와 연결되고 1개월 뒤 고배당 포트폴리오의 비정상수익률 하락과 연결되어, 지속적 정보보다 단기 수요 충격에 가깝다는 해석입니다. 모든 회귀는 전체 표본 in-sample이고 한계는 다음과 같습니다: 키워드가 투자 의도와 단순 정보 탐색을 구분하지 못함, 포트폴리오 수준 분석, 타이밍 전략의 거래비용 미반영 및 표본 밖 검증 부재.
