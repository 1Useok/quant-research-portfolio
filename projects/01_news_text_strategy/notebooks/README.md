# Notebook Map

| Notebook | 내용 | 실행 가능 여부 |
|---|---|---|
| `00_public_sample_workflow.ipynb` | `../input_sample/`의 합성 이벤트·분 수익률을 읽어 오프셋별 평균 수익률을 출력. 출력이 저장돼 있음 | 가능 (pandas) |
| `01_intraday_path_by_nb_quintile_sanitized.ipynb` | NB 점수 분위별 뉴스 전후 장중 가격 경로 | 참고용 사본, 비공개 데이터 필요 |
| `02_sentiment_scoring_sanitized.ipynb` | SESTM·NB 감성 점수 산출 | 참고용 사본, 비공개 데이터 필요 |
| `03_portfolio_capacity_and_costs_sanitized.ipynb` | 경매 거래대금 용량, 수수료·세금·슬리피지, 분 단위 참여율 체결 백테스트 | 참고용 사본, 비공개 데이터 필요 |

`*_sanitized` 노트북 3개는 원 연구 노트북에서 출력, 실행 횟수, 로컬 경로, 키 값을 제거한 사본이다. 뉴스 원문 토큰(`news_tokenized_labeled*.pkl`)과 일별·분봉·경매 가격(parquet)이 있어야 실행되며, 이 저장소만으로는 실행되지 않는다. 한국어 주석은 UTF-8이며 정상이다.
