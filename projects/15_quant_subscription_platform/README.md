# 15. Quant Subscription Platform

## Summary

퀀트 전략을 사용자가 고르고(종목 수, 시가총액 분위, 리밸런싱일, 롱/숏/롱숏) 성과 지표와 환급 판정을 확인하는 구독형 웹 애플리케이션 프로토타입입니다. 이 폴더에는 웹 앱 전체가 아니라 **핵심 계산 엔진(`code/portfolio_engine.py`)의 공개용 정리본**과 합성 샘플이 들어 있습니다.

## Product Question

퀀트 전략의 백테스트 결과를 일반 사용자가 이해할 수 있는 상품/구독 인터페이스로 표현할 수 있는가?

## What Is Shipped

| Path | Description |
|---|---|
| `code/portfolio_engine.py` | 포트폴리오 엔진 (pandas/numpy만 사용, 네트워크/DB/parquet 접근 없음). 리밸런싱일 계산, 점수 상위/하위 N종목 선정(롱/숏/롱숏, 시총 분위 필터), 일간 수익률 -> NAV, CAGR / MDD / Sharpe / 변동성 / 기간별 수익률, 환급 시뮬레이션, 벤치마크 비교 |
| `code/test_portfolio_engine.py` | 합성 샘플로 엔진을 실행해 롱/숏/롱숏 결과를 점검하는 smoke test |
| `input_sample/` | 합성 가격(6종목, 2025-01-31~06-30, seed 고정 랜덤워크)과 월별 전략 점수 |
| `output_sample/sample_engine_output.json` | 엔진을 합성 샘플에 돌린 결과 (**합성, 연구 결과 아님**) |
| `output_sample/sample_nav_metrics.csv` | 합성 toy 표 (임의 숫자) |
| `notebooks/` | 합성 데모 노트북(실행 출력 포함)과 계산 프로토타입 노트북의 참고용 사본 |

실행:

```bash
cd code
python portfolio_engine.py          # 합성 샘플로 지표 출력
python test_portfolio_engine.py     # smoke test
```

## Engine Behavior (from the code)

- 리밸런싱일: 월별로 `rebalance_day` 이상인 첫 거래일(없으면 월말)
- 종목 선정: 리밸런싱일의 점수 기준 상위 N(롱) / 하위 N(숏), 시가총액 분위 범위로 사전 필터
- 롱/숏은 동일가중. 롱숏은 `롱 일간수익률 평균 - 숏 일간수익률 평균`
- Sharpe: `(CAGR - 3.5%) / 연환산 변동성`(무위험 3.5% 고정). 비용과 슬리피지는 엔진에 없음
- 환급 시뮬레이션: 월/분기/연 단위 구간 수익률이 음수이면 "환급 대상"으로 표시하고, 수익 구간 비율을 확률로 계산. 모델링 예시이며 실제 환급 약속이나 투자 권유가 아님
- 알려진 한계: 성과지표에 승률은 계산하지 않습니다(원본 docstring에는 있었으나 구현 없음). 롱/숏은 구간 내 buy-and-hold 동일가중이고 롱숏만 일간 동일가중 평균 차이라 경로 정의가 다릅니다. 거래비용이 없습니다.

## Architecture (of the original app, not shipped)

| Layer | Stack |
|---|---|
| Frontend | Hono JSX server-rendered pages + static JS, Vite (`package.json`에 React 의존성 없음) |
| API / data | Hono routes on Cloudflare Pages/Workers (D1 및 Supabase 연동 코드), Python FastAPI 계산 서버(Railway), KRX 수집 파이프라인 |
| Deployment | Cloudflare Pages, Wrangler, Railway |

## Trading Relevance

직접적인 알파 연구가 아니라, 리서치 결과를 NAV/지표/환급 판정이 있는 제품 형태로 옮기는 엔지니어링 경험입니다. 엔진 수치(합성 샘플 기준)는 연구 결과가 아니며 성과를 주장하지 않습니다.

## Redaction Notes

원본에서 공개하지 않은 것: 프런트엔드/라우트 코드, 운영 DB 연결 정보와 환경변수, 크롤러 및 데이터 파이프라인, 운영 parquet/CSV 데이터와 시드 SQL, 배포 문서. 엔진은 시크릿이나 DB 접근 코드가 없음을 확인하고 합성 입력용 로더만 남겨 공개했습니다.
