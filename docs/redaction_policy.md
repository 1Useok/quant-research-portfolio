# Redaction Policy

이 저장소는 채용 포트폴리오 제출을 위한 공개/공유 가능 산출물만 포함합니다.

## Excluded

다음 항목은 저장소에 포함하지 않습니다.

| Category | Examples |
|---|---|
| API keys and accounts | BigKinds, DART, KIS, WorldQuant Brain, `.env` |
| Licensed raw data | DataGuide, KRX/KIS raw dumps, BigKinds news text, DART bulk documents |
| Platform identifiers | alpha ids, account routing files, submission logs |
| Large binary data | zip, parquet, xlsx, db, pickle, joblib |
| Third-party confidential materials | proposals, CVs, contracts, private decks |

## Included

다음 항목만 선별적으로 포함합니다.

| Category | Included Form |
|---|---|
| Research summary | project brief, method, result tables |
| Code | sanitized snippets or reproducible skeletons without credentials |
| Evidence | aggregated metrics, charts, anonymized tables |
| Operations | DAG schedules, architecture notes, failure-handling logic |

## Review Checklist

Before pushing any new file:

1. Search for keys, tokens, account names, and local paths.
2. Check file size and extension.
3. Confirm that raw data is not embedded in notebooks.
4. Remove output cells if they include proprietary data.
5. Prefer aggregated result tables over original records.

