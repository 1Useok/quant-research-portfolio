# Timeline

| Stage | Description | Where |
|---|---|---|
| 1. Raw data | 엑셀 시트 병렬 로딩 | 노트북 "Raw Data" |
| 2. Preprocessing | 금융업/단기 이력 종목 제외 | 노트북 "전처리" |
| 3. Feature engineering | RM12, EXRET12, TVOL, TSKEW 등 | 노트북 "변수 엔지니어링" |
| 4. Labeling | 6개월 +-35% crash/jump | 노트북 "폭락정의" |
| 5. Modeling | SMOTE + MNLogit, in-sample 후 expanding-window | 노트북 "모델 학습" |
| 6. Portfolio | 확률 십분위, SIZE 통제 | 노트북 "포트폴리오 구성" |
