# Results Interpretation

이 프로젝트는 리서치 결과를 사용자가 조작할 수 있는 product interface로 전환한 사례입니다. 전략 성과를 주장하는 프로젝트가 아니며, 공개 폴더의 모든 수치는 합성 데이터입니다.

## What To Look At

- `code/portfolio_engine.py`: 선정 -> 일간 수익률 -> NAV -> 지표 -> 환급 판정의 전체 계산 경로
- `code/test_portfolio_engine.py`: 합성 샘플 실행 검증
- `output_sample/sample_engine_output.json`: 엔진 출력 형식 (합성)
- `output_sample/sample_nav_metrics.csv`: 합성 toy 표

## Interpretation

전략은 연구 노트북 안에서만 존재하면 사용자가 이해하기 어렵습니다. 엔진은 strategy score를 NAV, CAGR, MDD, Sharpe, 환급 판정, 벤치마크 비교로 바꾸는 부분을 담당합니다. 비용/슬리피지/공매도 제약이 없고 무위험률이 고정이므로, 실제 상품 수준의 성과 산출에는 추가 검증이 필요합니다.
