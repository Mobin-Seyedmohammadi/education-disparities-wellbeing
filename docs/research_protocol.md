# Research protocol and scope

This independent empirical study examines socioeconomic gaps in secondary-school completion, national life evaluation, and the sensitivity of their relationship to measurement and adjustment choices. The paper and replication package are the principal outputs.

## Research questions

1. Do directly interpretable socioeconomic completion gaps contain information about national life evaluation beyond prosperity, overall completion and the Gini index?
2. Does the answer differ between absolute and relative definitions of educational disparity?
3. Do changes within countries, using education measured before disjoint happiness windows, support a similar association?
4. Does a measured disparity improve prediction for held-out countries?

The contribution is an empirical measurement and robustness study connecting these questions. It does not introduce a new causal estimator, identify an education-policy effect, or establish the optimal allocation of social spending.

## Status of the design

All substantive analyses are exploratory. The documented protocol records data-informed design choices rather than a preregistration. Neither prospective confirmation nor an untouched external test set is claimed.

## Measurement decisions

- Use one outcome: country mean Cantril life evaluation. Avoid treating it as a measure of every aspect of happiness or emotional experience.
- Use the WIDE `comp_upsec_v2_m` series: completion among young people 3-5 years older than the official upper-secondary graduation age. Do not mix this with the separate age-20-29 completion series.
- Compare Q5 and Q1 in the same country, survey and year. WIDE calls the grouping variable wealth, but its underlying socioeconomic ranking can derive from assets, income, consumption or other source-specific measures. Use "socioeconomic" as the general term.
- Primary exposure: signed Q5-Q1 completion gap, in percentage points, scaled per 10 pp for regression. A negative value, if observed, remains negative.
- Retain all five quintiles and the national total in a valid survey, allowing an all-five-quintile rank-gradient sensitivity check on the same observations.
- Alternative measures change the estimand. Relative gap divides by mean completion in the two boundary groups. The five-quintile rank slope uses fixed rank scores 0.1, 0.3, 0.5, 0.7 and 0.9. Since target-age-group shares are unavailable, this slope is not described as a population slope index of inequality.

## Source and joining rules

The exact input bytes are frozen in `data/raw`, with SHA-256 hashes, URLs and provenance notes in `data/source_manifest.json`. The three original data snapshots have unknown historical extraction dates. New GDP data were downloaded on 12 November 2026 and reflect later statistical revisions. Historical models therefore describe retrospective relationships rather than real-time forecast performance.

Join by ISO3 codes. Resolve naming changes explicitly. Do not use fuzzy country-name joins. Do not merge northern Cyprus with Cyprus or Somaliland with Somalia. Log those separate sampling territories as exclusions.

At each country-survey-year-group key, collapse identical point estimates. Exclude an entire survey if any required completion estimate conflicts. For equal point estimates with differing reported sample sizes, retain the smallest reported size for conservative sample-size flagging. Report these ambiguities rather than average them away.

Select the latest eligible survey, breaking same-year ties with DHS, then MICS, then alphabetical survey names. This is an explicit reproducibility convention, not a claim that one instrument is uniformly superior. Check source stability in the panel analysis. Do not fill missing education or Gini values with global averages.

## Cross-sectional design

The outcome window is 2022-2023. Education surveys span 2015-2021. The GDP control is the mean of annual natural logs of real PPP GDP per person in 2022-2024, requiring all three years. Gini is the most recent observed value in 2015-2023. Record the source year and test stricter recency rules. The working estimand is an equal-country conditional linear association in the observed sample, rather than a population-weighted individual effect.

The primary specification is `ladder ~ gap10 + log_gdp + completion10 + gini10`. Compare the nested specifications on the same complete-case countries. Use HC3 heteroskedasticity-robust covariance and a t reference with n-k degrees of freedom. This does not protect against dependence between countries or misspecified conditional means.

Bootstrap countries jointly 2,000 times, recomputing coefficients and both predictors' partial R-squared. Compare partial R-squareds through their paired difference rather than overlap of separate confidence intervals. Percentile intervals for nonnegative partial R-squareds near zero are descriptive and are not valid evidence that a population contribution differs from zero.

Use paired five-fold cross-validation repeated 20 times, and analytic leave-one-out OLS predictions. All compared models receive identical splits. The primary exposure uses fixed arithmetic and no learned imputer, scaler or PCA. Training-only fitting therefore contains every estimated transformation. Split-to-split variability is not a sampling confidence interval. Holding out countries assesses interpolation to countries represented by this sampling process, not future years or arbitrary geographic transport. Hold-one-region-out results are a separate stress test.

## Longitudinal analysis

Use non-overlapping outcome windows 2013-2015, 2016-2018, 2019-2021 and 2022-2023. For each, select one survey from the immediately preceding disjoint education block: 2010-2012, 2013-2015, 2016-2018 or 2019-2021. Education is therefore 1-3 years before the start of its matched outcome window, and no education survey is reused across periods.

Retain countries with at least two complete country-period observations. Fit country and period indicators, log real PPP GDP per person and national completion alongside the education gap. Report country-clustered CRV1 standard errors with finite-sample covariance correction and a t reference based on the number of countries minus one. Bootstrap complete country histories 2,000 times. Show identifying within-country variation, balanced-panel coverage, source-stable countries, adjacent-period first differences and leave-one-country-out estimates.

Add Gini only as a secondary panel specification, with and without its control estimated on precisely the same Gini-complete country-period rows. This distinguishes changes caused by adjustment from changes caused by sample selection.

Country effects address stable country-level differences. Period effects absorb common period shifts. Neither addresses changing confounders, reverse channels, heterogeneous survey definitions, sampling error in education, or the ecological mismatch between young people's schooling and adults' life evaluations. These models are not difference-in-differences estimates of a treatment, and temporal ordering is not causal identification.

## Sensitivity and multiplicity

Report the entire documented specification grid, not a preferred statistically significant subset. Express grid coefficients over each exposure's interquartile range while retaining the original units in the tables. A common outcome scale makes plot magnitudes readable but does not make distinct inequality concepts interchangeable. Report Holm adjustments across the 18 exploratory cross-sectional grid tests. Use confidence intervals and effect sizes as the main evidence. Do not interpret failure to reject zero as proof of equivalence.

## Acknowledgment

AI tools assisted with code and writing.
