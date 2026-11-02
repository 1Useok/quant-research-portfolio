# Experiment Log

| Experiment | Attempt | Outcome |
|---|---|---|
| Portfolio calculator | 노트북 프로토타입 (`notebooks/01_portfolio_calculator_sanitized.ipynb`) | 선정/NAV 로직 확정 |
| Engine module | 노트북 로직을 `portfolio_engine.py`로 이전, 지표/환급/벤치마크 추가 | `code/portfolio_engine.py` |
| Engine API | FastAPI 래퍼 | 비공개 |
| Frontend controls | 시총 분위, 리밸런싱일, 포지션 모드 | 비공개 원본 앱 |
| Refund simulation | 구간 수익률 < 0 이면 환급 판정, 수익 구간 비율을 확률로 | 엔진에 포함, 합성 샘플 출력 `output_sample/sample_engine_output.json` |
| Public cleanup | 시크릿/DB/parquet 제거, CSV 로더 추가, smoke test | `code/test_portfolio_engine.py` 통과 |
