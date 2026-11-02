# Results Interpretation

이 프로젝트의 핵심은 뉴스 텍스트 신호를 점수로 끝내지 않고 가격 경로, 투자자 수급, 거래 가능 용량까지 이어서 확인했다는 점이다.

## 읽는 순서

- [`../README.md`](../README.md): 원 연구 결과 요약. 수치마다 표본외 여부와 비용 반영 여부를 적었다.
- [`../output_sample/result_tables.md`](../output_sample/result_tables.md): 같은 수치의 표 형태
- [`../code/README.md`](../code/README.md): 종가 매수·익일 VWAP 매도 규칙을 합성 데이터로 재현한 실행 코드
- [`../notebooks/01_intraday_path_by_nb_quintile_sanitized.ipynb`](../notebooks/01_intraday_path_by_nb_quintile_sanitized.ipynb): 분위별 장중 경로 (참고용 사본)
- [`../notebooks/03_portfolio_capacity_and_costs_sanitized.ipynb`](../notebooks/03_portfolio_capacity_and_costs_sanitized.ipynb): 비용·용량 분석 (참고용 사본)

## 해석상 주의

- 임베딩 포트폴리오의 Sharpe 1.7007·1.9996은 표본외 월별 롱숏의 **비용 전** 값이다. 비용과 용량은 별도 분석(용량 모형, 비용·슬리피지 시나리오)에서 다루며 하나의 순수익률로 합쳐 보고하지 않았다.
- 용량 모형의 R2 0.2076은 20일 중앙값 기준선 대비 개선도다.
- 투자자 수급 결과는 회귀 계수이며, 특정 투자자가 가격을 움직였다는 인과 증거가 아니다.
- `code/`의 수익률은 합성 표본의 장부 결과이고 원 연구의 성과가 아니다.
