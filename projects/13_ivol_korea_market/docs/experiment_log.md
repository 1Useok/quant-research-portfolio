# Experiment Log

| Experiment | Attempt | Outcome |
|---|---|---|
| Factor model | Carhart 4팩터 60개월 롤링 회귀 잔차 표준편차 | ivol 행렬 생성 (전체 재계산 시 저장본과 최대 오차 4e-16로 일치) |
| Portfolio formation | 월말 리밸런싱, 저 ivol 20종목 동일가중 | 순수익 CAGR 15.9%, Sharpe 0.99, MDD -27.3% (2000-01~2025-08) |
| Liquidity filter | 60일 평균 거래대금 하위 10% 제외 | 포트폴리오 구성 노트북에 반영 |
| Transaction costs | Amihud 상위 20% 80bp / 나머지 30bp | 순수익 계산에 반영 |
| Quintile check | 5분위 단일정렬(gross) | Q1 17.10% / Q5 -3.25% (1996-07~2025-08) |
| Reproducibility check | 클린 커널 재실행, 수치 대조 (2026-08) | 성과/회귀 재현. 단 한 노트북은 셀 실행 순서에 의존하고, 두 노트북의 ivol 파일이 달라 결과를 서로 섞으면 안 됨 |
| Public cleanup | 경로 중립화, 리밸런싱 주기 QE를 ME로, threshold 변수명 분리 | 공개 노트북 3종 |

Robustness Test 노트북은 공개하지 않았습니다.
