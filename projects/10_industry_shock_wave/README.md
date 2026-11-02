# 10. Industry Shock Wave

## Summary

한국은행 산업연관표, DataGuide 기업 데이터, OpenDART 공시 텍스트를 결합해 산업 충격이 기업 위험으로 전파되는 경로를 정량화해 본 **PoC(개념 검증)** 프로젝트입니다. 결과는 "네트워크 정보를 더하면 예측이 좋아진다"가 아니라 그 반대였고, 그 한계를 확인한 기록입니다.

## Why It Matters For Trading

뉴스와 테마 매매에서는 특정 이벤트가 어느 산업과 기업으로 전파되는지 빠르게 판단해야 합니다. 이 프로젝트는 산업연관표와 기업 공급망 대용 변수로 테마 충격을 구조화하려는 시도입니다.

## Components

| Component | Role |
|---|---|
| BOK input-output table | direct and indirect industry exposure |
| DataGuide firm data | firm financials, returns, industry mapping |
| OpenDART text | evidence for firm-level supplier/customer links (429 evidence edges) |
| Risk model | vulnerability, market signal, network signal |
| Evaluation | next-quarter distress proxy AUC and top-decile lift |

## Key Evidence

평가 표본은 33,184 firm-quarter이며 base event rate(다음 분기 distress proxy)는 0.2583입니다. 점수를 학습하는 train/test 분할 없이 전체 표본에 적용한 평가이므로 in-sample 성격이며, 수익률이 아닌 분류 지표(AUC)입니다.

| Metric | Result |
|---|---:|
| Direct oil exposure x oil shock | coef -0.000084, t=-0.07 |
| Indirect oil exposure x oil shock | coef 0.001199, t=0.87 |
| Financial score AUC | 0.6750 |
| Multilayer model without firm network AUC | 0.6079 |
| + static (synthetic) firm network AUC | 0.5993 |
| + dynamic supplier network AUC | 0.5880 |
| Industry exposure score alone AUC | 0.4863 |
| Static / dynamic network score alone AUC | 0.4639 / 0.4806 |
| Financial score top-decile event rate | 0.6101 (base 0.2583) |
| Firm network edges (synthetic) | 296,200 |
| Buyer firms / Supplier firms | 1,640 / 349 |
| Industry pairs | 522 |

## Interpretation

- 단순 산업연관표 기반 석유 노출 회귀는 유의하지 않았습니다.
- 재무 취약도 점수 단독(AUC 0.675)이 가장 좋았고, 여기에 시장·네트워크 레이어를 더한 다층 모델은 오히려 AUC가 낮아졌습니다(0.675 -> 0.608 -> 0.599 -> 0.588).
- 산업 노출 점수와 네트워크 점수 단독 AUC는 0.5 미만(0.46~0.49)으로, 이 데이터에서는 예측력이 없었습니다.
- 기업 네트워크는 실제 거래 관계가 아니라 산업연관표 계수를 기업 매출·규모로 쪼갠 추정(synthetic) 네트워크입니다. 따라서 네트워크 레이어는 예측 성능 향상이 아니라 숨은 노출 설명과 시나리오 액션 도출을 위한 구조로 해석해야 하며, production 모델이 아니라 PoC입니다.

## Public Sample And Code

| File | Description |
|---|---|
| `code/public_risk_model_skeleton.py` | 합성 샘플 exposure + risk scoring (`python public_risk_model_skeleton.py`) |
| `input_sample/` | 합성 산업연관표, firm panel |
| `output_sample/risk_model_summary.md` | 위 표의 집계 결과 요약 |
| `output_sample/sample_risk_tiers.csv` | 합성 risk tier 예시 |
| `notebooks/00_public_sample_workflow.ipynb` | 합성 샘플 workflow (실행 결과 저장) |

## 원본에서 공개하지 않은 것

OpenDART API 키, DataGuide 원천 데이터, 기업 단위 상세 표, 외부 제안서 자료, 전체 pipeline 코드.
