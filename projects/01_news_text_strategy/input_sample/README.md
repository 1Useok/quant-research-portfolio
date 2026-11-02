# Input Sample

원 연구의 뉴스 원문이나 유료 데이터는 포함하지 않습니다. 이 폴더의 파일은 모두 손으로 만든 합성 표본이며, `notebooks/00_public_sample_workflow.ipynb`가 읽습니다.

| File | Description |
|---|---|
| `sample_news_events.csv` | 합성 기사-종목 이벤트 5행 (`event_id`, `date`, `ticker`, `headline`, `news_score`, `event_minute`) |
| `sample_intraday_returns.csv` | 이벤트 시각 기준 분 단위 수익률 장난감 표본 (`event_id`, `offset_min`, `ret_bps`, `trading_value_mil`) |
| `schema.md` | 위 두 파일의 컬럼 설명 |

실행 가능한 전체 합성 입력(기사, 종목 별칭, 학습 라벨, 시세)은 [`../code/data/`](../code/data/)에 있습니다.
