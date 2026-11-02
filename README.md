# Quant Research & Trading Project Portfolio

퀀트 전략 연구, 포트폴리오 최적화, 시장 데이터 운영 프로젝트를 모은 포트폴리오입니다. 모든 프로젝트는 [`projects/`](PROJECTS.md) 아래에 번호순으로 있습니다.

- **실행 가능한 프로젝트(01~05, 07, 08):** `code/` 폴더에 코드, 합성 입력, 테스트가 있습니다. 06과 15에도 합성 입력으로 도는 공개 스크립트가 있습니다. 원 연구의 핵심 절차(신호 → 주문 → 장부, 검정 → 기각, 데이터 등록 → 복구)를 합성 데이터로 옮겼고, GitHub Actions가 push마다 실행합니다.
- **연구 전시본(01, 06, 09~15):** 문제의식, 방법론, 결과 해석, 정제 노트북, 합성 input/output 샘플을 담았습니다.

원천 데이터, 유료 데이터, API 키, 계정 정보는 포함하지 않습니다. 기준은 [redaction policy](docs/redaction_policy.md)에 있습니다.

[![projects](https://github.com/1Useok/quant-research-portfolio/actions/workflows/projects.yml/badge.svg)](https://github.com/1Useok/quant-research-portfolio/actions/workflows/projects.yml)

## Projects

| No. | Project | 질문 / 내용 | 실행 코드 |
|---|---|---|---|
| 01 | [News Text Strategy](projects/01_news_text_strategy/README.md) | 뉴스 점수가 높은 종목의 발표 전후 가격 경로와 수급, 종가 매수·익일 VWAP 청산의 비용 후 성과 | 표준 라이브러리 |
| 02 | [IOF Long-Short](projects/02_iof_longshort/README.md) | 시총이 커진 기업에 기관 순매도가 몰리면 이후 상대적으로 반등하는가 | 표준 라이브러리 |
| 03 | [Cointegration Breakdown](projects/03_cointegration_breakdown/README.md) | 공적분 쌍의 괴리 경보 뒤에도 거래비용을 회수할 만큼 괴리가 커지는가 | numpy, pandas, scipy, statsmodels |
| 04 | [JKP ML Long-Short](projects/04_jkp_ml_longshort/README.md) | 월말에 보이는 재무·가격 특성만으로 다음 달 롱숏 종목을 정할 수 있는가 | numpy, pandas, scikit-learn, xgboost |
| 05 | [JKP Portfolio-ML](projects/05_jkp_portfolio_ml/README.md) | 거래비용을 반영해 특성에서 직접 학습한 비중이 비용을 무시한 규칙보다 비용 후 성과가 나은가 (구현 가능한 효율적 프런티어) | 표준 라이브러리 |
| 06 | [Factor Strategy Research](projects/06_factor_strategy_research/README.md) | 대규모 알파 풀에서 상관을 관리하며 조합 전략 선별 | numpy, pandas (선별 스크립트) |
| 07 | [Quant Model Replication](projects/07_quant_model_replication/README.md) | 공표 종목과 내 모델의 차이는 팩터 비중에서 생겼는가, 점수 산정에서 생겼는가 | 표준 라이브러리 |
| 08 | [Market Data Registry](projects/08_market_data_registry/README.md) | 날짜 없는 수급 파일을 어느 거래일에 붙이고, 중복·충돌·롤백을 어떻게 처리하는가 | 표준 라이브러리 (sqlite3) |
| 09 | [Market Data Operations: alba](projects/09_market_data_operations_alba/README.md) | KRX/KIS 데이터 자동 수집(Airflow)과 품질 검증 (팀 프로젝트) | |
| 10 | [Industry Shock Wave](projects/10_industry_shock_wave/README.md) | 산업연관표·공급망·OpenDART로 산업 충격을 기업 위험으로 구조화 | |
| 11 | [ASVI Dividend Attention](projects/11_asvi_dividend_attention/README.md) | 배당 검색량 기반 투자자 관심도와 고배당주 수익률·수급 | |
| 12 | [PER Anomaly](projects/12_per_anomaly/README.md) | 적정 PER 추정과 밸류에이션 괴리 | |
| 13 | [Idiosyncratic Volatility In Korea](projects/13_ivol_korea_market/README.md) | 한국 주식시장의 idiosyncratic volatility 이상현상 | |
| 14 | [CRASHP](projects/14_crashp_tail_risk/README.md) | 급락/급등 확률과 꼬리위험 | |
| 15 | [Quant Subscription Platform](projects/15_quant_subscription_platform/README.md) | 전략 성과와 환급 구조를 보여주는 구독형 웹앱 | numpy, pandas (계산 엔진) |

분야별 분류는 [PROJECTS.md](PROJECTS.md)에 있습니다.

## 실행

실행 코드가 있는 프로젝트는 모두 같은 방식으로 실행합니다(Python 3.11 이상).

```sh
cd projects/<NN_project>/code
python -m pip install -r requirements.txt   # requirements.txt가 있는 프로젝트만
python run_demo.py                          # outputs/ 에 결과 CSV 생성
python -m unittest discover -s tests -v
```

`outputs/`는 실행할 때 생성되며 저장소에는 올리지 않습니다. CI 설정은 [workflow](.github/workflows/projects.yml)에 있습니다.

## Repository Structure

```text
projects/
  <NN_project>/
    README.md                 질문, 방법, 결과, 원 연구와 합성 데이터의 구분
    code/                     실행 코드: run_demo.py, *.py, data/(합성 입력), tests/
    notebooks/                정제 노트북 (전시본)
    input_sample/ output_sample/ docs/
docs/redaction_policy.md      공개 기준
.github/workflows/            프로젝트 데모·테스트 CI
```

## Disclosure

프로젝트 원본에는 유료 데이터, API 키, 계정 정보, 대용량 원천 데이터가 있어 그대로 공개하지 않습니다. `code/`와 `input_sample/`의 종목·가격·수급·기사는 모두 합성 데이터이며, 원 연구의 수치는 각 README에 출처를 구분해 따로 적었습니다.

## 이용 조건

포트폴리오 검토용으로 공개한 저장소입니다. 코드와 문서의 복제, 수정, 재배포, 상업적 이용 및 실거래 사용을 허락하지 않습니다. 자세한 내용은 [LICENSE](LICENSE)를 참고하세요.
