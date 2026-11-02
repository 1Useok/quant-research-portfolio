# Notebook Map

| Notebook | Status |
|---|---|
| `00_public_sample_workflow.ipynb` | 합성 샘플(`../input_sample`)로 실행되며, 저장된 실행 출력을 포함합니다. |
| `01_factor_construction_sanitized.ipynb` | 참고용 사본. `./input/excess_return.csv`, `./input/factors_monthly.csv`가 필요합니다. |
| `02_portfolio_formation_sanitized.ipynb` | 참고용 사본. `./input/`의 가격/ivol/시총/거래대금 CSV 6개가 필요합니다. 리밸런싱 주기와 변수명을 수정했습니다(README 참조). |
| `03_performance_evaluation_sanitized.ipynb` | 참고용 사본. `./input/portfolio.csv`, `./input/factors_monthly.csv`가 필요합니다. |

원본은 학회 세션의 단계별 폴더 구조였고, 공개본은 경로를 중립 경로로 바꿨습니다. 단계 간 파일(`ivol.csv`, `portfolio.csv`)은 다음 노트북의 `./input/`으로 복사해야 합니다. 원본에서 공개하지 않은 것: Robustness Test 노트북, 초기 포트폴리오 노트북, 데이터 전처리 노트북.
