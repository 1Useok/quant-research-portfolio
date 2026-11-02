# Results Interpretation

이 프로젝트는 평균 수익률이 아니라 급락/급등 같은 tail event probability에 집중합니다.

## Reported Result (private data, not reproducible here)

- 확률 최저 십분위 vs 최고 십분위(동일가중, gross, 비용 전): 연 +17.0% vs -22.0% (2005-10~2025-01).
- 2021-01 이후 구간(노트북의 test 구간): +10.7% vs -26.4%. 같은 구간 전 종목 평균은 약 -0.8%라 확률 정렬의 구분력은 유지되지만, 이 숫자는 비용/공매도 제약을 반영하지 않았습니다.
- 급등 확률 정렬은 반대로 최고 십분위 +23.3%, 최저 -16.8%.

tail-risk signal은 롱온리 알파뿐 아니라 리스크 회피, 종목 필터링, 포지션 사이징에 활용될 수 있습니다.

## Files To Look At

- `notebooks/00_public_sample_workflow.ipynb`: 합성 데이터 데모
- `notebooks/01_crash_quarterly_sanitized.ipynb`: 실제 연구 코드(비공개 데이터 필요)
- `input_sample/feature_dictionary.md`: 구현된 변수 정의
- `output_sample/sample_probability_summary.csv`: 합성 toy 표
