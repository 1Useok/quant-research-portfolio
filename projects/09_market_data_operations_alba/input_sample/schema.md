# Input Schema

## `sample_universe.csv`

| Column | Description |
|---|---|
| `trade_date` | target date |
| `ticker` | anonymized ticker |
| `asset_type` | stock, futures, options, ETF |
| `source` | KRX or KIS |

## `sample_minute_bar.csv`

| Column | Description |
|---|---|
| `timestamp` | KST timestamp |
| `ticker` | anonymized ticker |
| `open`, `high`, `low`, `close` | synthetic price values |
| `volume` | toy minute volume |

