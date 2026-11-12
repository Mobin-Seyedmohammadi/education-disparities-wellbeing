# Methods and interpretation

## What the research can answer

The project asks whether measured socioeconomic disparities in completing upper secondary school contain information about national life evaluation. It separates three tasks: measuring disparity, estimating conditional relationships, and evaluating held-out predictions. A strong result in one task does not automatically resolve the others.

## Why there are multiple disparity measures

If completion is 10% in Q1 and 20% in Q5, the absolute gap is 10 percentage points and the relative gap is 0.10/0.15 = 0.667. If completion is 80% and 90%, the absolute gap remains 10 points but the relative gap becomes 0.10/0.85 = 0.118. Relative disparity emphasizes shortfalls when average attainment is low. Absolute disparity counts unequal percentage-point attainment. Neither is universally correct. They answer different questions.

A signed gap preserves the direction of the SES gradient. Applying an absolute value would hide reversals. The all-five-quintile alternative regresses the five completion rates on equally spaced rank scores. It uses additional information, but the unavailable target-age-group shares prevent interpreting it as the standard population slope index of inequality.

WIDE's "wealth" groups are source-specific SES rankings. Current household income and assets can partly reflect educational achievement. These groups are not uniformly predetermined circumstances, and this project does not estimate a formal inequality-of-opportunity decomposition.

## Why national attainment matters

Two equally unequal countries can have very different attainment levels. Bounded completion rates also constrain possible gap sizes near 0% or 100%. Reporting the gap alongside total completion separates disparities from educational scarcity. Adjusting for total completion defines a conditional association, rather than a total effect of educational redistribution. The quadratic-completion check addresses a simple form of the floor/ceiling relationship.

## Why use logarithmic PPP GDP

Purchasing power parity adjusts for different price levels, making real income levels more comparable. A logarithm allows an equal proportional increase in GDP per person to have the same modeled increment in life evaluation. The code averages annual log GDP over each outcome window. It never uses WHR's "Explained by GDP" column as raw income. The new GDP snapshot contains retrospective revisions, so this is not an evaluation of forecasts available in those historical years.

## OLS, HC3 and the coefficient

For the cross section, the education coefficient describes the difference in mean life evaluation associated with a 10 percentage-point larger Q5-Q1 completion gap, holding the model's prosperity, national attainment and Gini controls fixed. It does not describe what would happen if a government changed the gap by 10 points.

OLS minimizes the sum of squared residuals. HC3 keeps those coefficients but estimates their covariance using residuals divided by 1 minus leverage. This reduces the undue precision that can arise from unusual predictor combinations. The t reference is a finite-sample approximation, not a guarantee of exact coverage. Cross-country independence and a suitable conditional mean remain working assumptions.

The added-variable plot removes the controls from both the gap and outcome. Its slope equals the gap coefficient in the full OLS model by the Frisch-Waugh-Lovell identity. The plotted residuals do not provide a new set of independent observations or an alternative causal identification strategy.

## Partial R-squared and paired bootstraps

The education partial R-squared is `(SSE_without_education - SSE_full) / SSE_without_education`. It asks what fraction of the baseline model's remaining squared error the education gap removes in sample. Gini's partial R-squared uses the model dropping Gini instead. Their difference measures incremental fit, not causal importance, social welfare or policy returns.

Each country-bootstrap draw resamples the same countries for both quantities and refits the models. This directly represents uncertainty in their paired comparison. Overlap of two separate intervals is not the corresponding test. Partial R-squared is bounded below by zero and its percentile bootstrap can behave poorly near that boundary. In particular, a positive bootstrap lower endpoint is not evidence of a nonzero population contribution.

## Cross-validation and prediction

The code fits each model using four folds and predicts the remaining fold, cycling through every country. It repeats this with 20 reproducible partitions. Every comparison uses identical splits, so differences are paired. Lower RMSE means lower typical squared prediction error in ladder points. MAE is less sensitive to a few large errors. Out-of-fold R-squared may be negative because an estimated model can predict worse than an overall-mean benchmark.

Repeat-to-repeat standard deviation describes sensitivity to partitioning the same sample. It is not the sampling standard error of predictive performance. The leave-one-out calculation refits the OLS prediction implicitly using the PRESS identity `error_i = residual_i/(1-leverage_i)`, and explicit refits verify that identity. Holding out a region tests a harder transport problem separately. None of these is an untouched external validation sample.

## Country and period fixed effects

The panel includes one observation for a country in each available disjoint three-year outcome window. A country intercept absorbs every stable country attribute represented additively: persistent cultural differences, geography and long-run institutions, whether measured or not. A period intercept absorbs a shift common to countries in that outcome block. The education coefficient uses departures from a country's own pattern after the other modeled terms.

This is a repeated-country aggregate panel, not a panel of the same people. The young people represented by successive education surveys differ, as do the adults answering the life-evaluation surveys. Source changes, time-varying confounders and errors in the gap remain. Temporal ordering prevents using a later education measurement to explain an earlier outcome window, but it does not establish exogeneity.

Country-clustered standard errors permit serially correlated errors within a country. CRV1 uses a finite-sample covariance multiplier and a t reference with G-1 degrees of freedom. Different countries can still share correlated shocks beyond a common period effect. Four periods are too few to justify treating a time-cluster correction as automatically reliable. Country bootstrapping resamples whole observed histories and retains their missing-period pattern. Neither procedure propagates all sampling uncertainty from the underlying household surveys.

The within R-squared compares remaining error to outcome variation around country means. The much larger overall R-squared includes explanatory power from country intercepts. It should not be presented as the amount of happiness "explained by educational inequality."

## Why the source-stable and balanced checks matter

If the survey changes from an asset ranking to an income ranking, a change in the measured gap may partly reflect measurement rather than educational change. Restricting to countries using the same survey name addresses some of this problem, although definitions can still change within a named survey. Requiring all four periods changes the observed population and reduces precision. Those checks therefore show sensitivity rather than an automatically superior estimate.

The Gini panel check estimates with and without Gini on the same selected rows. A coefficient change between the full panel and Gini-restricted panel could come from selection, adjustment or both. The matched comparison isolates the adjustment component within the selected panel.

## Why simulation is included

The schematic simulation deliberately generates life evaluation from prosperity, with an absolute completion gap independent of prosperity and the outcome noise. Overall completion rises with prosperity. Dividing the independent gap by completion then induces a negative association between relative disparity and life evaluation. That unconditional relative association is real in this simulated population. Calling it a causal education effect would be the error. The experiment illustrates a possible mechanism rather than proving that it generated the real data.

## What a null or uncertain estimate means

A confidence interval including zero does not prove an effect is zero. It describes an estimated association that is not distinguished from zero under the stated model and inference assumptions. Equivalence would require an a priori substantively meaningful margin and a dedicated analysis. This project does not choose such a margin after seeing the estimates.

The sound conclusion is about the evidence in these specific source snapshots and samples. It does not say that educational equality is unimportant, that inequality has no causal effect on wellbeing, or that income redistribution is the preferable policy.
