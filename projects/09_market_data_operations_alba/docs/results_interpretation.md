# Results Interpretation

이 프로젝트는 수익률 모델이 아니라 운영 안정성을 보여주는 프로젝트입니다. 저는 팀 기여자로 참여했습니다.

## What To Look At

- `output_sample/dag_schedule.md`: 운영 DAG 구조 요약
- `output_sample/sample_quality_report.csv`: 합성 데이터 품질 점검 결과
- `code/public_pipeline_skeleton.py`: 합성 sample로 품질 점검을 수행하는 skeleton

## Interpretation

데이터 수집 실패는 잘못된 신호로 이어질 수 있습니다. 이 프로젝트는 KRX universe, KIS minute bars, raw-to-backtest conversion, data quality check를 분리해 운영 안정성과 검증 가능성을 높이는 구조입니다. 데이터 일치율(97%, 92% 등)은 팀 검증 메모의 값이며 이 저장소에서 재현할 수 없습니다.
