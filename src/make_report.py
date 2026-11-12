"""Author the paper from verified numerical outputs, with an editable MD twin."""
import html
import json
import re
from pathlib import Path
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak, KeepTogether
from .analysis import ROOT, TABLES, FIGURES

TITLE='Education Disparities and National Life Evaluation'
SUBTITLE='Measurement, prosperity adjustment and evidence within countries'


def main():
    r=json.loads((ROOT/'outputs/results.json').read_text())
    panel=json.loads((ROOT/'outputs/panel_results.json').read_text())
    primary=r['primary']; pm=panel['primary']
    cv=pd.read_csv(TABLES/'cv_summary.csv').set_index('model')
    desc=pd.read_csv(TABLES/'descriptive_statistics.csv',index_col=0)
    measure=pd.read_csv(TABLES/'measurement_comparison_same_countries.csv')
    sims=pd.read_csv(TABLES/'simulation_summary.csv')
    selection=pd.read_csv(TABLES/'sample_selection.csv').set_index('variable')
    blocks=[]
    def p(s):blocks.append(('p',s))
    def h(s):blocks.append(('h',s))
    def section(s):blocks.extend([('break',None),('h',s)])
    def table(headers,rows,widths=None):blocks.append(('table',(headers,rows,widths)))
    def fig(name,caption,max_height=3.4):blocks.append(('figure',(name,caption,max_height)))
    def formula(s):blocks.append(('formula',s))
    def f(x,d=3):return f'{x:.{d}f}'
    def ci(x):return f"[{x['ci_low']:.3f}, {x['ci_high']:.3f}]"

    blocks.append(('title',TITLE));blocks.append(('subtitle',SUBTITLE))
    p('Mobin Seyedmohammadi · Independent research draft · 12 November 2026')
    h('Abstract')
    p('This study asks whether socioeconomic disparities in upper-secondary completion contain information about national life evaluation beyond prosperity and average educational attainment. It compares three clearly defined completion-disparity measures, estimates conditional cross-sectional and within-country associations, and evaluates prediction for held-out countries using public education, wellbeing and macroeconomic data.')
    p(f'The primary measure pairs upper-secondary completion in the highest and lowest socioeconomic quintiles within a single survey. In {primary["n"]} recent complete-case countries, its adjusted coefficient is {primary["estimate"]:.3f} life-ladder points per 10 percentage-point larger gap, with interval {ci(primary)}. A longitudinal analysis matches education to subsequent, non-overlapping life-evaluation windows and retains {panel["within_country_periods"]} observations across {panel["within_countries"]} countries. The country- and period-effects estimate is {pm["estimate"]:.3f}, with a country-clustered interval of {ci(pm)}. Adding the gap changes repeated held-out RMSE from {cv.loc["Baseline","rmse_mean"]:.3f} to {cv.loc["Baseline + education gap","rmse_mean"]:.3f}.')
    p("The estimates provide limited evidence of an independent association between the measured completion gap and life evaluation in these observed samples. Absolute and relative measures produce different unconditional patterns, and adding the absolute gap yields little stable predictive gain. These results do not identify causal effects or establish that educational equality has no social value. A schematic simulation illustrates how attainment in a relative measure's denominator can connect it to prosperity.")
    p('Keywords: educational disparities, life evaluation, measurement, panel data, robust inference, predictive validation')
    p('All substantive analyses are exploratory. The study is observational and was not preregistered.')

    section('1. Motivation and contribution')
    p('Educational disparities and the distribution of economic resources are plausible correlates of subjective wellbeing. Yet the question “which inequality matters more?” mixes several distinct tasks. A measure must first represent a defensible concept. A regression must then separate its association from other country attributes. A predictor must finally improve performance on observations that did not determine its fitted parameters. Comparing two unadjusted R-squared values answers only a narrow version of the second task.')
    p('Educational disparity and educational scarcity are different concepts. Countries can have the same national completion rate but different gaps between socioeconomic groups. Absolute and relative gap definitions can also tell different stories when overall completion differs. A study of wellbeing must therefore examine both the definition of disparity and its relationship with prosperity and average attainment.')
    p('The research questions are whether a same-survey socioeconomic completion gap contains additional information about life evaluation, whether the answer depends on the definition of disparity, and whether within-country comparisons and held-out predictions support a similar interpretation. The analysis uses a recent cross section and an unbalanced country panel with education observed before disjoint wellbeing windows. Source records, inclusion decisions and numerical outputs remain inspectable.')
    h('Relationship to existing research')
    p('Research on educational inequality distinguishes attainment, achievement and opportunity. Thomas, Wang and Fan [1] construct inequality measures using schooling attainment. Ferreira and Gignoux [2] show why educational measurement and the population covered by a survey matter, and distinguish achievement dispersion from inequality associated with predetermined circumstances. The present SES completion gaps are narrower than either a full education distribution or a formal opportunity decomposition.')
    p('Oishi, Kesebir and Diener [3], and Oishi and Kesebir [4], examine income inequality and wellbeing in settings that differ from this project’s recent cross section. Their results motivate investigation but cannot validate a coefficient in a different design. The World Happiness Report provides both the life-evaluation source and an established empirical reason to account for prosperity [5]. The OECD/JRC guidance on composite indicators [6] motivates checking choices of normalization, weighting and missing-data treatment. Country-level longitudinal comparisons draw on the distinction between within-unit and between-unit information associated with Mundlak [7].')
    p('The contribution is an integrated empirical study of measurement, conditional association and prediction. It combines transparent survey pairing, dependence-aware inference, a complete sensitivity grid and an explicit comparison of training fit with held-out prediction. The analysis is designed to show both the information these aggregate sources contain and the limits of what they can establish.')

    section('2. Data and population under study')
    table(['Source','Variables used','Role'],[
        ['UNESCO GEM/UIS WIDE [8]','Completion rates, SES quintiles, national totals, survey/year, sample counts','Build same-survey education gaps'],
        ['World Happiness Report 2025 figure data [5]','Cantril Ladder averages and reported intervals','Country life evaluation, not emotional affect'],
        ['World Bank WDI [9]','SI.POV.GINI','Observed income/consumption inequality'],
        ['World Bank WDI [10]','NY.GDP.PCAP.PP.KD','Actual real PPP GDP per person']], [.25,.43,.32])
    p('The WIDE, Gini and happiness data are archived public-source snapshots whose historical extraction dates are unknown. The GDP responses were downloaded on 12 November 2026, with API metadata reporting a last update of 11 November 2026. This is a retrospective analysis using revised macroeconomic data rather than historical real-time forecast inputs. Exact source files, URLs and hashes are bundled. WIDE is stored in losslessly compressed form, with the uncompressed source hash retained in the manifest.')
    p('The WHR workbook is Figure 2.1 data. Its “Year” label identifies the endpoint of a reporting window. Endpoint 2024 represents 2022-2024, rather than an annual 2024 wave. Columns labelled “Explained by” are model contributions. They are not used as raw GDP, social support or other original covariates. Cross-sectional regressions use actual World Bank GDP instead.')
    h('Sample construction')
    table(['Cross-sectional step','Countries'],[
        ['WHR outcome at endpoint 2024',str(r['sample']['happiness_countries'])],
        ['WIDE countries with a valid 2015-2021 paired survey',str(r['sample']['paired_recent_education_countries'])],
        ['WHR countries with an eligible education observation',str(r['sample']['happiness_with_education'])],
        ['Also observed Gini in 2015-2024 and three-year GDP',str(primary['n'])]], [.82,.18])
    p('Country names are reconciled with explicit ISO3 mappings. Fuzzy matching is prohibited. Northern Cyprus and Somaliland are separate outcome sampling territories and are not reassigned to Cyprus or Somalia. At the measurement key, identical point estimates collapse. A country-survey-year is excluded if any required quintile or national completion estimate conflicts. This flags seven ambiguous surveys rather than silently averaging the contradictions. Every exclusion remains in a country or country-period audit.')
    p(f'The observed cross-sectional sample is selective: included countries average {selection.loc["ladder","included_mean"]:.2f} life-ladder points, compared with {selection.loc["ladder","excluded_mean"]:.2f} among excluded outcome countries. Only seven high-income countries enter the cross section. Complete-case analysis exposes this selection; it does not remove it. Estimates therefore refer to the observed sample rather than all countries or the world population.')

    section('3. Measuring socioeconomic educational disparity')
    p('The primary exposure uses WIDE’s upper-secondary completion series `comp_upsec_v2_m`, distinct from its age-20-29 completion series. Within a single country-survey-year, p1 and p5 denote the completion proportions for the lowest and highest socioeconomic quintiles. “Socioeconomic” is deliberate: WIDE’s wealth grouping can derive from assets, income, consumption or other source-specific definitions [8]. It is not a uniform international wealth scale.')
    formula('Absolute gap D = 100(p5 - p1) percentage points; regression exposure = D / 10')
    formula('Relative gap R = (p5 - p1) / [(p5 + p1)/2]')
    p('A 10-point gap between completion rates of 10% and 20% has relative gap 0.667. The same absolute gap between 80% and 90% has relative gap 0.118. Relative disparity emphasizes proportional shortfalls where completion is scarce. Absolute disparity represents unequal percentage-point attainment. Neither measure is universally preferable, and comparing them changes the scientific question.')
    fig('13_measurement_comparison','Figure 1. Each bar uses the same 65 countries and life-evaluation outcome. Large differences in unconditional fit reflect distinct measures, not a change in the compared population.',2.9)
    p('In the cross section, the relative gap correlates -0.944 with national completion. Its denominator connects disparity to educational scarcity. The absolute gap has much weaker correlation with national completion. The five-quintile alternative uses fixed rank scores of 0.1, 0.3, 0.5, 0.7 and 0.9. Target-age-group population shares are unavailable, so this is a descriptive rank gradient rather than a population slope index of inequality.')

    section('4. Empirical design and estimands')
    h('Cross-sectional association')
    formula('L_i = a + b D_i/10 + c log(GDP_i) + d Completion_i/10 + e Gini_i/10 + u_i')
    p('The outcome is 2022-2024 life evaluation. Education is the latest valid 2015-2021 survey. Gini is the most recent actual observation in 2015-2024. GDP is the mean of annual natural logs of real PPP GDP per person across all three outcome years, requiring complete coverage. Each country receives equal regression weight. The coefficient b is a conditional linear association in this observed sample, not the response to an education policy. The same 65 countries enter the nested comparisons.')
    p('HC3 covariance and a t reference with n-k degrees of freedom provide the main cross-sectional intervals [11]. Countries are the resampling units in 2,000 paired bootstrap draws. Partial R-squared compares the residual fit contribution of education with that of Gini after the other model terms. Direct bootstrap differences replace the incorrect practice of comparing two separate intervals. Diagnostics inspect residual shape, leverage, influence and a limited functional-form test without treating non-rejection as proof of assumptions.')
    h('Longitudinal association')
    table(['Prior education survey block','Subsequent life-evaluation window'],[
        ['2010-2012','2013-2015'],['2013-2015','2016-2018'],['2016-2018','2019-2021'],['2019-2021','2022-2024']], [.5,.5])
    formula('L_it = country_i + period_t + b_w D_it/10 + c_w log(GDP_it) + d_w Completion_it/10 + u_it')
    p('Education is 1-3 years before the start of its outcome window, and no education survey appears in more than one period. Countries must contribute at least two complete observations. Country intercepts absorb stable additive differences, and period intercepts absorb a common shift in each outcome block. Inference clusters by country, with CRV1 finite-sample correction and a t reference based on G-1 degrees of freedom [12]. A second 2,000-draw bootstrap resamples entire country histories. These are aggregate associations, not a treatment-based difference-in-differences design.')
    p('The analysis is exploratory and its recorded decisions are not a preregistration. Data-informed choices and internal cross-validation do not provide an untouched external test set. All documented specifications are reported rather than selecting a statistically attractive subset.')

    section('5. Cross-sectional evidence')
    ladder=pd.read_csv(TABLES/'model_ladder.csv')
    table(['Model, same 65 countries','Coefficient','95% HC3 interval','R²'],[
        [a.label, f(a.estimate),f'[{a.ci_low:.3f}, {a.ci_high:.3f}]',f(a.r2)] for _,a in ladder.iterrows()], [.49,.14,.24,.13])
    p('The Gini-only row uses a 10-point Gini increment. All other rows use a 10 percentage-point education-gap increment. Their coefficient magnitudes are therefore not directly comparable. Model R-squared refers to the entire specification, not the fraction of happiness caused by the included inequality measure.')
    fig('03_model_ladder','Figure 2. Education-gap estimates over the model sequence. The confidence intervals use HC3 covariance and t references. Every estimate refers to the same countries.',3.2)
    p(f'The full model estimates {primary["estimate"]:.3f} life-ladder points per 10 pp larger gap, with interval {ci(primary)} and p={primary["p_value"]:.3f}. The education partial R-squared is {r["partial_r2"]["gap10"]:.3f}, compared with {r["partial_r2"]["gini10"]:.3f} for Gini. The paired bootstrap interval for their partial-R-squared difference spans both signs. These results provide no stable basis for ranking education disparity as the stronger independent predictor in this sample.')
    p('The uncertain coefficient does not establish a zero relationship or a positive benefit from disparity. The relative gap has a substantially stronger unconditional association than the absolute gap, but it is also closely connected to overall attainment. The measures capture distinct aspects of educational disparity and should not be treated as interchangeable.')

    section('6. Evidence from changes within countries')
    p(f'The disjoint-window construction yields {panel["all_complete_country_periods"]} complete country-periods across {panel["all_complete_countries"]} countries. Restricting to countries with repeated information retains {panel["within_country_periods"]} observations across {panel["within_countries"]} countries. Thirty contribute two periods, 22 contribute three and 18 contribute all four. This is an unbalanced repeated-country panel. It does not follow the same people over time.')
    panel_models=pd.read_csv(TABLES/'panel_models.csv')
    table(['Specification','Countries / rows','Gap coefficient','95% clustered interval'],[
        [a.model,f'{a.countries} / {a.country_periods}',f(a.estimate),f'[{a.ci_low:.3f}, {a.ci_high:.3f}]'] for _,a in panel_models.iterrows()], [.44,.15,.16,.25])
    p('The five-quintile row uses its own rank-gradient increment. First differences use changes in the 10 pp gap and retain adjacent periods only. Other rows use the absolute gap. Intervals cluster by country with G-1 reference degrees of freedom; the small balanced-panel comparison has only 18 countries and correspondingly fragile large-cluster justification.')
    p(f'The main country- and period-effects estimate is {pm["estimate"]:.3f}, with clustered interval {ci(pm)} and p={pm["p_value"]:.3f}. The country-history bootstrap interval is [{panel["cluster_bootstrap"]["ci_low"]:.3f}, {panel["cluster_bootstrap"]["ci_high"]:.3f}]. Leaving out one country at a time yields coefficients from {panel["leave_one_country_beta_min"]:.3f} to {panel["leave_one_country_beta_max"]:.3f}. These estimates do not reveal a precise negative association between measured disparity changes and later life evaluation.')
    p('Source-stable countries, balanced countries and Gini-complete histories are different selected samples. Estimating with and without Gini on the same 123 observations makes the adjustment comparison interpretable within that selected panel. None of the specifications turns a changing SES completion measure into an exogenous intervention.')

    section('7. Identifying variation and population coverage')
    fig('09_panel_histories','Figure 3. Individual country histories use only observed eligible periods. The education measurement always precedes its matched outcome window. The lines do not represent annual interpolation.',3.5)
    variance=pd.read_csv(TABLES/'panel_identifying_variation.csv')
    labels={'gap10':'Education gap, per 10 pp','log_gdp':'Log real PPP GDP/person','completion10':'Completion, per 10 pp','ladder':'Life evaluation'}
    table(['Variable','Overall SD','Within-country SD','Within share of variance'],[
        [labels[a.variable],f(a.overall_sd),f(a.within_sd),f'{a.within_variance_share*100:.1f}%'] for _,a in variance.iterrows()], [.43,.17,.2,.2])
    p('These quantities describe where information comes from. They are not reliability ratios. Education and prosperity contain much less variation within countries than across them. Fixed effects remove stable differences but can make measurement error more consequential when true changes are small. The panel’s overall R-squared is 0.920 because country intercepts absorb persistent differences; its within R-squared is 0.119. Reporting the former as education’s explanatory contribution would be misleading.')
    p('Requiring prior education and subsequent wellbeing windows also narrows coverage in recent periods. Complete rows decline from 78 in the first outcome window to 37 in the last. Missingness is a characteristic of the source architecture and sampling populations. A balanced-panel restriction changes which countries the analysis describes rather than repairing all selection bias.')

    section('8. Predictive value for held-out countries')
    p('A predictor comparison should evaluate observations outside the estimation fold. The cross-sectional models therefore use five common folds repeated over 20 deterministic partitions. No imputer, scaler or PCA is fitted to the full sample: the primary gap is fixed arithmetic from the source records. All regression parameters are estimated using training countries only. The outcome scale remains the Cantril Ladder.')
    fig('04_prediction','Figure 4. Mean out-of-fold RMSE over 20 repeated five-fold partitions. Labels report complete out-of-fold errors for each repetition before averaging. Split variability is not a sampling confidence interval.',3.6)
    table(['Model','Repeated-CV RMSE','MAE'],[[name,f(cv.loc[name,'rmse_mean']),f(cv.loc[name,'mae_mean'])] for name in ['Mean only','Prosperity','Baseline','Baseline + education gap']], [.55,.25,.2])
    p(f'Adding the education gap to prosperity, attainment and Gini changes RMSE by {r["cv_paired"]["rmse_difference_full_minus_baseline"]:.4f} ladder points on average. It improves the score in {r["cv_paired"]["repeats_full_better"]} of 20 partitions and worsens it in the rest. This supports a practical conclusion of little stable incremental gain in this evaluation, rather than a formal proof of predictive equivalence. Analytic leave-one-out predictions produce the same qualitative comparison. Hold-one-region-out results remain available as a separate transport stress test.')
    p('These predictions address countries represented by the observed sampling process. They are not forecasts for future years. Repeated evaluation on a dataset that also informs research choices can be optimistic, and an external holdout would be required for stronger generalization claims.')

    section('9. Sensitivity, diagnostics and multiplicity')
    sensitivity=pd.read_csv(TABLES/'sensitivity.csv')
    table(['Cross-sectional design check','n','Gap coefficient','95% HC3 interval'],[
        [a.model,str(a.n),f(a.estimate),f'[{a.ci_low:.3f}, {a.ci_high:.3f}]'] for _,a in sensitivity.iterrows()], [.48,.08,.17,.27])
    p('The region-indicator check excludes singleton regions before fitting, because a singleton fixed-effect cell has leverage one and invalidates the usual HC3 residual correction. This removes the sole Oceania country for that check. Excluding Cook-flagged countries is reported as a sensitivity result and never replaces the main sample. Requiring reported Q1 and Q5 sample sizes reduces coverage because counts are missing for some sources; it is not a survey-design correction.')
    p(f'The main cross-sectional diagnostic results are Breusch-Pagan p={r["diagnostics"]["breusch_pagan_lm_p"]:.3f}, an HC3 quadratic RESET check p={r["diagnostics"]["reset_hc3_p"]:.3f}, and maximum VIF={r["diagnostics"]["max_vif"]:.2f}. These tests do not establish homoskedasticity, linearity or exogeneity. HC3 remains the main covariance choice regardless of those diagnostic p-values. The package includes residual plots, influence values and an algebraic check of the added-variable slope.')
    p('The exploratory grid reports all 18 combinations of three education measures, three adjustment sets and two recency samples. Appendix B shows them in design order, with coefficients scaled over each exposure’s interquartile range. Holm-adjusted p-values across that family remain in the tables. This prevents selectively showing an attractive specification, but it does not convert a retrospective analysis into a confirmatory one. Percentile intervals for partial R-squared near its zero boundary are treated as descriptive.')

    section('10. A simulation of denominator coupling')
    p('A schematic experiment isolates a mechanism that is otherwise difficult to see in the empirical comparison. Generate standardized prosperity z, national completion midpoint m=0.2+0.6 logistic(z), and an absolute completion gap d drawn independently from Uniform(0.04,0.16). Set Q1=m-d/2 and Q5=m+d/2. Life evaluation is 5+0.9z plus independent normal noise with standard deviation 0.7. All completion rates remain between zero and one.')
    formula('R = d/m;    life evaluation = 5 + 0.9z + noise;    d independent of z and noise')
    fig('11_measurement_simulation','Figure 5. One thousand replications, each with 150 simulated countries. The event is a negative coefficient with p below 0.05. The real datasets do not determine these simulation parameters.',3.4)
    p('The relative gap has a negative unconditional relationship with life evaluation in every replication, even though the generated absolute disparity is independent of prosperity and outcome noise. Controlling for prosperity removes that systematic detection pattern. The unadjusted relative association is real in this simulated population; calling it a false rejection of zero association would be incorrect. The mistaken step would be interpreting it as an effect of unequal education.')
    p('This experiment does not show that the real data follow this DGP, invalidate relative inequality as a normative concept, or identify the empirical causal mechanism. Its purpose is narrower: demonstrate why normalizing by attainment can connect an inequality measure to development, and why the chosen ruler should be part of the research question.')

    section('11. Limits of the evidence')
    h('Identification and interpretation')
    p('The design does not isolate an intervention. Prosperity, institutions, educational completion and wellbeing may influence one another over long periods. GDP and attainment can be confounders, mediators, outcomes of shared causes or proxies. Their inclusion defines a conditional association rather than uniquely identifying a causal effect. Country effects absorb stable additive attributes but leave time-varying confounders, heterogeneous trends and reverse channels unresolved.')
    h('Measurement and comparability')
    p('WIDE combines instruments and source-specific SES rankings. Same-survey pairing prevents a direct mismatch of Q1 and Q5, but does not harmonize what household status means across countries. Even the same survey name can change definitions across waves. National completion and SES gaps refer to young people, while national life evaluation summarizes adults. The ecological relationship cannot establish how an individual’s education or background changes their wellbeing. Sampling uncertainty from complex household designs is not fully available in these aggregate records. Country bootstraps therefore condition on the observed education estimates.')
    h('Selection, dependence and precision')
    p('Coverage omits many high-income countries and changes across periods. Missingness may depend on relevant outcomes and institutions. Complete-case estimates and balanced-panel checks do not identify the resulting selection bias. Cross-sectional HC3 assumes independence across countries. Country clustering permits within-country dependence but still assumes sufficient independence between countries after modeled terms. Regional shocks can violate that assumption, and four periods provide too little information for an automatic time-cluster solution. The balanced comparison has few country clusters.')
    h('Multiplicity and generalization')
    p('The project began with known original results and evolved after inspection. All estimates are exploratory. The complete specification grid and explicit decision log reduce selective reporting, but cannot erase analytical discretion. Cross-validation reuses the same country pool and does not evaluate an untouched external population. A lack of stable predictive improvement does not establish universal equivalence. Intervals including zero do not prove zero effects, and no post hoc equivalence margin is selected.')
    h('Data vintage')
    p('Original extraction dates remain unknown, while the new GDP snapshot includes retrospective revisions. Disjoint outcome windows prevent overlapping-year averages from mechanically reusing the same calendar years, but observations can still share persistent country shocks. Results describe these frozen inputs and harmonization rules. Updated data or more comparable microdata could change the estimates.')

    section('12. Interpretation and further research')
    p('The recent cross section, country panel and held-out predictions provide limited evidence that the measured absolute completion gap adds independent information about national life evaluation beyond the stated model terms. A five-quintile gradient gives a similar interpretation. Relative disparity has a stronger unconditional association, emphasizing the importance of its connection to overall completion and prosperity.')
    p('The appropriate substantive conclusion is that these aggregate data and designs provide limited evidence for an independent relationship between the measured completion gap and national life evaluation. They do not imply that educational equality is unimportant or justify prioritizing one redistributive policy over another. A wellbeing coefficient is also not a complete valuation of education as a social objective.')
    p('The most useful next investment is stronger measurement. Comparable repeated household or student microdata would permit a stable socioeconomic ranking, correct population weights, survey-design uncertainty and a closer match between educational circumstances and individual outcomes. A causal analysis would additionally need a defensible source of exogenous policy variation, a clearly stated target effect and assumptions that can be investigated. Adding instrumental variables, difference-in-differences or increasingly flexible machine learning without that design would not resolve the central limitations.')
    p('The substantive finding is limited evidence of an independent relationship in these selected aggregate samples, alongside substantial sensitivity of unconditional fit to the definition of disparity. The research contribution is a reproducible integration of clear measurement, temporal matching, clustered inference, paired prediction and a controlled mechanism illustration. Uncertainty, sampling coverage and identification limits remain part of the result.')

    section('References')
    refs=[
      ('1','Thomas, V., Wang, Y., and Fan, X. (2001). Measuring Education Inequality: Gini Coefficients of Education. World Bank Policy Research Working Paper 2525.','https://documents1.worldbank.org/curated/en/361761468761690314/pdf/multi-page.pdf'),
      ('2','Ferreira, F. H. G., and Gignoux, J. (2014). The Measurement of Educational Inequality: Achievement and Opportunity. The World Bank Economic Review 28(2), 210-246. doi:10.1093/wber/lht004.','https://doi.org/10.1093/wber/lht004'),
      ('3','Oishi, S., Kesebir, S., and Diener, E. (2011). Income Inequality and Happiness. Psychological Science 22(9), 1095-1100. doi:10.1177/0956797611417262.','https://journals.sagepub.com/doi/10.1177/0956797611417262'),
      ('4','Oishi, S., and Kesebir, S. (2015). Income Inequality Explains Why Economic Growth Does Not Always Translate to an Increase in Happiness. Psychological Science 26(10), 1630-1638. doi:10.1177/0956797615596713.','https://journals.sagepub.com/doi/10.1177/0956797615596713'),
      ('5','Helliwell, J. F., et al. (eds.) (2025). World Happiness Report 2025. University of Oxford: Wellbeing Research Centre. Chapter 2, Statistical Appendix and Figure 2.1 data.','https://www.worldhappiness.report/ed/2025/'),
      ('6','OECD / European Union / EC-JRC (2008). Handbook on Constructing Composite Indicators: Methodology and User Guide. OECD Publishing. doi:10.1787/9789264043466-en.','https://doi.org/10.1787/9789264043466-en'),
      ('7','Mundlak, Y. (1978). On the Pooling of Time Series and Cross Section Data. Econometrica 46(1), 69-85. doi:10.2307/1913646.','https://www.jstor.org/stable/1913646'),
      ('8','GEM Report and UIS. World Inequality Database on Education (WIDE). Database, indicator definitions and brief data note. Archived snapshot, extraction date unknown. Metadata consulted 12 November 2026.','https://www.education-inequalities.org/about'),
      ('9','World Bank. World Development Indicators, Gini index (SI.POV.GINI). Archived snapshot, extraction date unknown. Indicator metadata consulted 12 November 2026.','https://data.worldbank.org/indicator/SI.POV.GINI'),
      ('10','World Bank. World Development Indicators, GDP per capita, PPP (constant 2021 international dollars), NY.GDP.PCAP.PP.KD. API snapshots downloaded 12 November 2026, last update 11 November 2026.','https://data.worldbank.org/indicator/NY.GDP.PCAP.PP.KD'),
      ('11','statsmodels developers. OLSResults.HC3_se and RegressionResults.get_robustcov_results documentation. Software version 0.15.0. Consulted 12 November 2026.','https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.OLSResults.HC3_se.html'),
      ('12','Cameron, A. C., and Miller, D. L. (2015). A Practitioner’s Guide to Cluster-Robust Inference. Journal of Human Resources 50(2).','https://cameron.econ.ucdavis.edu/research/Cameron_Miller_JHR_2015.pdf'),
      ('13','scikit-learn developers. Common pitfalls and recommended practices, and cross-validation documentation. Software version used: 1.8.0. Consulted 12 November 2026.','https://scikit-learn.org/stable/common_pitfalls.html'),
    ]
    for n,text,url in refs:blocks.append(('reference',(n,text,url)))
    p('Source citation for the supplied WIDE snapshot: Adapted from GEM Report and UIS World Inequality Database on Education (WIDE), https://www.education-inequalities.org. Original extraction date unknown; snapshot archived for this analysis on 12 November 2026. Data-source terms govern the data. No data license is inferred from the project’s code license.')

    section('Appendix A. Estimation and inference details')
    h('Cross-sectional covariance')
    formula('b = (X′X)⁻¹X′y;  h_i = x_i′(X′X)⁻¹x_i')
    formula('V_HC3 = (X′X)⁻¹ [Σ_i x_i x_i′ e_i²/(1-h_i)²] (X′X)⁻¹')
    p('The main cross-sectional interval uses b ± t(0.975,n-k) times the HC3 standard error. The verification script reconstructs the coefficients and covariance from matrix algebra and checks them against the estimation library. The same script checks the Frisch-Waugh-Lovell residualized slope and analytic PRESS errors using explicit omitted-country refits.')
    h('Country-clustered covariance')
    formula('V_CRV1 = [G/(G-1)] [(n-1)/(n-k)] (X′X)⁻¹ [Σ_g s_g s_g′] (X′X)⁻¹')
    formula('s_g = X_g′ e_g;  reference degrees of freedom = G - 1')
    p('Here X includes the intercept and country and period indicators. The included indicators count toward k. The country-cluster covariance and reference degrees of freedom are independently checked. A joint Wald F-test of all country intercepts is omitted because its covariance is rank deficient under country clustering; the substantive slope intervals remain the reported objects.')
    h('Bootstrap and dependence')
    p('Cross-sectional bootstrap draws resample entire country rows. The panel bootstrap draws complete country histories. Country effects are absorbed by within-country demeaning, including the period-indicator columns, and each draw refits the remaining least-squares problem. Repeated appearances of a country are independent copies of its history for resampling purposes. The absorbed estimate is checked against the full indicator regression. Neither bootstrap reconstructs the household-survey sampling design or identifies unobserved education estimates.')
    h('Prediction')
    formula('LOO error_i = OLS residual_i / (1 - leverage_i)')
    p('Each repeated-CV score is calculated from one prediction per country, with every country held out once per repetition. Scores are then averaged across repetitions. The code stores every split, prediction and observed value. The baseline includes log GDP, national completion and Gini. The full predictor adds the education gap. The compared predictors share every fold.')

    section('Appendix B. Complete exploratory specification grid')
    fig('10_specification_grid','Figure B1. All 18 combinations of three measurement choices, three adjustment sets and two recency windows. Primary uses 2015-2021 education surveys; expanded uses 2010-2021. Intervals are individual 95% HC3 intervals, not simultaneous confidence bands. The accompanying CSV includes Holm-adjusted p-values across the entire exploratory family. Exposure IQR scaling aids interpretation on the outcome scale without making the underlying constructs identical.',8.4)

    section('Appendix C. Replication and provenance')
    p('The project runs from frozen inputs without network access. Install the pinned Python dependencies, then run `python reproduce.py` from the project root. It rebuilds cleaned data, measurement comparisons, cross-sectional models, panel models, simulation, verification and this report. The executed notebook provides a guided route through the same material. CSV tables, full bootstrap draws, individual held-out predictions and vector/raster figures are included.')
    table(['Path','Purpose'],[
      ['data/raw/ and data/source_manifest.json','Exact input files, hashes, source URLs and known provenance'],
      ['data/processed/','Survey-level records, country crosswalk, complete samples and exclusion audits'],
      ['src/analysis.py','Cross-sectional pipeline, diagnostics and prediction'],
      ['src/measurement.py','Same-country comparison of three completion-disparity measures'],
      ['src/panel.py','Disjoint-window longitudinal analysis and specification grid'],
      ['src/simulation.py','Schematic measurement experiment'],
      ['src/verify.py','Independent algebra, sampling and data-contract checks'],
      ['docs/research_protocol.md','Research decisions, exploratory status and estimands'],
      ['docs/methods_explained.md','Interpretations and limitations of each method']], [.43,.57])
    p('For each output, provenance begins with the raw source manifest and the deterministic configuration. Run metadata records the Python and package versions and analysis-source hash. Source-specific use terms remain applicable. The code and authored analysis are distinct from the third-party data and referenced papers.')
    p('AI tools assisted with code and writing.')

    # Both outputs derive from the same blocks, preventing numerical drift.
    md=[]
    for kind,value in blocks:
        if kind=='title':md.append('# '+value)
        elif kind=='subtitle':md.append('## '+value)
        elif kind=='h':md.append('## '+value)
        elif kind=='p':md.append(value)
        elif kind=='formula':md.append('`'+value+'`')
        elif kind=='table':
            headers,rows,_=value
            md.append('| '+' | '.join(headers)+' |\n| '+' | '.join('---' for _ in headers)+' |\n'+'\n'.join('| '+' | '.join(str(x) for x in row)+' |' for row in rows))
        elif kind=='figure':
            name,caption,_=value;md.append(f'![{caption}](../outputs/figures/{name}.png)\n\n{caption}')
        elif kind=='reference':
            n,text,url=value;md.append(f'[{n}] {text}'+(f' [Source]({url})' if url else ''))
    (ROOT/'docs/research_paper.md').write_text('\n\n'.join(md)+'\n')
    make_pdf(blocks)
    print(ROOT/'outputs/Education_Disparities_Research_Paper.pdf')


def make_pdf(blocks):
    font_root=ROOT/'assets/fonts'
    for name,file in [('Body','DejaVuSerif.ttf'),('BodyBold','DejaVuSerif-Bold.ttf'),('Sans','DejaVuSans.ttf'),('SansBold','DejaVuSans-Bold.ttf')]:
        pdfmetrics.registerFont(TTFont(name,str(font_root/file)))
    pdfmetrics.registerFontFamily('Body',normal='Body',bold='BodyBold',italic='Body',boldItalic='BodyBold')
    pdfmetrics.registerFontFamily('Sans',normal='Sans',bold='SansBold',italic='Sans',boldItalic='SansBold')
    ink=colors.HexColor('#172C3C');muted=colors.HexColor('#607584');blue=colors.HexColor('#236F9E');pale=colors.HexColor('#EAF0F4')
    styles={
      'p':ParagraphStyle('body',fontName='Body',fontSize=10.1,leading=15.1,textColor=ink,spaceAfter=9,allowWidows=0,allowOrphans=0),
      'h':ParagraphStyle('heading',fontName='SansBold',fontSize=15.2,leading=20,textColor=ink,spaceBefore=9,spaceAfter=14,keepWithNext=True),
      'title':ParagraphStyle('title',fontName='SansBold',fontSize=29,leading=35,textColor=ink,spaceBefore=12,spaceAfter=16),
      'subtitle':ParagraphStyle('subtitle',fontName='Sans',fontSize=14.5,leading=21,textColor=blue,spaceAfter=22),
      'caption':ParagraphStyle('caption',fontName='Sans',fontSize=8.3,leading=11.5,textColor=muted,spaceBefore=6,spaceAfter=13),
      'cell':ParagraphStyle('cell',fontName='Sans',fontSize=8.2,leading=11.7,textColor=ink),
      'headcell':ParagraphStyle('headcell',fontName='SansBold',fontSize=8.2,leading=11.7,textColor=ink),
      'formula':ParagraphStyle('formula',fontName='Sans',fontSize=9.5,leading=14,textColor=blue,spaceBefore=5,spaceAfter=12,leftIndent=10),
      'reference':ParagraphStyle('reference',fontName='Body',fontSize=9.0,leading=13.5,textColor=ink,spaceAfter=13)}
    out=ROOT/'outputs/Education_Disparities_Research_Paper.pdf'
    doc=SimpleDocTemplate(str(out),pagesize=A4,rightMargin=47,leftMargin=47,topMargin=48,bottomMargin=45,
          title=TITLE,author='Mobin Seyedmohammadi',subject=SUBTITLE)
    width=A4[0]-94
    story=[]
    def clean(s):
        # Inline backticks are typographic emphasis in PDF, not hidden code.
        s=html.escape(str(s)).replace('`','')
        return s
    for kind,value in blocks:
        if kind=='break':story.append(PageBreak())
        elif kind in ['p','h','title','subtitle','formula']:
            text=clean(value)
            if kind=='formula':text=re.sub(r'_([A-Za-z0-9]+)',r'<sub>\1</sub>',text)
            story.append(Paragraph(text,styles[kind]))
        elif kind=='table':
            headers,rows,weights=value
            weights=weights or [1/len(headers)]*len(headers)
            cells=[[Paragraph(clean(s),styles['headcell']) for s in headers]]+[
                   [Paragraph(clean(s),styles['cell']) for s in row] for row in rows]
            t=Table(cells,colWidths=[width*x for x in weights],repeatRows=1,hAlign='LEFT')
            t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),pale),('VALIGN',(0,0),(-1,-1),'TOP'),
                ('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),
                ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),
                ('LINEBELOW',(0,0),(-1,0),.7,blue),('LINEBELOW',(0,1),(-1,-1),.3,colors.HexColor('#D6E0E6'))]))
            story.extend([t,Spacer(1,12)])
        elif kind=='figure':
            name,caption,maxheight=value
            image=Image(str(FIGURES/(name+'.png')))
            scale=min(width/image.imageWidth,maxheight*72/image.imageHeight)
            image.drawWidth=image.imageWidth*scale;image.drawHeight=image.imageHeight*scale
            story.append(KeepTogether([image,Paragraph(clean(caption),styles['caption'])]))
        elif kind=='reference':
            n,text,url=value
            link=(' <link href="'+html.escape(url,quote=True)+'" color="#236F9E">Source</link>') if url else ''
            story.append(Paragraph('['+n+'] '+clean(text)+link,styles['reference']))
    def page(canvas,doc):
        canvas.setStrokeColor(colors.HexColor('#CBD9E2'));canvas.setLineWidth(.5)
        canvas.line(47, A4[1]-31,A4[0]-47,A4[1]-31)
        canvas.setFont('Sans',7.1);canvas.setFillColor(muted)
        canvas.drawString(47,A4[1]-24,'EDUCATION DISPARITIES AND NATIONAL LIFE EVALUATION')
        canvas.drawString(47,25,'Independent research draft · 12 November 2026')
        canvas.drawRightString(A4[0]-47,25,str(doc.page))
    doc.build(story,onFirstPage=page,onLaterPages=page)


if __name__=='__main__':main()
