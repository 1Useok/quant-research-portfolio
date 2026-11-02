# Code

| File | Description |
|---|---|
| `portfolio_engine.py` | 웹앱 백엔드의 계산 엔진을 공개용으로 정리한 사본. pandas/numpy만 필요. `python portfolio_engine.py`로 합성 샘플 실행 |
| `test_portfolio_engine.py` | smoke test (`python test_portfolio_engine.py`) |

원본 엔진에서 바꾼 점: parquet 로더와 KOSPI CSV 경로를 제거하고 CSV 기반 `build_panel()`/`load_sample_panel()`을 넣었으며, 벤치마크는 선택 입력으로 만들었습니다. 계산 로직(리밸런싱, 선정, NAV, 지표, 환급)은 원본과 같습니다. API 서버, 프런트엔드, 크롤러, DB 코드는 공개하지 않았습니다.
