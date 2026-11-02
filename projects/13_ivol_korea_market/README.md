# 13. Idiosyncratic Volatility In Korea Market

## Summary

한국 주식시장에서 idiosyncratic volatility(고유변동성) 이상현상을 검증한 프로젝트입니다. Carhart 4팩터 잔차의 60개월 롤링 표준편차를 ivol 신호로 만들고, 분위/저변동 20종목 포트폴리오와 유동성 기반 거래비용 가정을 적용해 성과를 평가했습니다.

학회 세션(Advanced Backtesting, Robustness Test) 과제로 시작했고, 팩터 산출부터 포트폴리오 구성, 성과 평가, 강건성 점검까지 전 과정을 직접 수행했습니다. 공개 노트북 3종은 단계별 노트북(팩터 산출, 포트폴리오 구성, 성과 평가)을 정리한 사본이며, 이후 클린 커널 재실행과 수치 대조(재현성 점검)를 거쳤습니다.

## Research Question

한국 시장에서도 고유변동성이 높은 종목이 낮은 미래 수익률을 보이는가? 거래비용과 유동성 필터를 적용해도 결과가 유지되는가?

## Headline Results

모두 전체 기간 단일 백테스트(in-sample, 별도 hold-out 없음)이며 샘플 선택과 파라미터는 같은 구간에서 정해졌습니다. 로컬 원본 데이터에서 계산한 값이고 이 저장소의 노트북으로는 재현되지 않습니다(유료 데이터 필요).

| # | Setup | Period | Costs | Result |
|---|---|---|---|---|
| 1 | 5분위 단일정렬, 월간 (재현성 점검용 노트북) | 1996-07 ~ 2025-08 (350개월) | 없음 (gross) | 연환산 기하수익률 Q1(저 ivol) 17.10%, Q5(고 ivol) -3.25%; Q1-Q5 11.83% |
| 2 | 저 ivol 20종목 동일가중 롱 + 거래대금 하위 10% 제외 | 2000-01 ~ 2025-08 (308개월) | 순수익 (비유동 상위 20% 80bp / 나머지 30bp) | CAGR 15.9%, 연 변동성 16.3%, Sharpe(rf=0) 0.99, MDD -27.3% |
| 3 | 저 ivol 20종목 롱(동일가중)과 고 ivol 20종목 숏(시총가중)의 50:50 | 2000-01 ~ 2025-08 (308개월) | 없음 (gross) | CAGR 27.1%, 연 변동성 15.8%, Sharpe 1.61, MDD -35.9%; Carhart 4팩터 월 알파 1.47% (HAC 12, p < 1e-13) |

- 출처: #1, #3은 재현성 점검 보고서(`reproducibility_check/REPORT.md`, 2026-08-26, 클린 커널 재실행)의 값이고, #2는 포트폴리오 구성 단계의 저장된 `portfolio.csv`(309행, 월간)에서 성과 지표 정의대로 다시 계산한 값입니다.
- #3은 숏 레그에 비용과 대차 제약이 없으므로 실제 수익률이 아닙니다. #2와 #3은 서로 다른 구성이라 직접 비교하면 안 됩니다.
- 알려진 불일치: (a) 두 노트북이 서로 다른 `ivol` 파일을 씁니다(공통 유효값 중 518개가 다르고 최대 차이 0.094). (b) 성과 평가 노트북에 남아 있던 이전 실행 출력(CAGR 27.5%, 변동성 37.1%, MDD -82.1%)은 현재 `portfolio.csv`로 계산한 값(#2)과 달라서 사용하지 않았습니다. 어떤 설정의 출력인지 확인하지 못했습니다.

## Data And Signal

| Item | Description |
|---|---|
| Returns | 월간/일간 한국 주식 수익률 (현금배당 반영 수정주가 기반 총수익률) |
| Factors | KOSPI, SMB, HML, MOM, RF 월간 팩터 |
| Liquidity | 60일 평균 거래대금, Amihud 비유동성 (abs(일간수익률) / 거래대금) |
| Signal | Carhart 4팩터 회귀 잔차의 60개월 롤링 표준편차 |

## Methodology

1. 종목별 월간 초과수익률을 Carhart 4팩터에 60개월 롤링 회귀 후 잔차 표준편차를 ivol로 사용
2. 월말 리밸런싱, 거래대금 하위 10% 제외 후 ivol 하위 20종목 동일가중 선정
3. 수익률 상하위 1% 윈저라이징
4. 거래비용: Amihud 상위 20% 종목 80bp, 나머지 30bp (매매 금액 기준)
5. 성과 평가: CAGR, 변동성, Sharpe, MDD, 회전율, Carhart 회귀

## Notes On The Public Notebooks

- 이 노트북들은 참고용 사본이며(비공개 데이터 필요), 경로를 `./input/`, `./output/` 기준의 중립 경로로 바꿨습니다.
- `02_portfolio_formation_sanitized.ipynb`의 리밸런싱 날짜는 원본에서 `resample('QE')`(분기)로 남아 있었으나 저장된 결과(`portfolio.csv`)는 월간이어서 `'ME'`로 고쳤습니다.
- Amihud 상위 20% 기준(`illiq.quantile(0.8)`)은 원본에서도 맞게 되어 있습니다. 다만 거래대금 필터와 Amihud 기준이 같은 변수명 `threshold`를 재사용하고 있어(로직 오류는 아님) 공개 노트북에서는 `tv_threshold`, `illiq_threshold`로 분리했습니다. 거래대금 분위(0.1)와 비유동성 분위(0.8)를 혼동한 버전은 이 소스 폴더에서 찾지 못했습니다.
- 위 헤드라인 수치는 원본 실행에서 나온 것이며, 수정된 공개 노트북을 데이터로 다시 돌려 검증한 것은 아닙니다.

## Project Artifacts

| Path | Role |
|---|---|
| `notebooks/00_public_sample_workflow.ipynb` | 합성 샘플로 실행되는 잔차 변동성 데모 (출력 포함) |
| `notebooks/01_factor_construction_sanitized.ipynb` | ivol 산출 (참고용 사본) |
| `notebooks/02_portfolio_formation_sanitized.ipynb` | 포트폴리오 구성/비용 (참고용 사본) |
| `notebooks/03_performance_evaluation_sanitized.ipynb` | 성과 평가 (참고용 사본) |
| `input_sample/`, `output_sample/` | 합성 toy 데이터와 표 |
| 비공개 원본 | Robustness Test 노트북, `ivol.csv`, 가격/시총/거래대금 원자료, 재현성 점검 산출물 |

## Trading Relevance

고전적 팩터 이상현상을 한국 시장에 맞게 재현하고, 거래비용과 유동성 필터를 반영해 검증한 경험입니다. 성과는 같은 표본에서 파라미터를 정한 in-sample 값이므로 전략 성과 주장이 아니라 연구 방법의 예시로 읽어야 합니다.

## Redaction Notes

원본에서 공개하지 않은 것: 원본 zip/xlsx, 가격/시총/거래대금 원자료, `ivol.csv`, Robustness Test 노트북, 재현성 점검 산출물.
