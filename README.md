# Education Disparities and National Life Evaluation

**Measurement, prosperity adjustment and evidence within countries**  
Mobin Seyedmohammadi · Independent empirical research · 12 November 2026

Do socioeconomic gaps in upper-secondary completion contain information about national life evaluation beyond prosperity, overall completion and income inequality? This study examines the question through cross-sectional association, repeated-country comparisons and prediction for held-out countries.

It uses public UNESCO GEM/UIS WIDE, World Happiness Report and World Bank data. All analyses are exploratory and observational. The estimates do not identify causal policy effects.

## Main findings

| Analysis | Result | Interpretation |
|---|---|---|
| Cross section, 65 countries | +0.054 ladder points per 10 pp larger completion gap; 95% HC3 interval [-0.040, 0.148] | An uncertain conditional association |
| Country panel, 198 observations across 70 countries | +0.008; country-clustered 95% interval [-0.103, 0.119] | No precise independent relationship in the observed histories |
| Measurement comparison on the same 65 countries | Unadjusted R²: relative gap 0.414, absolute gap 0.009, rank gradient 0.003 | Disparity definitions capture different information about attainment |
| Held-out country prediction | Baseline RMSE 0.685; adding the gap 0.688 | Little stable incremental predictive gain in this evaluation |

The evidence is limited and imprecise. It does not establish zero effects or show that educational equality lacks social value. Coverage, measurement and identification limitations remain central to interpretation.

## Read the study

- [Research paper](outputs/Education_Disparities_Research_Paper.pdf)
- [Executed notebook](notebooks/education_disparities_research.ipynb)
- [Seminar slides](presentation/Education_Disparities_Seminar.pptx)
- [Editable manuscript](docs/research_paper.md)
- [Research protocol](docs/research_protocol.md)
- [Methods explained](docs/methods_explained.md)
- [Data dictionary](docs/data_dictionary.md)

## Reproduce the analysis

Use Python 3.12. All required data are bundled; estimation and report generation require no data download or credentials.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python reproduce.py
```

On Windows, activate with `.venv\Scripts\activate`.

To rebuild and execute the notebook:

```bash
python -m src.make_notebook --execute
```

For environments that restrict local kernel sockets:

```bash
python -m src.make_notebook --execute --executor inprocess
```

The paper uses the licensed fonts bundled in `assets/fonts/`. The scientific pipeline uses standard Python packages and does not require any private authoring runtime.

## Research design

The primary exposure is the signed difference in upper-secondary completion between the highest and lowest socioeconomic quintiles, observed in the same country, survey and year. It is scaled per 10 percentage points. Relative gaps and a five-quintile rank gradient provide alternative measures. These measure attainment disparities, not test-score achievement or a formal decomposition of educational opportunity.

The recent cross section uses life evaluation in 2022–2024, education surveys from 2015–2021, observed Gini data from 2015–2024 and real PPP GDP per person. The full model includes the gap, log GDP, national completion and Gini.

The panel matches prior education blocks to disjoint three-year wellbeing windows: 2010–2012 education to 2013–2015 wellbeing, followed by three further blocks through 2022–2024. Country and period effects, country-clustered inference and a country-history bootstrap support the longitudinal comparison.

The study reports 18 exploratory specifications, sensitivity to source coverage and model choices, two empirical bootstraps of 2,000 replications each, paired cross-validation and a separate schematic simulation. The simulation illustrates a possible measurement mechanism; it is not a fitted model of the actual countries.

## Data and reproducibility

| Path | Contents |
|---|---|
| `config.json` | Analysis windows, estimand, seeds and resampling settings |
| `data/raw/` | Frozen source snapshots, with WIDE stored as lossless gzip |
| `data/source_manifest.json` | Source URLs, known provenance, sizes and hashes |
| `data/processed/` | Same-survey records, country crosswalk, samples and exclusion audits |
| `src/analysis.py` | Cross-sectional data management, estimation, diagnostics and prediction |
| `src/measurement.py` | Same-country comparison of three disparity measures |
| `src/panel.py` | Longitudinal models, clustered inference and specification grid |
| `src/simulation.py` | Schematic denominator-coupling experiment |
| `src/verify.py` | Independent algebra, source-window and split checks |
| `outputs/tables/` | Coefficients, resampling draws, predictions and diagnostics |
| `outputs/figures/` | Scientific figures in PNG and vector PDF |

Joins use ISO codes with explicit aliases. Conflicting required survey values invalidate a survey and remain logged. The main analysis uses no education or Gini imputation. Reported sample counts are metadata, not survey-design weights. Source extraction dates are unknown for the archived WIDE, Gini and WHR snapshots. The GDP responses were downloaded on 12 November 2026 and contain retrospective revisions.

`python -m src.verify` independently reconstructs HC3 and country-clustered covariance, checks analytic leave-one-out predictions against explicit refits, audits prediction splits and survey windows, and checks the documented specification family. Computational verification does not establish exogeneity or worldwide representativeness.

## Limitations

The samples are selective and SES definitions vary by source. Country effects remove stable additive differences but do not solve changing confounders, measurement error or the mismatch between young people's education and adults' wellbeing. Aggregate records do not provide complete household-survey sampling uncertainty. Cross-validation describes held-out countries from this observed pool, not future years or an external population.

## Sources and rights

- [UNESCO GEM/UIS WIDE](https://www.education-inequalities.org/about)
- [World Happiness Report 2025](https://www.worldhappiness.report/ed/2025/)
- [World Bank Gini](https://data.worldbank.org/indicator/SI.POV.GINI)
- [World Bank real PPP GDP per person](https://data.worldbank.org/indicator/NY.GDP.PCAP.PP.KD)

The MIT license covers the project code and authored text, subject to third-party rights. Source datasets and referenced papers retain their own terms. The data manifest and paper provide detailed attribution.

## Acknowledgment

AI tools assisted with code and writing.
