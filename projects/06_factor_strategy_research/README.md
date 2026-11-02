# 06. Factor Strategy Research

## Summary

WorldQuant Brain 플랫폼에서 대규모 팩터(알파) 후보 풀을 만들고, Sharpe, fitness, turnover, 기존 제출 전략과의 상관 조건으로 조합을 탐색·시뮬레이션한 프로젝트입니다. 이 폴더에는 선별 로직을 보여주는 소형 공개 코드와 합성 데이터 샘플만 있고, 플랫폼 계정·알파 식별자·원본 결과는 포함하지 않습니다.

## Workflow

1. 단일 팩터 성과 계산
2. 후보 팩터 풀 구성
3. 다중 팩터 조합 탐색
4. 기존 제출/선정 전략과 상관관계 제한
5. 성과, turnover, fitness 기준으로 후보 선별
6. 자동 시뮬레이션과 제출 관리

## Key Evidence (WorldQuant Brain 플랫폼 in-sample 지표)

아래 수치는 모두 Brain 플랫폼의 in-sample(IS) 시뮬레이션 지표이며, 원본 결과 파일이 이 저장소에 없고 현재 로컬에서 재확인하지 못했습니다(2026-06 프로젝트 점검 메모 기준). out-of-sample 또는 실거래 성과가 아닙니다.

| Metric | Result | 비고 |
|---|---:|---|
| Base verified factor pool | 1,630 factors | 풀 크기 |
| Extended candidate pool | 2,306 factors | OAP 후보 676개 추가 |
| Daily return period | 2019-01-02 to 2024-12-31 | 플랫폼 데이터 구간 (샘플 CSV의 2025 날짜와 무관) |
| Performance scenarios | 9 | 조합 시나리오 수 |
| Scenario average IS Sharpe | 5.794 | in-sample, 플랫폼 지표(비용 반영 여부 미확인) |
| Scenario max IS Sharpe | 6.862 | in-sample |
| Scenario max IS fitness | 6.371 | in-sample |
| D0 improvement candidates | 10 | 선별 후보 수 |
| D0 candidate average IS Sharpe | 2.513 | in-sample |
| D0 candidate average IS turnover | 4.64% | in-sample |

IS Sharpe 5~7 수준은 다수 후보 중 선택한 결과의 in-sample 값이므로 과최적화 가능성이 크고, 기대 성과로 읽으면 안 됩니다.

## Public Sample And Code

| File | Description |
|---|---|
| `code/factor_selection.py` | 상관 필터 + greedy 조합 선택 (합성 데이터로 실행, `python factor_selection.py`) |
| `code/make_synthetic_factors.py` | 합성 팩터 수익률 생성기 (seed 고정) |
| `input_sample/` | 합성 팩터 8개 x 252영업일 수익률, metadata |
| `output_sample/sample_candidate_summary.csv` | `factor_selection.py` 실행 결과 (합성, in-sample, gross, 비용 미반영) |
| `notebooks/00_public_sample_workflow.ipynb` | 합성 데이터 요약 (실행 결과 저장) |
| `notebooks/01_strategy_picking_sanitized.ipynb` | 원본 노트북의 참고용 사본 (비공개 데이터 필요) |

샘플 데이터는 전부 난수로 만든 합성 데이터이며 실제 팩터 성과와 무관합니다.

## Positioning

"좋은 팩터 하나를 찾았다"가 아니라 "후보를 체계적으로 만들고, 중복을 제거하고, 기준에 맞는 전략을 운영 가능한 형태로 선별했다"는 점을 보여주는 프로젝트입니다.

## 원본에서 공개하지 않은 것

WorldQuant Brain 계정 파일, 알파 식별자, 제출 JSON, 플랫폼 로그, 독자 수식, 시뮬레이션 스케줄러 원본 코드.
