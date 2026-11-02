# 14. CRASHP Tail Risk

## Summary

한국 주식에서 향후 6개월 내 급락(-35% 이하)/급등(+35% 이상) 확률을 다항 로지스틱 회귀로 추정하고, 이 확률로 종목을 십분위 정렬해 사후 수익률을 확인한 프로젝트입니다. 학술 논문(주가 급락 확률과 횡단면 수익률)의 CRASHP 아이디어를 한국 시장에 적용했습니다.

## Research Question

주가 급락 또는 급등 가능성을 사전에 설명하는 변수를 만들 수 있는가? 이 확률로 종목을 정렬하면 이후 수익률 차이가 나타나는가?

## Headline Results

아래 수치는 로컬 원본 출력(`crashp(6m,35%).csv`, `ret.csv`)에서 노트북의 포트폴리오 구성 로직(`crashp.shift(1)` 십분위 정렬, 동일가중)을 그대로 재계산한 값입니다. 모든 수치는 **비용 전(gross), 롱온리 십분위**이며 공매도/거래비용/슬리피지는 반영하지 않았습니다. 이 저장소의 노트북으로는 재현되지 않습니다(원본 raw 데이터 필요).

| 구간 | 최저 확률 십분위 (D1) CAGR | 최고 확률 십분위 (D10) CAGR |
|---|---:|---:|
| 2005-10 ~ 2025-01 (232개월, 전체) | +17.0% | -22.0% |
| 2005-10 ~ 2020-12 (183개월) | +18.7% | -20.8% |
| 2021-01 ~ 2025-01 (49개월, 노트북의 test 구간과 동일) | +10.7% | -26.4% |

- 비교용: 같은 기간 확률 정보가 있는 전 종목 동일가중 평균은 약 연 9.0% (2021-01 이후는 약 -0.8%). 십분위당 평균 약 160종목입니다.
- 확률은 매월 과거 데이터로 모형을 다시 적합한 expanding-window 예측(예측 시점은 학습 시점 +7개월)이므로, 모형 적합 관점에서는 전 구간이 out-of-sample입니다. 다만 변수 선택과 임계값(6개월/35%)은 같은 표본에서 정했으므로 전체를 순수한 hold-out으로 보기는 어렵습니다.
- 분류 모형 자체: 학습 구간(~2020-01, SMOTE 오버샘플링 후 642,933 관측) 다항 로짓 pseudo R-squared 0.0756 (in-sample). 별도의 분류 정확도 수치는 이 문서에서 검증하지 못했습니다.
- 급등 확률(jump probability)은 방향이 반대입니다: 최고 확률 십분위 +23.3% / 최저 -16.8% (2005-10~2025-02, 동일 방식으로 계산).
- 한계: 소형/비유동 종목 포함, 동일가중, 비용 미반영이라 실제 매매 가능한 수익률이 아닙니다. 확률 절대값은 SMOTE로 클래스 균형을 맞춰 학습했기 때문에 실제 발생 빈도보다 높게 나오며, 순위(랭킹)에만 의미가 있습니다.

## Data And Features

원자료는 분기/월별 한국 주식 패널(가격, 상장주식수, 거래량, 재무, 개인 순매수, 코스피)이며 비공개입니다.

| Feature (code name) | Meaning |
|---|---|
| RM12 (논문의 RM5) | 코스피의 최근 6개월(t-5~t) 로그 수익률 |
| EXRET12 | 종목의 최근 6개월 로그 수익률에서 RM12를 뺀 초과수익률 |
| TVOL / TSKEW | 최근 125거래일 일간 로그수익률의 표준편차 / 왜도 |
| SIZE, DTURN, AGE, TANG, SALESG, DRETAIL, CAIPG | 규모, 초과회전율, 상장 경과, 유형자산 비율, 매출 성장, 개인 순매수, 자본잠식률 변화 |
| Label | 향후 6개월 로그수익률 >= +35% 이면 jump, <= -35% 이면 crash |

## Methodology

1. 월말 가격/재무 패널 구성, 금융업 키워드 및 이력 18개월 미만 종목 제외
2. 위 변수와 crash/jump 라벨 생성
3. SMOTE 오버샘플링 후 다항 로지스틱 회귀(MNLogit); 2020-01까지 학습/2021년 이후 테스트
4. 매월 expanding-window로 재적합해 종목별 crash/jump 확률 생성
5. 전월 확률 기준 십분위 포트폴리오 및 SIZE 통제 정렬로 사후 수익률 확인

## Project Artifacts

| Path | Role |
|---|---|
| `notebooks/00_public_sample_workflow.ipynb` | 합성 데이터로 실행되는 tail-risk 점수 데모 (출력 포함) |
| `notebooks/01_crash_quarterly_sanitized.ipynb` | 전체 연구 노트북의 참고용 사본 (비공개 raw 데이터 필요) |
| `input_sample/` | 합성 패널, 스키마, feature dictionary |
| `output_sample/sample_probability_summary.csv` | 합성 toy 표 (연구 결과 아님) |
| `docs/` | 실험 로그, 해석, 타임라인 |
| 비공개 원본 | `raw_q.xlsx`, 확률/수익률/포지션 CSV 전체(예: 6개월/35% 및 24주/35%, 12개월/70% 설정), KOSPI/KOSPI200 유니버스별 출력, 참고 논문 PDF |

## Tools

Python, pandas, numpy, scipy, statsmodels, scikit-learn, imbalanced-learn, yfinance(벤치마크 지수 다운로드), joblib.

## Trading Relevance

뉴스나 테마 이벤트 이후 급등락 위험을 다루는 리스크 관리/종목 필터링 용도입니다. 평균 수익률이 아니라 tail event probability에 집중한 점이 특징입니다.

## Redaction Notes

원본에서 공개하지 않은 것: raw 데이터 엑셀, 전체 확률/수익률/포지션 출력 CSV, 참고 논문 PDF.
