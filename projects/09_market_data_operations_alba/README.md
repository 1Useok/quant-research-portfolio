# 09. Market Data Operations: alba

## Summary

KRX 크롤러와 KIS API로 시장 데이터를 로컬 Windows 환경에서 자동 수집, 검증, 변환하는 Airflow 기반 팀 프로젝트(GitHub `Jayden-Jaehoon/alba`)입니다. 저는 이 팀 프로젝트의 기여자(team contributor)로 참여했으며, 이 폴더는 프로젝트 구조와 운영 설계, 공개해도 안전한 합성 샘플 파이프라인을 정리한 것입니다. 저장소 전체를 단독으로 만든 것이 아닙니다.

개인이 단독으로 만든 데이터 저장소 프로젝트는 별도 항목인 [`../08_market_data_registry`](../08_market_data_registry)를 참고하세요.

## Why It Matters For Trading

트레이딩 프로그램 운영에서는 신호 자체만큼 데이터 수집의 안정성, 누락 탐지, 품질 검증이 중요합니다. 이 프로젝트는 매일 반복되는 데이터 파이프라인을 운영 관점에서 설계한 사례입니다.

## Architecture

| Component | Role |
|---|---|
| Airflow | batch scheduling and dependency control |
| PostgreSQL | Airflow metadata and local data store |
| KRX crawler | daily market data and index constituents |
| KIS API client | minute bars and investor trading flow |
| Streamlit dashboard | monitoring and inspection |
| Tests/research notebooks | pcap matching and data quality checks |

## DAG Schedule

| DAG | Purpose | Schedule |
|---|---|---|
| `krx_daily_batch` | KRX daily data collection | 23:00 KST |
| `krx_index_constituents` | index constituents | 22:00 KST |
| `kis_minute_batch` | KIS minute bar collection | 23:30 KST |
| `kis_investor_trading` | investor trading flow | every market minute |
| `convert_raw_to_bt` | raw-to-backtest conversion | D+1 01:30 |
| `data_quality_check` | quality checks | D+1 01:00 |
| `catch_up` | missing data recovery | planned/partial |

## Key Evidence

설계 사항:

- KRX universe 수집이 실패하면 잘못된 universe로 KIS 분봉을 수집하지 않고 해당 배치를 skip합니다.
- KIS API rate limit을 수집 구조(병렬화 제한)에 반영했습니다.

검증 결과 (팀 `PROJECT_OVERVIEW.md`의 검증 메모 기준, 이 저장소에서 재현하지 않았고 검증 산출물은 비공개):

| Item | 메모 내용 |
|---|---|
| Futures vs pcap | 100% 일치 |
| Options vs pcap | 부동소수점 수준 차이만 |
| Stock OHLC / volume (KRX+NXT 통합) | 약 97% / 약 92% |

위 일치율의 비교 대상, 표본 기간, 일치 기준은 이 저장소에 없습니다. 수익률 성과가 아닌 데이터 일치율이므로 in-sample/out-of-sample 구분은 해당하지 않습니다.

## Public Sample And Code

| File | Description |
|---|---|
| `code/public_pipeline_skeleton.py` | 합성 샘플로 품질 점검을 수행하는 축소 파이프라인 (`python public_pipeline_skeleton.py`) |
| `input_sample/` | 합성 universe, minute bar |
| `output_sample/dag_schedule.md` | DAG 스케줄과 검증 메모 |
| `output_sample/sample_quality_report.csv` | 합성 데이터 품질 점검 결과 |
| `notebooks/00_public_sample_workflow.ipynb` | 합성 샘플 품질 점검 (실행 결과 저장) |

## Positioning

분석보다 운영 역량을 보여주는 프로젝트입니다. 신호 연구뿐 아니라 데이터가 매일 정확히 들어오도록 관리하는 관점의 팀 협업 사례입니다.

## 원본에서 공개하지 않은 것

`.env`, KIS 키, 로컬 데이터 경로, raw DB, 원천 시장 데이터, 계정별 설정, 팀 저장소 원본 코드.
