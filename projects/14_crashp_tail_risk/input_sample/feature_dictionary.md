# Feature Dictionary

원본 구현(`notebooks/01_crash_quarterly_sanitized.ipynb`) 기준입니다. 샘플 CSV의 컬럼명은 단순화되어 있습니다.

| Feature | Meaning |
|---|---|
| `rm5` (code: RM12) | 코스피의 t-5~t 개월 로그 수익률 |
| `exret12` | 종목의 t-5~t 개월 로그 수익률 - rm5 (이름은 12지만 구현은 6개월 윈도우) |
| `tvol` | 최근 125거래일 일간 로그수익률 표준편차, 월말 값 |
| `tskew` | 최근 125거래일 일간 로그수익률 왜도, 월말 값 |
| `crash_label` | 향후 6개월 로그수익률 <= -35% 이면 1 |
| `jump_label` | 향후 6개월 로그수익률 >= +35% 이면 1 |

원본 모형에는 SIZE, DTURN, AGE, TANG, SALESG, DRETAIL, CAIPG도 포함되지만 샘플 데이터에는 넣지 않았습니다.
