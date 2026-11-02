# Experiment Log

| Experiment | Attempt | Outcome |
|---|---|---|
| Factor pool | 1,630 verified factors | baseline pool (플랫폼 IS 기준) |
| Pool expansion | 676 OAP candidates added | 2,306 candidate pool |
| Scoring variants | Kelly, q-factor, quintile | scoring 경로 3종 비교 |
| Combo search | parallel and greedy search | 후보 전략 선별 |
| Correlation filter | 제출 전략과의 overlap 제한 | `code/factor_selection.py`에 축소판 구현 |
| Simulation scheduler | Account, WorkItem, WorkScheduler 구조 | 자동 시뮬레이션 운영 (원본 비공개) |

수치는 모두 Brain 플랫폼 in-sample 지표입니다.
