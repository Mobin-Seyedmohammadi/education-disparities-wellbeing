"""Longitudinal analysis with disjoint outcome and prior-education windows.

Country effects remove stable country differences. Neither time ordering nor
fixed effects identify a causal effect in these observational repeated surveys.
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests
from .analysis import (ROOT, RAW, PROCESSED, TABLES, FIGURES, CFG, C,
                       country_code, latest_education, write_json, save_figure, fit)

VARS = ["gap10", "log_gdp", "completion10"]


def build_panel():
    surveys = pd.read_csv(PROCESSED / "all_valid_education_surveys.csv")
    h = pd.read_excel(RAW / "happiness2025.xlsx")
    rows = []; unmapped = []; flows = []
    gr = pd.read_csv(RAW / "GINI.csv", skiprows=4)
    for endpoint in CFG["panel_outcome_endpoints"]:
        edu = latest_education(surveys, endpoint-5, endpoint-3)
        hh = h[h.Year.eq(endpoint)].copy()
        iso = []
        for name in hh["Country name"]:
            # Do not conflate northern Cyprus with Cyprus, or Somaliland with
            # Somalia: their outcome sampling populations are not interchangeable.
            if name in ["North Cyprus", "Somaliland Region"]:
                iso.append(None); unmapped.append({"endpoint": endpoint, "name": name,
                    "reason": "Separate survey territory, no equivalent WIDE/World Bank ISO unit"})
            else: iso.append(country_code(name)[0])
        hh["iso_code"] = iso
        hh = hh.dropna(subset=["iso_code"]).rename(columns={"Country name": "country", "Ladder score": "ladder"})
        assert hh.iso_code.is_unique
        p = hh[["iso_code", "country", "ladder"]].merge(edu.drop(columns="country"), on="iso_code", how="left", validate="one_to_one")
        filename = "gdp_ppp_2022_2024.json" if endpoint==2024 else f"gdp_panel_{endpoint-2}_{endpoint}.json"
        source = json.loads((RAW / filename).read_text())
        assert source[0]["pages"] == 1
        raw_gdp = pd.DataFrame([{"iso_code": r["countryiso3code"], "gdp": r["value"], "year": int(r["date"])} for r in source[1]])
        raw_gdp = raw_gdp.dropna(subset=["gdp"])
        raw_gdp = raw_gdp[raw_gdp.gdp > 0]
        raw_gdp["log_gdp"] = np.log(raw_gdp.gdp)
        gdp = raw_gdp.groupby("iso_code", as_index=False).agg(log_gdp=("log_gdp", "mean"), gdp_years=("year", "nunique"))
        gdp = gdp[gdp.gdp_years == 3]
        p = p.merge(gdp, on="iso_code", how="left", validate="one_to_one")
        # Gini is optional in panel analysis, to avoid imposing especially sparse
        # survey coverage on the entire repeated-country design.
        cols = [str(y) for y in range(endpoint-2, endpoint+1)]
        gg = gr[["Country Code"] + cols].melt(id_vars="Country Code", var_name="gini_year", value_name="gini").dropna(subset=["gini"])
        gg.gini_year = gg.gini_year.astype(int)
        gg = gg.sort_values(["Country Code", "gini_year"]).drop_duplicates("Country Code", keep="last").rename(columns={"Country Code": "iso_code"})
        gg["gini10"] = gg.gini/10
        p = p.merge(gg, on="iso_code", how="left", validate="one_to_one")
        p["endpoint"] = endpoint
        p["outcome_start"] = endpoint-2
        p["education_lag"] = p.outcome_start-p.education_year
        p["complete"] = p[VARS + ["ladder"]].notna().all(axis=1)
        flows.append({"endpoint": endpoint, "happiness_units_after_territory_exclusions": len(hh),
                      "with_prior_education": int(p.gap10.notna().sum()), "complete_rows": int(p.complete.sum())})
        rows.append(p)
    audit = pd.concat(rows, ignore_index=True)
    audit.to_csv(PROCESSED / "panel_country_period_audit.csv", index=False)
    p = audit[audit.complete].copy()
    p["country_periods"] = p.groupby("iso_code").iso_code.transform("size")
    p["eligible_for_within"] = p.country_periods >= 2
    p.to_csv(PROCESSED / "panel_all_complete.csv", index=False)
    d = p[p.eligible_for_within].copy().sort_values(["iso_code", "endpoint"]).reset_index(drop=True)
    assert not d.duplicated(["iso_code", "endpoint"]).any()
    assert d.education_lag.between(1, 3).all()
    assert d.groupby("iso_code").size().min() >= 2
    assert not d.duplicated(["iso_code", "survey", "education_year"]).any()
    d.to_csv(PROCESSED / "panel_within_sample.csv", index=False)
    pd.DataFrame(unmapped).to_csv(TABLES / "panel_territory_exclusions.csv", index=False)
    pd.DataFrame(flows).to_csv(TABLES / "panel_sample_flow.csv", index=False)
    return p, d


def panel_fit(d, variables=VARS, country_effects=True, outcome="ladder", period_col="endpoint"):
    blocks = [d[list(variables)].astype(float)]
    blocks.append(pd.get_dummies(d[period_col].astype(str), prefix="period", drop_first=True, dtype=float))
    if country_effects:
        blocks.append(pd.get_dummies(d.iso_code, prefix="country", drop_first=True, dtype=float))
    x = sm.add_constant(pd.concat(blocks, axis=1), has_constant="add")
    if np.linalg.matrix_rank(x) != x.shape[1]: raise ValueError("Rank-deficient panel model")
    groups = pd.factorize(d.iso_code)[0]
    m = sm.OLS(d[outcome], x).fit(cov_type="cluster", cov_kwds={"groups": groups, "use_correction": True, "df_correction": True}, use_t=True)
    return m


def row(name, d, m, term="gap10", outcome="ladder", fe=True):
    lo, hi = m.conf_int().loc[term]
    within_ss = ((d[outcome]-d.groupby("iso_code")[outcome].transform("mean"))**2).sum()
    return {"model": name, "term": term, "country_periods": len(d), "countries": d.iso_code.nunique(),
            "estimate": m.params[term], "se_cluster_country": m.bse[term], "ci_low": lo, "ci_high": hi,
            "p_value": m.pvalues[term], "df_inference": m.df_resid_inference,
            "within_r2": 1-m.ssr/within_ss if fe else np.nan, "overall_r2": m.rsquared}


def bootstrap_panel(d):
    # FWL absorbs country intercepts once. Each bootstrap draw resamples whole
    # countries, including their availability pattern, as independent blocks.
    periods = pd.get_dummies(d.endpoint.astype(str), drop_first=True, dtype=float)
    x = pd.concat([d[VARS], periods], axis=1)
    xw = x-x.groupby(d.iso_code).transform("mean")
    yw = d.ladder-d.groupby(d.iso_code).ladder.transform("mean")
    groups = [np.flatnonzero(d.iso_code.eq(g)) for g in d.iso_code.unique()]
    X = xw.to_numpy(float); y = yw.to_numpy(float)
    check = np.linalg.lstsq(X, y, rcond=None)[0][0]
    assert np.isclose(check, panel_fit(d).params.gap10, atol=1e-9)
    rng = np.random.default_rng(CFG["seed"]+500)
    draws = []
    for _ in range(CFG["bootstrap_replications"]):
        selected = rng.integers(0,len(groups),len(groups))
        idx = np.concatenate([groups[j] for j in selected])
        if np.linalg.matrix_rank(X[idx]) != X.shape[1]: continue
        draws.append(np.linalg.lstsq(X[idx],y[idx],rcond=None)[0][0])
    pd.DataFrame({"education_within_beta": draws}).to_csv(TABLES / "panel_cluster_bootstrap_draws.csv", index=False)
    return {"successful_draws": len(draws), "median": np.median(draws),
            "ci_low": np.quantile(draws,.025), "ci_high": np.quantile(draws,.975),
            "resampling_unit": "Whole country histories, conditional on observed surveys and outcome aggregates"}


def specification_grid():
    rows = []
    for sample in ["primary", "expanded"]:
        d = pd.read_csv(PROCESSED / f"analysis_{sample}.csv")
        for term in ["gap10", "relative_gap", "gradient10"]:
            iqr = d[term].quantile(.75)-d[term].quantile(.25)
            for adjustment, controls in [("Unadjusted", []), ("Prosperity", ["log_gdp"]),
                                          ("Prosperity + attainment + Gini", ["log_gdp", "completion10", "gini10"])]:
                m = fit(d, controls+[term]); lo, hi = m.conf_int().loc[term]
                rows.append({"sample": sample, "n": len(d), "measure": term, "adjustment": adjustment,
                             "estimate_per_iqr": m.params[term]*iqr, "ci_low_per_iqr": lo*iqr,
                             "ci_high_per_iqr": hi*iqr, "iqr_exposure": iqr, "p_value": m.pvalues[term],
                             "max_leverage": m.get_influence().hat_matrix_diag.max()})
    grid = pd.DataFrame(rows)
    grid["p_holm_exploratory_family"] = multipletests(grid.p_value, method="holm")[1]
    grid.to_csv(TABLES / "specification_grid.csv", index=False)
    return grid


def main():
    all_complete, d = build_panel()
    results = []
    pooled = panel_fit(d, country_effects=False)
    main_fit = panel_fit(d)
    results.append(row("Pooled + period indicators", d, pooled, fe=False))
    results.append(row("Country + period effects", d, main_fit))
    # A joint Wald test of every country intercept is rank deficient under
    # country clustering. Report the scientific coefficients rather than that F.
    (TABLES / "panel_main_summary.txt").write_text(
        "Country and period effects, OLS. CRV1 covariance clustered by country.\n"
        "The joint F-test of all absorbed country indicators is intentionally omitted.\n" +
        pd.DataFrame({"coefficient":main_fit.params[VARS],"cluster_se":main_fit.bse[VARS],
                      "p_value":main_fit.pvalues[VARS]}).to_string()+"\n")
    coefficients = []
    for term in VARS: coefficients.append(row("Country + period effects", d, main_fit, term))
    pd.DataFrame(coefficients).to_csv(TABLES / "panel_all_main_coefficients.csv", index=False)
    # Require comparable source names within a country's observed history.
    stable = d.groupby("iso_code").survey.transform("nunique").eq(1)
    stable_d = d[stable].copy()
    if stable_d.iso_code.nunique() >= 12:
        results.append(row("Same survey source within country", stable_d, panel_fit(stable_d)))
    balanced = d[d.country_periods.eq(4)].copy()
    if balanced.iso_code.nunique() >= 12:
        results.append(row("Balanced four-period countries", balanced, panel_fit(balanced)))
    # Re-estimate WITH and WITHOUT Gini on the exact same eligible panel rows.
    gin = d.dropna(subset=["gini10"]).copy()
    gin = gin[gin.groupby("iso_code").iso_code.transform("size")>=2].copy()
    if gin.iso_code.nunique() >= 12:
        results.append(row("Gini-complete rows, no Gini control", gin, panel_fit(gin)))
        results.append(row("Gini-complete rows, add Gini", gin, panel_fit(gin, VARS+["gini10"])))
    # Comparable coefficient scale for the full five-quintile alternative.
    vg = ["gradient10", "log_gdp", "completion10"]
    results.append(row("Five-quintile gradient", d, panel_fit(d, vg), "gradient10"))
    nonlinear = d.copy()
    nonlinear["completion_squared"] = nonlinear.completion10**2
    results.append(row("Quadratic completion control", nonlinear, panel_fit(nonlinear, VARS+["completion_squared"])))
    # First differences in adjacent periods avoid treating a six-year jump as a
    # three-year change. Repeated differences still cluster on country.
    fd = d.copy()
    for var in VARS+["ladder"]: fd["d_"+var] = fd.groupby("iso_code")[var].diff()
    fd["period_step"] = fd.groupby("iso_code").endpoint.diff()
    fd = fd[fd.period_step.eq(3)].copy()
    if fd.iso_code.nunique() >= 12:
        m = panel_fit(fd, ["d_"+v for v in VARS], country_effects=False, outcome="d_ladder")
        results.append(row("Adjacent-period first differences", fd, m, "d_gap10", "d_ladder", fe=False))
    # A descriptive within/between decomposition makes their distinction visible.
    hybrid = d.copy()
    hybrid_vars = []
    for v in VARS:
        hybrid[v+"_between"] = hybrid.groupby("iso_code")[v].transform("mean")
        hybrid[v+"_within"] = hybrid[v]-hybrid[v+"_between"]
        hybrid_vars += [v+"_between",v+"_within"]
    hm = panel_fit(hybrid, hybrid_vars, country_effects=False)
    decomposition = [row("Within/between with period indicators",hybrid,hm,t,fe=False)
                     for t in ["gap10_between","gap10_within"]]
    pd.DataFrame(decomposition).to_csv(TABLES / "panel_within_between.csv", index=False)
    result = pd.DataFrame(results); result.to_csv(TABLES / "panel_models.csv", index=False)
    boot = bootstrap_panel(d)
    grid = specification_grid()
    # Describe how much variation genuinely identifies the longitudinal slope.
    variance = []
    for v in VARS+["ladder"]:
        within = d[v]-d.groupby("iso_code")[v].transform("mean")
        variance.append({"variable":v,"overall_sd":d[v].std(),"within_sd":within.std(),
                         "within_variance_share":within.var()/d[v].var()})
    pd.DataFrame(variance).to_csv(TABLES / "panel_identifying_variation.csv",index=False)
    d.groupby("iso_code").size().value_counts().sort_index().rename_axis("periods").rename("countries").to_csv(TABLES / "panel_coverage.csv")
    # Country influence is a sensitivity range, never an outcome-based deletion.
    leave = []
    for code in d.iso_code.unique():
        dd = d[d.iso_code.ne(code)]
        leave.append({"omitted_iso":code,"education_within_beta":panel_fit(dd).params.gap10})
    pd.DataFrame(leave).to_csv(TABLES / "panel_leave_one_country_out.csv",index=False)
    summary={"all_complete_country_periods":len(all_complete),"all_complete_countries":all_complete.iso_code.nunique(),
             "within_country_periods":len(d),"within_countries":d.iso_code.nunique(),
             "balanced_countries":balanced.iso_code.nunique(),"same_source_countries":stable_d.iso_code.nunique(),
             "gini_complete_countries":gin.iso_code.nunique(),"primary":row("Country + period effects",d,main_fit),
             "cluster_bootstrap":boot,"leave_one_country_beta_min":min(x["education_within_beta"] for x in leave),
             "leave_one_country_beta_max":max(x["education_within_beta"] for x in leave),
             "interpretation":"Exploratory longitudinal association. Repeated aggregate country observations, not individual tracking or a causal policy evaluation."}
    write_json(ROOT / "outputs/panel_results.json", summary)
    plt.rcParams.update({"font.family":"DejaVu Sans","axes.spines.top":False,"axes.spines.right":False,"font.size":10})
    fig,ax=plt.subplots(figsize=(10,5.4))
    rr=result.iloc[::-1]
    for j,(_,r) in enumerate(rr.iterrows()):
        ax.errorbar(r.estimate,j,xerr=[[r.estimate-r.ci_low],[r.ci_high-r.estimate]],fmt="o",capsize=3,color=C["blue"])
    ax.set_yticks(range(len(rr)),[f"{r.model} ({r.countries} countries)" for _,r in rr.iterrows()])
    ax.axvline(0,color=C["muted"],ls="--",lw=1)
    ax.set(xlabel="Ladder points per 10 pp gap or gradient (country-clustered 95% interval)",title="Within-country comparisons and design checks")
    fig.tight_layout();save_figure(fig,"08_panel_estimates")
    fig,axes=plt.subplots(1,2,figsize=(11,4.5))
    for _,g in d.groupby("iso_code"):
        axes[0].plot(g.endpoint,g.gap10*10,color=C["blue"],alpha=.25,lw=1)
        axes[1].plot(g.endpoint,g.ladder,color=C["amber"],alpha=.25,lw=1)
    axes[0].set(xlabel="Outcome window endpoint",ylabel="Prior Q5-Q1 completion gap (pp)",title="Educational disparities across observed histories")
    axes[1].set(xlabel="Outcome window endpoint",ylabel="Life evaluation",title="Non-overlapping three-year outcome windows")
    for a in axes:a.set_xticks(CFG["panel_outcome_endpoints"])
    fig.tight_layout();save_figure(fig,"09_panel_histories")
    fig,ax=plt.subplots(figsize=(8.5,9))
    labels=[]
    measures={"gap10":"Absolute gap","relative_gap":"Relative gap","gradient10":"Rank gradient"}
    for j,(_,r) in enumerate(grid.iterrows()):
        color=C["blue"] if r.adjustment=="Prosperity + attainment + Gini" else C["muted"]
        ax.errorbar(r.estimate_per_iqr,j,xerr=[[r.estimate_per_iqr-r.ci_low_per_iqr],[r.ci_high_per_iqr-r.estimate_per_iqr]],fmt="o",ms=3,capsize=2,color=color)
        labels.append(f"{measures[r.measure]}, {r.adjustment}, n={r.n}")
    ax.set_yticks(range(len(grid)),labels,fontsize=9.5)
    ax.axvline(0,color=C["muted"],ls="--",lw=1)
    ax.set(xlabel="Ladder-point difference over an exposure IQR (95% HC3 interval)",title="All 18 exploratory specifications, in design order")
    fig.tight_layout();save_figure(fig,"10_specification_grid")
    print(json.dumps(summary,indent=2,default=str))


if __name__=="__main__":main()
