# Analysis data dictionary

The full raw WIDE schema remains in the bundled source file. This dictionary describes the processed scientific variables and auditing fields. No processed sample substitutes WHR model contributions for raw regressors.

| Variable | Meaning | Unit / constraint |
|---|---|---|
| `iso_code` | ISO3 country code, with explicit `XKX` alias for Kosovo where relevant | Join key; unique in cross section |
| `country` | WHR country display label | Human-readable label, not a join key |
| `survey` | Selected WIDE source name | Source-specific instrument |
| `education_year` | Selected education survey year | Cross section 2015–2021; panel prior block |
| `Quintile 1` … `Quintile 5` | WIDE upper-secondary completion rate for each source-specific SES group | Proportion, 0–1 |
| `Total` | National completion estimate from the same survey | Proportion, 0–1; not an unweighted average of quintile rates |
| `gap_pp` | `100 × (Q5 − Q1)` | Signed percentage-point gap |
| `gap10` | `gap_pp / 10` | Regression increment of 10 pp |
| `completion_pp` | `100 × Total` | National completion percentage |
| `completion10` | `10 × Total` | Regression increment of 10 pp |
| `relative_gap` | `(Q5 − Q1) / ((Q5 + Q1)/2)` | Dimensionless; undefined when denominator is zero |
| `quintile_gradient_pp` | Slope of five completion proportions on fixed SES rank scores, multiplied by 100 | Descriptive rank gradient, not population SII |
| `gradient10` | Rank gradient divided by 10 | Alternative exposure scale |
| `q1_n`, `q5_n` | Reported sample count for boundary groups, when available | Missing for some surveys; not design weights or effective sample sizes |
| `sex_gap_pp` | Male minus female completion from the selected survey, when unambiguous | Descriptive backup; signed pp |
| `location_gap_pp` | Urban minus rural completion from the selected survey, when unambiguous | Descriptive backup; signed pp |
| `ladder` | Country average Cantril Ladder life evaluation | 0–10; three-year reporting window |
| `lowerwhisker`, `upperwhisker` | WHR's reported lower/upper interval bounds | Used to document outcome uncertainty |
| `ladder_se_approx` | Interval width divided by `2 × 1.96` | Approximate outcome SE; not model residual variance |
| `log_gdp` | Mean annual natural log real PPP GDP per person over the outcome window | Constant 2021 international dollars before logging |
| `gdp_years` | Count of observed GDP years in that window | Required to equal 3 |
| `gdp_ppp_mean` | Arithmetic GDP/person mean in the cross section | Descriptive, distinct from mean log |
| `gini` | Latest eligible actual Gini observation | 0–100; income or consumption source definition |
| `gini10` | `gini / 10` | Regression increment of 10 Gini points |
| `gini_year` | Selected Gini source year | Cross section 2015–2024; panel within outcome block |
| `region_group`, `income_group` | WIDE snapshot country metadata | Descriptive snapshot labels, not time-varying historical classifications |
| `endpoint` | Panel outcome window's final year | 2015, 2018, 2021 or 2024 |
| `outcome_start` | Panel endpoint minus 2 | Start of disjoint wellbeing window |
| `education_lag` | Outcome start minus education year | Required 1–3 years in panel |
| `country_periods` | Available complete observations in the core panel construction | 1–4 before restricting to repeated countries |
| `eligible_for_within` | At least two complete observations for a country | Does not imply a balanced panel |
| `included`, `complete` | All required observed variables present under the relevant design | Inclusion flags, no imputation |
| `exclusion_reasons` | One or more missing-source conditions | Reasons can overlap |

Boundary-group count flags do not propagate full survey variance. A survey's national total need not equal the simple average of its SES-group completion rates, since the target-age-group population shares can differ from household quintile shares. That is why the code uses the source national total rather than reconstructing it.
