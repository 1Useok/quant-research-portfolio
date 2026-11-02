# 12. PER Anomaly (Fair P/E Gap)

## Summary

회귀와 XGBoost로 기업의 적정 PER(Fair P/E)을 추정하고, 실제 PER과 모델 추정치의 괴리를 신호로 써서 한국 주식시장(KOSPI+KOSDAQ)의 valuation anomaly를 검증한 프로젝트입니다. 이 폴더는 연구 노트북 3종의 참고용 사본, 합성 샘플 데이터, 공개 가능한 검증 결과 요약을 담고 있습니다.

## Research Question

실제 PER이 기업 특성으로 설명되는 적정 PER보다 낮거나 높은 경우, 이후 수익률에 예측력이 존재하는가? 그 예측력이 거래비용과 차입비용을 반영한 뒤에도 남는가?

## Headline Results

백테스트 감사 보고서(`BACKTEST_REPORT.md`, 2026-09-03 실행)의 수치입니다. 원본 보고서와 CSV는 로컬에 보관하며 이 저장소에는 포함하지 않았습니다.

| Item | Value |
|---|---|
| Period | 2004-05 ~ 2025-08 (256개월, 월말 리밸런싱) |
| Signal | `log(예측 Fair P/E) - log(실제 P/E)`; 상위 10% 롱 / 하위 10% 숏, 동일가중 |
| Universe | KOSPI+KOSDAQ, 금융업 키워드 제외, 형성월 시가총액 2,000억 원 이상 (월 평균 약 350종목, 레그당 중앙값 약 35종목) |
| Prediction | 60개월 롤링 윈도우로 학습한 XGBoost의 **다음 달 out-of-sample 예측치** (저장된 예측치를 사용, 모델 재학습은 하지 않음) |

| Series (200% gross L/S) | CAGR | Ann. vol | Sharpe (rf=0) | MDD | Carhart monthly alpha (HAC t) |
|---|---:|---:|---:|---:|---:|
| Gross (비용 전) | 8.30% | 15.91% | 0.58 | -35.08% | 0.96% (3.55) |
| Net (거래 20bp/체결금액 + 연 2% 차입비용) | 1.71% | 15.90% | 0.19 | -52.45% | 0.44% (1.62) |

- 해석: 비용 전에는 통계적으로 유의한 알파가 있지만, 보수적 비용 가정(20bp, 연 2% 차입비용) 아래에서는 알파가 약 절반으로 줄고 유의성도 사라집니다. 비용 민감도 표에서 거래비용 50bp면 CAGR이 음수입니다.
- 하위 기간(gross CAGR): 2005-2009 14.5%, 2010-2014 2.8%, 2015-2019 4.7%, 2020-2025.08 10.3%로 기간별 편차가 큽니다.
- Alpha decay: 형성 후 첫 5거래일 평균 7.2bp/일, 21~60거래일 평균 3.1bp/일 (후기/초기 0.44).
- 한계: 현금배당 반영 여부가 불분명한 수정주가를 사용했고, 공매도 가능 종목/대차 가용성/슬리피지는 반영하지 않았습니다. 이 수치는 전체 기간 단일 백테스트이며 별도의 hold-out 구간은 없습니다(예측치만 롤링 out-of-sample).
- 위 수치는 이 저장소의 노트북으로 재현되지 않습니다(유료 데이터 필요).

## Data And Features

| Item | Description |
|---|---|
| Valuation | PER, PE, earnings-related variables (DataGuide 추출본, 비공개) |
| Firm characteristics | size, industry, fundamentals |
| Returns | monthly stock returns |
| Models | pooled OLS, industry OLS, XGBoost |

## Methodology

1. PER winsorizing and preprocessing
2. explanatory variable preprocessing
3. pooled OLS and industry-level OLS fitting
4. XGBoost modeling
5. rolling-window prediction (60개월 윈도우, 이후 1개월 예측)
6. Fama-MacBeth regression
7. portfolio performance test

## Project Artifacts

| Path | Role |
|---|---|
| `notebooks/00_public_sample_workflow.ipynb` | 합성 샘플로 실행되는 PER gap 데모 (실행 출력 포함) |
| `notebooks/01_per_preprocessing_sanitized.ipynb` | 전처리 참고용 사본 (비공개 데이터 필요) |
| `notebooks/02_per_modeling_sanitized.ipynb` | OLS/XGBoost, 롤링 예측 참고용 사본 (비공개 데이터 필요) |
| `notebooks/03_hypothesis_testing_sanitized.ipynb` | 가설검정/포트폴리오 참고용 사본 (비공개 데이터 필요) |
| `input_sample/` | 합성 데이터 CSV와 스키마 |
| `output_sample/sample_model_comparison.csv` | 합성 toy 표 (연구 결과 아님) |
| `docs/` | 실험 로그, 해석, 타임라인 |
| 비공개 원본 | 예측 PE CSV, 포트폴리오 수익률 CSV, 백테스트 xlsx/차트, 논문 PDF |

## Trading Relevance

장중 매매보다는 중기(월간) 리밸런싱형 valuation signal입니다. 모델 기반 적정가치와 실제 가격의 괴리를 신호로 바꾸고, 비용 후 알파가 얼마나 남는지까지 확인하는 알파 리서치 흐름을 보여줍니다.

## Redaction Notes

원본에서 공개하지 않은 것: 유료 데이터(DataGuide) 기반 원자료와 예측/수익률 CSV, 논문 PDF, 백테스트 워크북.
