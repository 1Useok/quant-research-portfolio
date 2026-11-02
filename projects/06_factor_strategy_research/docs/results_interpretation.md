# Results Interpretation

이 프로젝트의 핵심은 단일 팩터 성과보다, 대규모 후보를 체계적으로 줄이고 중복 상관을 관리하는 탐색 프로세스입니다.

## What To Look At

- `code/factor_selection.py`: 상관 필터와 greedy 조합 선택 (합성 데이터)
- `output_sample/sample_candidate_summary.csv`: 위 코드의 실행 결과 (합성, in-sample, gross)
- `notebooks/01_strategy_picking_sanitized.ipynb`: strategy selection 원본 노트북의 참고용 사본
- `docs/timeline.md`: factor pool 확장과 simulation workflow

## Interpretation

팩터 후보가 많을수록 과최적화와 중복 노출 위험이 커집니다. 이 프로젝트는 Sharpe, fitness, turnover, correlation을 함께 고려해 후보를 줄이는 과정을 보여줍니다. README의 IS Sharpe는 다수 후보에서 선택된 in-sample 값이므로 out-of-sample 성과를 보장하지 않으며, 플랫폼 지표를 로컬에서 재현해 검증한 것도 아닙니다.
