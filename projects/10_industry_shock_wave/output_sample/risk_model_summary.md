# Industry Shock Wave Evidence

## Empirical Check

| Test | Coef | t-stat |
|---|---:|---:|
| Direct oil exposure x oil shock | -0.000084 | -0.07 |
| Indirect oil exposure x oil shock | 0.001199 | 0.87 |

The simple oil exposure regression was not significant. Adding network layers lowered AUC (0.675 -> 0.588), and the industry-exposure and network scores alone are below 0.5. The firm network is an estimated (synthetic) network, not observed transactions, so this is a PoC. Evaluation: 33,184 firm-quarters, full sample, in-sample.

## Distress Proxy Evaluation

| Model | AUC |
|---|---:|
| Financial score | 0.6750 |
| Multilayer without firm network | 0.6079 |
| Multilayer + static (synthetic) network | 0.5993 |
| Multilayer + dynamic supplier network | 0.5880 |
| Industry exposure score alone | 0.4863 |

## Network Construction

| Metric | Count |
|---|---:|
| Firm network edges | 296,200 |
| Buyer firms | 1,640 |
| Supplier firms | 349 |
| Industry pairs | 522 |
| OpenDART evidence edges | 429 |
| Evidence buyers | 159 |

