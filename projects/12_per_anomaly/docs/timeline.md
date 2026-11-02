# Timeline

| Stage | Description | Where |
|---|---|---|
| 1. Preprocessing | PER winsorizing and variable preprocessing | `notebooks/01_per_preprocessing_sanitized.ipynb` |
| 2. Modeling | pooled/industry OLS and XGBoost, 60개월 rolling prediction | `notebooks/02_per_modeling_sanitized.ipynb` |
| 3. Hypothesis tests | H1, H2, H3, Fama-MacBeth, portfolio | `notebooks/03_hypothesis_testing_sanitized.ipynb` |
| 4. Paper | 적정 PE를 XGBoost로 추정한 논문 작성 | 비공개 |
| 5. Backtest audit | 저장된 예측으로 롱숏 전략 재구성, 비용/알파 감쇠 검증 (2026-09) | README Headline Results |
