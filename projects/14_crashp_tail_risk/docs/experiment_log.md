# Experiment Log

| Experiment | Attempt | Outcome |
|---|---|---|
| Tail label | 6개월 선행 로그수익률 +-35% (crash=-1, jump=+1) | 노트북의 `폭락정의` 섹션. 원본에는 24주/35%, 12개월/70% 설정의 출력도 있었으나 공개 노트북은 6개월/35% |
| Feature engineering | RM12, EXRET12, TVOL, TSKEW 외 7개 | `input_sample/feature_dictionary.md` |
| Imbalanced modeling | SMOTE + 다항 로짓 | 학습 구간(~2020-01) pseudo R-squared 0.0756 |
| Out-of-sample probabilities | 매월 expanding-window 재적합, +7개월 시점 예측 | crash/jump 확률 행렬 생성 |
| Decile sort | 전월 확률 십분위 동일가중 | D1 +17.0% / D10 -22.0% CAGR gross (2005-10~2025-01), README 참조 |
| Universe split | KOSPI/KOSPI200 한정 출력 | 비공개 원본에만 있음 |
