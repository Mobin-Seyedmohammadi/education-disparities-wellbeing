"""Build the guided notebook; add --execute for a clean executed copy."""
import argparse
import traceback
from pathlib import Path
import nbformat as nbf
from nbclient import NotebookClient
from .analysis import ROOT


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--execute',action='store_true')
    parser.add_argument('--executor',choices=['jupyter','inprocess'],default='jupyter');args=parser.parse_args()
    cells=[]
    def md(s):cells.append(nbf.v4.new_markdown_cell(s))
    def code(s):cells.append(nbf.v4.new_code_cell(s))
    md('''# Education Disparities and National Life Evaluation
## Measurement, prosperity adjustment and evidence within countries

**Mobin Seyedmohammadi — independent research study, 12 November 2026**

This study examines socioeconomic disparities in secondary-school completion and their association with national life evaluation using a recent cross section and a repeated-country panel.

AI tools assisted with code and writing. This notebook is exploratory and is not a preregistered analysis.

The paper and notebook distinguish measurement, conditional association and prediction. The complete raw-data snapshots are bundled, so no additional download is necessary.''')
    md('''## 1. A reproducible starting point

Install `requirements.txt` in a Python 3.12 environment. Run this notebook from its directory or the project root. The first cell identifies the root and rebuilds all scientific outputs when `RUN_FULL_PIPELINE=True`. No network requests occur. For a quick reading of the supplied outputs, change that flag to `False`.

The scientific functions live in inspectable modules under `src/`. This prevents the paper, notebook and command-line workflow from drifting into different analyses.''')
    code('''from pathlib import Path
import os, sys, json, runpy

PROJECT = Path.cwd()
if not (PROJECT / 'src').is_dir():
    PROJECT = PROJECT.parent
assert (PROJECT / 'src/analysis.py').is_file(), 'Open this notebook inside the project folder.'
os.chdir(PROJECT)
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))

RUN_FULL_PIPELINE = True
if RUN_FULL_PIPELINE:
    for module in ['src.analysis', 'src.measurement', 'src.panel', 'src.simulation', 'src.verify', 'src.make_report']:
        print('Rebuilding', module)
        runpy.run_module(module, run_name='__main__')
print('Project:', PROJECT)''')
    code('''import numpy as np
import pandas as pd
import statsmodels.api as sm
from IPython.display import display, Image, Markdown
from src.analysis import FULL, BASE, fit, verify_inputs
from src.panel import panel_fit

T = PROJECT / 'outputs/tables'
P = PROJECT / 'data/processed'
F = PROJECT / 'outputs/figures'
d = pd.read_csv(P / 'analysis_primary.csv')
panel = pd.read_csv(P / 'panel_within_sample.csv')
results = json.loads((PROJECT / 'outputs/results.json').read_text())
panel_results = json.loads((PROJECT / 'outputs/panel_results.json').read_text())
def show(name, width=950):
    display(Image(filename=str(F / (name + '.png')), width=width))
def table(name):
    return pd.read_csv(T / name)
display(pd.Series(results['sample'], name='Count'))''')
    md('''## 2. Source provenance and data management

The original WIDE, Gini and happiness snapshots have unknown historical extraction dates. New real PPP GDP observations were downloaded on 12 November 2026 and contain later revisions. We describe historical relationships retrospectively, rather than forecasting with vintage information.

Country joins use ISO3 codes and explicit aliases. Conflicting completion estimates at a country-survey-year-group key invalidate the entire survey. Identical point estimates collapse. All five SES quintiles and a national total must exist in a selected survey. Each analysis country has exactly one selected observation per eligible period.''')
    code('''manifest = verify_inputs()
display(pd.DataFrame(manifest['files'])[['path', 'bytes', 'provider', 'provenance_note']])
display(table('excluded_ambiguous_surveys.csv'))
display(pd.read_csv(P / 'country_crosswalk.csv').head(12))''')
    code('''audit = pd.read_csv(P / 'country_audit_primary.csv')
display(audit[['iso_code', 'country', 'education_year', 'gini_year', 'included', 'exclusion_reasons']].head(20))
display(table('sample_selection.csv'))
display(table('coverage_by_income_group.csv'))''')
    md('''## 3. What does educational inequality mean here?

The absolute gap is `100 × (Q5 − Q1)` percentage points. The relative gap is `(Q5 − Q1) / ((Q5 + Q1)/2)`. The same absolute difference receives a different relative score when the groups have a different overall attainment level.

Neither is a universal definition of educational inequality. The selected WIDE column measures a specific upper-secondary completion cohort, and its SES groups are source-specific rankings. They are not uniformly predetermined circumstances. We therefore avoid calling this a formal inequality-of-opportunity estimate.''')
    code('''example = pd.DataFrame({'Q1': [.10, .80], 'Q5': [.20, .90]})
example['absolute_gap_pp'] = 100 * (example.Q5 - example.Q1)
example['relative_gap'] = (example.Q5 - example.Q1) / ((example.Q5 + example.Q1) / 2)
display(example)
assert np.allclose(d.gap10, (d['Quintile 5'] - d['Quintile 1']) * 10)
display(d[['gap10', 'relative_gap', 'completion10', 'log_gdp', 'ladder']].corr().round(3))
show('13_measurement_comparison')''')
    md('''## 4. The recent cross section

Every nested comparison uses the same complete-case countries. The full specification includes the 10 pp education gap, log real PPP GDP/person, 10 pp national completion, and 10-point Gini. HC3 covariance with a t reference addresses heteroskedasticity and leverage under a working model. It does not solve omitted variables, dependence between countries or causal identification.''')
    code('''m = fit(d, FULL)
display(table('model_ladder.csv'))
display(pd.DataFrame({'coefficient': m.params, 'HC3_SE': m.bse, 'p': m.pvalues}).join(m.conf_int().rename(columns={0:'CI_low', 1:'CI_high'})))
show('03_model_ladder')''')
    md('''## 5. The added-variable identity and diagnostic evidence

Residualize both the education gap and life evaluation on the same controls. The residual-on-residual slope equals the education coefficient in the full regression. This is an algebraic identity, not a new identification strategy.

Model checks and influence diagnostics remain visible even when their outcomes look reassuring. Country deletion is a sensitivity exercise, not a method of selecting an attractive result.''')
    code('''controls = sm.add_constant(d[BASE], has_constant='add')
gap_resid = sm.OLS(d.gap10, controls).fit().resid
life_resid = sm.OLS(d.ladder, controls).fit().resid
fwl_slope = np.dot(gap_resid, life_resid) / np.dot(gap_resid, gap_resid)
assert np.isclose(fwl_slope, m.params.gap10, atol=1e-10)
print('FWL slope:', fwl_slope)
display(pd.Series(results['diagnostics']))
show('02_raw_and_adjusted')
show('06_diagnostics')''')
    md('''## 6. A repeated-country design without overlapping outcome windows

The longitudinal analysis matches education in 2010–2012 to life evaluation in 2013–2015, then advances both disjoint blocks by three years. Education precedes the start of its outcome window by 1–3 years. No survey is reused across periods. Country effects absorb stable additive country attributes, and period effects absorb common shifts.

These are repeated aggregate country observations. They do not follow the same individuals, and temporal ordering does not turn the education gap into an exogenous treatment.''')
    code('''display(table('panel_sample_flow.csv'))
display(table('panel_coverage.csv'))
assert not panel.duplicated(['iso_code', 'endpoint']).any()
assert not panel.duplicated(['iso_code', 'survey', 'education_year']).any()
assert panel.education_lag.between(1, 3).all()
display(panel[['iso_code', 'country', 'endpoint', 'education_year', 'survey', 'education_lag']].head(18))''')
    code('''pm = panel_fit(panel)
display(table('panel_models.csv'))
display(table('panel_all_main_coefficients.csv'))
print('Inference reference degrees of freedom:', pm.df_resid_inference)
show('08_panel_estimates')''')
    md('''## 7. What variation supports the panel estimate?

Country effects remove persistent between-country differences. The resulting estimate depends on changes within observed histories, which contain much less variation and can be more sensitive to measurement error. The overall R² includes country intercepts and should not be interpreted as education's contribution.

Source-stable and balanced histories change the represented sample. The small balanced comparison has few country clusters. With and without Gini, the selected panel comparison uses exactly the same observations.''')
    code('''display(table('panel_identifying_variation.csv'))
display(table('panel_within_between.csv'))
display(pd.Series(panel_results))
show('09_panel_histories')''')
    md('''## 8. Incremental fit and paired resampling

Partial R² is the fraction of a reduced model's remaining squared error removed by a predictor. The two predictor contributions must be compared using the same resampled countries. Separate confidence-interval overlap is not the paired comparison.

Partial R² is bounded below by zero. Percentile bootstrap limits near that boundary are descriptive and must not be read as proof of nonzero population contribution. Panel resampling uses whole country histories. Neither empirical bootstrap reconstructs the original complex household-survey uncertainty.''')
    code('''display(table('partial_r2.csv'))
display(table('country_bootstrap_summary.csv'))
print('Country-history bootstrap:', panel_results['cluster_bootstrap'])''')
    md('''## 9. Prediction for held-out countries

All compared models share identical five-fold splits, repeated 20 times. The gap uses fixed arithmetic, so no learned preprocessing has leaked across folds. Scores describe interpolation to countries represented by this selected sample. They are not forecasts of future wellbeing or an untouched external validation.

Split-to-split variation describes re-partitioning the same observations. It is not a sampling confidence interval.''')
    code('''display(table('cv_summary.csv'))
display(table('loocv.csv'))
print(results['cv_paired'])
show('04_prediction')''')
    code('''predictions = table('cv_predictions.csv')
assert predictions.groupby(['repeat', 'iso_code']).fold.nunique().eq(1).all()
display(predictions.head(15))
display(table('region_transport.csv'))''')
    md('''## 10. The complete specification grid

Three measurements × three adjustment sets × two recency samples produce 18 exploratory specifications. All are reported in design order. Coefficients are shown over each exposure's IQR to share a readable outcome scale; the underlying constructs remain different. Holm-adjusted p-values account for this documented test family without retrospectively making the study confirmatory.''')
    code('''display(table('sensitivity.csv'))
display(table('specification_grid.csv'))
show('10_specification_grid', width=950)''')
    md('''## 11. A separate, schematic simulation

Generate prosperity z, completion midpoint `m = 0.2 + 0.6 logistic(z)`, and an independent absolute gap `d ~ Uniform(0.04, 0.16)`. Generate life evaluation as `5 + 0.9z + noise`. Relative disparity is `d/m`.

The relative measure can then have a strong negative unconditional association even though absolute disparity has no generated causal path to wellbeing. That unconditional association is real in this simulated population, not a statistical false positive for zero association. The experiment illustrates denominator coupling and the danger of a causal reading. Its parameters are not fitted to the real data.''')
    code('''display(table('simulation_summary.csv'))
display(json.loads((PROJECT / 'outputs/simulation_design.json').read_text()))
show('11_measurement_simulation')''')
    md('''## 12. Scientific verification

The verification script independently reconstructs the HC3 and country-cluster covariance matrices, checks PRESS against explicit refits, audits all country splits and survey windows and checks same-country measurement comparisons. Passing these checks establishes computational consistency under the implemented design, not truth of the identifying assumptions.''')
    code('''runpy.run_module('src.verify', run_name='__main__')
display(json.loads((PROJECT / 'outputs/verification.json').read_text()))''')
    md('''## 13. What the evidence supports

The absolute completion gap has little stable incremental predictive value in the observed recent sample. Absolute and relative measures capture different information about attainment levels. The longitudinal estimates are also imprecise around zero.

This does not prove that educational equality lacks a causal effect or social value. Gaps are measured imperfectly, selection is substantial, household-survey uncertainty is incomplete, and time-varying confounding remains. A causal analysis requires a new design with defensible policy variation or comparable microdata, rather than simply adding an estimator.

Read the full paper in `outputs/Education_Disparities_Research_Paper.pdf`, the editable manuscript in `docs/research_paper.md`, the decision log in `docs/research_protocol.md`, and the detailed methods guide in `docs/methods_explained.md`. All third-party data retain their source terms.''')
    nb=nbf.v4.new_notebook(cells=cells,metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},
          'language_info':{'name':'python','version':'3.12'}})
    destination=ROOT/'notebooks/education_disparities_research.ipynb'
    if args.execute:
        if args.executor=='jupyter':
            client=NotebookClient(nb,timeout=600,kernel_name='python3',resources={'metadata':{'path':str(ROOT)}})
            client.execute()
        else:
            # Execute the real cells sequentially in IPython without opening TCP
            # sockets. This is useful in containers with restricted networking.
            from IPython.core.interactiveshell import InteractiveShell
            from IPython.utils.capture import capture_output
            shell=InteractiveShell.instance();count=0
            for cell in nb.cells:
                if cell.cell_type!='code':continue
                count+=1;print(f'Executing cell {count}',flush=True)
                with capture_output(stdout=True,stderr=True,display=True) as captured:
                    result=shell.run_cell(cell.source,store_history=True,silent=False)
                if result.error_before_exec or result.error_in_exec:
                    raise RuntimeError(f'Notebook execution failed in cell {count}: {result.error_before_exec or result.error_in_exec}')
                cell.execution_count=count;cell.outputs=[]
                if captured.stdout:cell.outputs.append(nbf.v4.new_output('stream',name='stdout',text=captured.stdout))
                if captured.stderr:cell.outputs.append(nbf.v4.new_output('stream',name='stderr',text=captured.stderr))
                for output in captured.outputs:
                    cell.outputs.append(nbf.v4.new_output('display_data',data=output.data,metadata=output.metadata))
            nb.metadata['execution_method']='Actual sequential IPython in-process execution, with captured stdout/stderr and rich display outputs. No fabricated outputs.'
    nbf.write(nb,destination)
    print(destination)


if __name__=='__main__':main()
