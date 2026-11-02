# Results Interpretation

이 프로젝트는 산업 충격이 기업 위험으로 전파되는 경로를 구조화한 PoC이며, 예측 성능 측면의 성과는 제한적이었습니다.

## What To Look At

- `output_sample/risk_model_summary.md`: 집계 결과 요약
- `output_sample/sample_risk_tiers.csv`: 합성 risk-tier 출력 예시
- `code/public_risk_model_skeleton.py`: exposure와 risk scoring 축소 예시

## Interpretation

- 산업연관표 exposure만으로는 설명력이 없었습니다(산업 노출 점수 AUC 0.486, 석유 노출 회귀 비유의).
- 재무 취약도 점수 단독이 가장 좋았고(AUC 0.675, top-decile event rate 0.610 vs base 0.258), 네트워크를 더한 모델은 더 나빠졌습니다(0.588).
- 네트워크는 실제 거래망이 아닌 추정 네트워크입니다. 실제 거래망 데이터와 신용 이벤트 데이터로 보정하기 전까지는 예측 모델이 아니라 설명·시나리오 도구로 읽어야 합니다.
- 모든 평가는 33,184 firm-quarter 전체 표본에 적용한 값(in-sample 성격)입니다.
