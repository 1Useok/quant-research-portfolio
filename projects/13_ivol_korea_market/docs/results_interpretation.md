# Results Interpretation

이 프로젝트는 한국 시장에서 idiosyncratic volatility 이상현상을 검증하고, 거래비용과 유동성 조건을 반영합니다. 학회 세션 과제로 시작해 분석 전 과정을 직접 수행했습니다.

## Reported Results (private data, not reproducible here)

- 5분위 단일정렬 gross (1996-07~2025-08): 저 ivol 17.10%, 고 ivol -3.25%, 저-고 11.83%.
- 저 ivol 20종목 롱, 비용 반영 (2000-01~2025-08): CAGR 15.9%, 변동성 16.3%, Sharpe 0.99, MDD -27.3%.
- 롱숏 gross (동일 기간): CAGR 27.1%, Sharpe 1.61, MDD -35.9%, Carhart 월 알파 1.47%.

전부 in-sample 전체 기간 수치입니다. 롱숏 수치는 숏 비용/제약이 없습니다.

## Caveats

- 노트북 간 ivol 입력 파일이 달라(518개 값 차이) 수치를 섞을 수 없습니다.
- 성과 평가 노트북에 남은 이전 실행 출력은 현재 입력과 맞지 않아 사용하지 않았습니다.
- 공개 포트폴리오 노트북은 리밸런싱 주기를 QE에서 ME로, 변수명 threshold를 분리하는 수정을 했습니다. 수정 후 재실행은 데이터가 없어 하지 못했습니다.

## Files To Look At

- `output_sample/sample_portfolio_summary.csv`: 합성 toy 표 (연구 결과 아님)
- `notebooks/01~03_*_sanitized.ipynb`: 참고용 사본
