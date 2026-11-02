# Code

별도 `.py` 모듈은 공개하지 않았습니다. 구현은 `../notebooks/01_crash_quarterly_sanitized.ipynb`에 있습니다.

| Section in notebook | Contents |
|---|---|
| 변수 엔지니어링 | RM12, EXRET12, TVOL, TSKEW, SIZE, DTURN, AGE, TANG, SALESG, DRETAIL, CAIPG |
| 폭락정의 | 6개월 선행 로그수익률 +-35% 라벨 |
| 모델 학습 (In-Sample / Out of Sample) | SMOTE + MNLogit, 병렬 expanding-window 예측 |
| 포트폴리오 구성 | 확률 십분위 정렬, SIZE 통제, KOSPI 비교 플롯 |
