# Experiment Log

| Experiment | Attempt | Outcome |
|---|---|---|
| Winsorizing | 횡단면 PER 윈저라이징 (`winsorize_row`) | 전처리 파이프라인 구성 (`01_per_preprocessing_sanitized.ipynb`) |
| Model comparison | pooled OLS, industry OLS, XGBoost | 전체 표본 적합 후 모델별 예측 산출 (`02_per_modeling_sanitized.ipynb`) |
| Rolling analysis | 60개월 윈도우 롤링, OLS는 CPU 병렬 / XGBoost는 GPU | 모델별 월간 out-of-sample 예측 행렬 생성 |
| Hypothesis tests | H1/H2/H3, Fama-MacBeth | `03_hypothesis_testing_sanitized.ipynb` |
| Portfolio backtest audit | 저장된 롤링 XGBoost 예측으로 10%/10% 롱숏 재구성, 비용 시나리오 | Gross CAGR 8.30% / Net CAGR 1.71% (2004-05~2025-08), README Headline Results 참조 |

모델별 RMSE/IC 등 비교 수치는 이 저장소에 공개하지 않았습니다. `output_sample/sample_model_comparison.csv`는 합성 toy 데이터입니다.
