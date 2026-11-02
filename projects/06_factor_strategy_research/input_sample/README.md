# Input Sample

| File | Description |
|---|---|
| `sample_factor_returns.csv` | 합성 팩터 8개 x 252영업일(2025-01-02 시작) 일별 수익률. 난수 생성(seed 42)이며 실제 데이터 아님 |
| `sample_factor_metadata.csv` | 합성 factor metadata (family, turnover, coverage) |
| `schema.md` | 컬럼 정의 |

샘플 날짜(2025)는 합성 데이터용이며 프로젝트의 실제 데이터 구간(2019-2024)과 다릅니다. 생성기는 `../code/make_synthetic_factors.py`입니다.
