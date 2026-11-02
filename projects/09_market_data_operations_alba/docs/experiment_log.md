# Experiment Log

| Experiment | Attempt | Outcome |
|---|---|---|
| KRX failure handling | KRX universe 실패 시 KIS 배치 skip | 잘못된 universe로 수집하는 것을 방지 |
| KIS rate limit | 과도한 병렬화 제거 | API 제한에 맞춘 수집 구조 |
| Futures validation | pcap comparison | 100% 일치 (팀 검증 메모 기준, 미재현) |
| Options validation | pcap comparison | 부동소수점 수준 차이 (팀 검증 메모 기준) |
| Stock validation | OHLC and volume check | OHLC 약 97%, volume 약 92% (팀 검증 메모 기준) |
| Test suite | DAG and helper tests | logical date, output validation 테스트 존재 (원본 저장소) |
