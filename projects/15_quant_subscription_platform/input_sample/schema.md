# Input Schema (synthetic toy data)

## `sample_strategy_scores.csv`

| Column | Description |
|---|---|
| `date` | score date (month-end) |
| `ticker` | anonymized ticker |
| `strategy_score` | toy strategy score |
| `size_decile` | toy size bucket (1 = smallest) |

## `sample_prices.csv`

| Column | Description |
|---|---|
| `date` | business date |
| `ticker` | anonymized ticker |
| `close` | toy close price |

`code/portfolio_engine.py`의 `build_panel()`이 두 파일을 합쳐 `daily_ret`을 만들고 점수를 종목별로 forward-fill 합니다.
