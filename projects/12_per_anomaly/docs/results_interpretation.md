# Results Interpretation

이 프로젝트는 실제 PER과 모델이 추정한 적정 PER의 괴리를 valuation signal로 바꾸는 연구입니다. 핵심은 "PER이 낮다"가 아니라 "기업 특성으로 설명되는 적정 PER 대비 얼마나 싸거나 비싼가"입니다.

## Reported Result (private data, not reproducible here)

- 2004-05 ~ 2025-08, 월말 리밸런싱, 상/하위 10% 동일가중 롱숏.
- Gross: CAGR 8.30%, Sharpe 0.58, MDD -35.08%, Carhart 월 알파 0.96% (HAC t=3.55).
- Net (거래 20bp + 연 2% 차입비용): CAGR 1.71%, Sharpe 0.19, MDD -52.45%, 월 알파 0.44% (t=1.62).
- 예측치는 60개월 롤링 XGBoost의 다음 달 out-of-sample 값이지만, 전략 백테스트는 전체 기간 단일 구간이며 별도 hold-out은 없습니다.

즉, 비용 전 신호는 유의하지만 비용을 반영하면 경제적 유의성이 크게 약해진다는 것이 결론입니다. 하위 기간별 편차(2010-2014 gross CAGR 2.8% 등)도 큽니다.

## Files To Look At

- `notebooks/00_public_sample_workflow.ipynb`: 합성 데이터로 per_gap 신호를 계산하는 실행 가능 데모
- `notebooks/01~03_*_sanitized.ipynb`: 실제 전처리/모델링/검정 코드 (비공개 데이터 필요)
- `input_sample/`, `output_sample/`: 합성 toy 데이터. 수치에 연구적 의미 없음
