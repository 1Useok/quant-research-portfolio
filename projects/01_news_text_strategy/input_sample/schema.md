# Input Schema

## `sample_news_events.csv`

| Column | Description |
|---|---|
| `event_id` | anonymized news-event identifier |
| `date` | event date |
| `ticker` | anonymized stock identifier |
| `headline` | synthetic headline |
| `news_score` | sentiment or text-derived score |
| `event_minute` | minute of event in trading session |

## `sample_intraday_returns.csv`

| Column | Description |
|---|---|
| `event_id` | event identifier |
| `offset_min` | minutes relative to event |
| `ret_bps` | return in basis points |
| `trading_value_mil` | toy trading value in million KRW |

