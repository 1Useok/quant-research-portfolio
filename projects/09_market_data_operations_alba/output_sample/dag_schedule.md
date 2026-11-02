# Market Data Operations Evidence

## DAG Schedule

| DAG | Purpose | Schedule |
|---|---|---|
| `krx_daily_batch` | KRX daily market data | 23:00 KST |
| `krx_index_constituents` | index constituents | 22:00 KST |
| `kis_minute_batch` | KIS minute bars | 23:30 KST |
| `kis_investor_trading` | investor trading flow | every market minute |
| `convert_raw_to_bt` | raw-to-backtest conversion | D+1 01:30 |
| `data_quality_check` | quality checks | D+1 01:00 |
| `catch_up` | missing-data recovery | planned/partial |

## Operational Notes

- The pipeline avoids collecting KIS minute data against a wrong universe when KRX crawling fails.
- Rate limits are treated as a design constraint.
- Market data is converted into backtest-ready tables after raw ingestion.
- Data quality checks run separately from collection jobs.

## Validation Notes

팀 `PROJECT_OVERVIEW.md` 검증 메모 기준이며 이 저장소에서 재현하지 않았습니다.

| Item | Result |
|---|---|
| Futures pcap validation (team note) | 100% match |
| Options validation | floating-point-level differences |
| Stock OHLC validation (team note) | around 97% |
| Stock volume validation (team note) | around 92% |

