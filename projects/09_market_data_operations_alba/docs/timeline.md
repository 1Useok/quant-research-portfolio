# Timeline

| Stage | Description | Main artifacts |
|---|---|---|
| 1. Porting | 팀이 기존에 운영하던 사내 데이터 서버(저장소 내 호스트명 `mft-server`)의 수집 코드를 Windows 로컬 운영 환경으로 이식 | 팀 프로젝트 개요 문서 |
| 2. Docker orchestration | Airflow, Postgres, dashboard 구성 | docker compose |
| 3. KRX collection | daily data and index constituents | `mft_krx` 패키지 |
| 4. KIS collection | minute bars and investor trading flow | `mft_kis` 패키지 |
| 5. Data conversion | raw data to backtest-ready tables | `mft_koscom` 패키지 |
| 6. Validation | pcap and compare report validation | tests and research |
| 7. Operations hardening | catch-up, missing detector, notifier (일부 구현, 일부 계획) | 계획 문서 |

패키지명 접두사 `mft`는 이식 원본 서버 코드베이스에서 온 이름입니다. 위 산출물은 팀 저장소에 있으며 이 폴더에는 포함하지 않았습니다.
