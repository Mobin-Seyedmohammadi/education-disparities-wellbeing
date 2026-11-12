"""Run from the project root: python -m src.analysis

All cleaning rules depend on source metadata and coverage, not outcome signs.
This is a retrospective, exploratory study, not a preregistered analysis.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pycountry
from scipy import stats
import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.stats.diagnostic import het_breuschpagan, linear_reset
from statsmodels.stats.outliers_influence import variance_inflation_factor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import KFold, LeaveOneGroupOut

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw"
PROCESSED = ROOT / "data/processed"
TABLES = ROOT / "outputs/tables"
FIGURES = ROOT / "outputs/figures"
CFG = json.loads((ROOT / "config.json").read_text())
C = {"ink": "#172C3C", "blue": "#236F9E", "amber": "#B47720",
     "pale": "#E4EDF2", "muted": "#607584", "purple": "#7566A8"}
BASE = ["log_gdp", "completion10", "gini10"]
FULL = BASE + ["gap10"]


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False,
                                     default=lambda x: x.item() if hasattr(x, "item") else str(x)) + "\n")


def hash_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""): h.update(b)
    return h.hexdigest()


def verify_inputs():
    expected = json.loads((ROOT / "data/source_manifest.json").read_text())
    for row in expected["files"]:
        p = ROOT / row["path"]
        if hash_file(p) != row["sha256"]:
            raise ValueError(f"Raw input changed: {p.name}. Use the frozen files or deliberately create a new vintage and manifest.")
    return expected


def country_code(name):
    # Explicit nomenclature reconciliation. No fuzzy or substring joins.
    aliases = {
        "Taiwan Province of China": "TWN", "Kosovo": "XKX",
        "Republic of Korea": "KOR", "Hong Kong SAR of China": "HKG",
        "Côte d’Ivoire": "CIV", "Iran": "IRN", "Congo": "COG",
        "DR Congo": "COD", "State of Palestine": "PSE", "Türkiye": "TUR",
        "Republic of Moldova": "MDA", "Venezuela": "VEN", "Bolivia": "BOL",
        "Tanzania": "TZA", "Laos": "LAO", "Lao PDR": "LAO", "Vietnam": "VNM",
        "Macedonia": "MKD", "Swaziland": "SWZ",
    }
    if name in aliases: return aliases[name], "explicit alias"
    try: return pycountry.countries.lookup(name).alpha_3, "ISO exact lookup"
    except LookupError: raise ValueError(f"Unresolved country: {name!r}. Add an explicit, reviewed alias.")


def prepare_wide():
    use = ["iso_code", "country", "region_group", "income_group", "survey", "year",
           "category", "wealth", "sex", "location", "comp_upsec_v2_m", "comp_upsec_v2_no"]
    w = pd.read_csv(RAW / "WIDE.csv.gz", usecols=use, low_memory=False)
    universe = w[["iso_code", "country", "region_group", "income_group"]].drop_duplicates()
    assert not universe.iso_code.duplicated().any(), "Ambiguous WIDE country metadata"
    eligible = w[w.category.isin(["Wealth", "Total"]) & w.comp_upsec_v2_m.notna()].copy()
    eligible["group"] = eligible.wealth.where(eligible.category.eq("Wealth"), "Total")
    eligible = eligible[eligible.group.isin([f"Quintile {q}" for q in range(1, 6)] + ["Total"])]
    assert eligible.comp_upsec_v2_m.between(0, 1).all()
    keys = ["iso_code", "survey", "year"]
    k = keys + ["group"]
    counts = eligible.groupby(k).comp_upsec_v2_m.agg(["size", "nunique"]).reset_index()
    counts[counts["size"] > 1].to_csv(TABLES / "duplicate_measurements.csv", index=False)
    # A conflicting national total or middle quintile also invalidates this survey.
    bad = counts[counts["nunique"] > 1][keys].drop_duplicates()
    bad.to_csv(TABLES / "excluded_ambiguous_surveys.csv", index=False)
    bidx = pd.MultiIndex.from_frame(bad)
    keep = ~pd.MultiIndex.from_frame(eligible[keys]).isin(bidx)
    clean = eligible[keep].copy()
    # Identical point estimates can have absent counts. Keep a reported count if
    # present, then its minimum if more than one is reported (conservative flag).
    clean = clean.groupby(k, as_index=False).agg(value=("comp_upsec_v2_m", "first"),
                                               sample_n=("comp_upsec_v2_no", "min"))
    values = clean.pivot(index=keys, columns="group", values="value")
    sizes = clean.pivot(index=keys, columns="group", values="sample_n")
    required = [f"Quintile {q}" for q in range(1, 6)] + ["Total"]
    good = values.dropna(subset=required).copy()
    good["q1_n"] = sizes["Quintile 1"]
    good["q5_n"] = sizes["Quintile 5"]
    good = good.reset_index()
    good["gap_pp"] = 100 * (good["Quintile 5"] - good["Quintile 1"])
    good["gap10"] = good.gap_pp / 10
    good["completion_pp"] = good.Total * 100
    good["completion10"] = good.Total * 10
    denom = (good["Quintile 5"] + good["Quintile 1"]) / 2
    good["relative_gap"] = (good["Quintile 5"] - good["Quintile 1"]) / denom.replace(0, np.nan)
    # Rank-order gradient uses all five country-specific SES groups. It is not
    # a population SII: group shares of the target age group are unavailable.
    x = np.array([.1, .3, .5, .7, .9]); centered = x - x.mean()
    good["quintile_gradient_pp"] = good[[f"Quintile {q}" for q in range(1, 6)]].to_numpy() @ centered / (centered @ centered) * 100
    good["gradient10"] = good.quintile_gradient_pp / 10
    good["priority"] = good.survey.map({"DHS": 0, "MICS": 1}).fillna(2)
    # Sex/location gaps are descriptive backups and must use this same survey.
    for cat, group, high, low, prefix in [("Sex", "sex", "Male", "Female", "sex"),
                                           ("Location", "location", "Urban", "Rural", "location")]:
        s = w[(w.category == cat) & w.comp_upsec_v2_m.notna()]
        g = s.groupby(keys + [group]).comp_upsec_v2_m.agg(["first", "nunique"]).reset_index()
        g = g[g["nunique"] == 1].pivot(index=keys, columns=group, values="first")
        diff = ((g[high] - g[low]) * 100).rename(prefix + "_gap_pp").reset_index()
        good = good.merge(diff, on=keys, how="left", validate="one_to_one")
    good = good.merge(universe, on="iso_code", validate="many_to_one")
    good.to_csv(PROCESSED / "all_valid_education_surveys.csv", index=False)
    audit = {"wide_rows": len(w), "wide_countries": len(universe),
             "completion_rows_before_dedup": len(eligible),
             "duplicated_measurement_keys": int((counts["size"] > 1).sum()),
             "conflicting_measurement_keys": int((counts["nunique"] > 1).sum()),
             "excluded_ambiguous_surveys": len(bad), "valid_education_surveys": len(good)}
    return universe, good, audit


def latest_education(surveys, start, end):
    return (surveys[surveys.year.between(start, end)]
            .sort_values(["iso_code", "year", "priority", "survey"], ascending=[True, False, True, True])
            .drop_duplicates("iso_code").rename(columns={"year": "education_year"}))


def prepare_happiness():
    h = pd.read_excel(RAW / "happiness2025.xlsx")
    h = h[h.Year == CFG["happiness_endpoint"]].copy()
    parsed = [country_code(n) for n in h["Country name"]]
    h["iso_code"] = [x[0] for x in parsed]
    cross = pd.DataFrame({"happiness_name": h["Country name"], "iso_code": h.iso_code,
                          "method": [x[1] for x in parsed]})
    cross.to_csv(PROCESSED / "country_crosswalk.csv", index=False)
    assert h.iso_code.is_unique
    h = h.rename(columns={"Country name": "happiness_country", "Ladder score": "ladder"})
    h["ladder_se_approx"] = (h.upperwhisker - h.lowerwhisker) / (2 * 1.96)
    assert h.ladder.between(0, 10).all()
    assert ((h.lowerwhisker <= h.ladder) & (h.ladder <= h.upperwhisker)).all()
    return h[["iso_code", "happiness_country", "ladder", "lowerwhisker", "upperwhisker", "ladder_se_approx"]]


def prepare_gini():
    g = pd.read_csv(RAW / "GINI.csv", skiprows=4)
    years = [str(y) for y in range(CFG["gini_start_year"], CFG["gini_end_year"] + 1)]
    long = g.melt(id_vars=["Country Code"], value_vars=years, var_name="gini_year", value_name="gini")
    long = long.dropna(subset=["gini"])
    long.gini_year = long.gini_year.astype(int)
    long = long.rename(columns={"Country Code": "iso_code"})
    latest = long.sort_values(["iso_code", "gini_year"]).drop_duplicates("iso_code", keep="last")
    latest["gini10"] = latest.gini / 10
    assert latest.gini.between(0, 100).all()
    return latest


def prepare_gdp():
    response = json.loads((RAW / "gdp_ppp_2022_2024.json").read_text())
    if response[0]["pages"] != 1: raise ValueError("Incomplete API response")
    a = pd.DataFrame([{"iso_code": r["countryiso3code"], "year": int(r["date"]), "gdp": r["value"]}
                      for r in response[1]])
    a = a[a.year.isin(CFG["gdp_years"])].dropna(subset=["gdp"])
    a = a[a.gdp > 0]
    a["log_gdp"] = np.log(a.gdp)
    g = a.groupby("iso_code", as_index=False).agg(log_gdp=("log_gdp", "mean"),
                  gdp_years=("year", "nunique"), gdp_ppp_mean=("gdp", "mean"))
    # Require all three calendar years instead of silently averaging uneven windows.
    g = g[g.gdp_years == len(CFG["gdp_years"])]
    return g, response[0]


def merge_sources(universe, edu, happy, gini, gdp, suffix="primary"):
    # Start from all happiness countries to make exclusions visible.
    d = happy.merge(edu.drop(columns="country"), on="iso_code", how="left", validate="one_to_one")
    d = d.merge(gini, on="iso_code", how="left", validate="one_to_one")
    d = d.merge(gdp, on="iso_code", how="left", validate="one_to_one")
    d["has_education"] = d.gap10.notna()
    d["has_gini"] = d.gini10.notna()
    d["has_gdp"] = d.log_gdp.notna()
    d["included"] = d[["gap10", "completion10", "gini10", "log_gdp", "ladder"]].notna().all(axis=1)
    for flag in ["has_education", "has_gini", "has_gdp", "included"]: d[flag] = d[flag].astype(bool)
    d["exclusion_reasons"] = d.apply(lambda r: "; ".join(x for x, flag in
           [("no eligible paired education survey", "has_education"),
            ("no 2015-2024 Gini", "has_gini"), ("incomplete 2022-2024 GDP", "has_gdp")] if not r[flag]), axis=1)
    d["country"] = d.happiness_country
    d["education_age_at_outcome_start"] = 2022 - d.education_year
    d["gini_age_at_endpoint"] = CFG["happiness_endpoint"] - d.gini_year
    d.to_csv(PROCESSED / f"country_audit_{suffix}.csv", index=False)
    sample = d[d.included].copy().sort_values("iso_code").reset_index(drop=True)
    assert sample.iso_code.is_unique and sample[FULL + ["ladder"]].notna().all().all()
    sample.to_csv(PROCESSED / f"analysis_{suffix}.csv", index=False)
    return sample, d


def fit(d, features, robust=True):
    x = sm.add_constant(d[features].astype(float), has_constant="add")
    if np.linalg.matrix_rank(x) != x.shape[1]: raise ValueError("Rank-deficient regression")
    m = sm.OLS(d.ladder, x)
    return m.fit(cov_type="HC3", use_t=True) if robust else m.fit()


def model_row(name, m, term="gap10", label=None):
    lo, hi = m.conf_int().loc[term]
    return {"model": name, "label": label or name, "term": term, "n": int(m.nobs),
            "estimate": float(m.params[term]), "se_hc3": float(m.bse[term]),
            "ci_low": float(lo), "ci_high": float(hi), "p_value": float(m.pvalues[term]),
            "r2": float(m.rsquared), "adj_r2": float(m.rsquared_adj)}


def regressions(d):
    definitions = [("M1", ["gap10"], "Education gap only"),
                   ("M2", ["gini10"], "Gini only"),
                   ("M3", ["log_gdp", "gap10"], "Gap + prosperity"),
                   ("M4", ["log_gdp", "completion10", "gap10"], "Gap + prosperity + attainment"),
                   ("M5", FULL, "Gap + prosperity + attainment + Gini")]
    models = {}; rows = []; coefficients = []
    for name, features, label in definitions:
        m = fit(d, features); models[name] = m
        term = "gap10" if "gap10" in features else "gini10"
        rows.append(model_row(name, m, term, label))
        for t in m.params.index: coefficients.append(model_row(name, m, t, label))
        (TABLES / f"{name}_summary.txt").write_text(m.summary().as_text())
    pd.DataFrame(rows).to_csv(TABLES / "model_ladder.csv", index=False)
    pd.DataFrame(coefficients).to_csv(TABLES / "all_coefficients.csv", index=False)
    full = models["M5"]
    partial = {}
    for term in ["gap10", "gini10"]:
        reduced = fit(d, [x for x in FULL if x != term])
        partial[term] = (reduced.ssr - full.ssr) / reduced.ssr
    pd.DataFrame([{"predictor": k, "partial_r2": v} for k, v in partial.items()]).to_csv(TABLES / "partial_r2.csv", index=False)
    return models, pd.DataFrame(rows), partial


def bootstrap(d):
    rng = np.random.default_rng(CFG["seed"])
    x = sm.add_constant(d[FULL], has_constant="add").to_numpy(float)
    y = d.ladder.to_numpy(float); n = len(y)
    def sse(a, b):
        residual = b - a @ np.linalg.lstsq(a, b, rcond=None)[0]
        return residual @ residual
    records = []
    for _ in range(CFG["bootstrap_replications"]):
        idx = rng.integers(0, n, n); xb = x[idx]; yb = y[idx]
        if np.linalg.matrix_rank(xb) != x.shape[1]: continue
        b = np.linalg.lstsq(xb, yb, rcond=None)[0]
        ss = sse(xb, yb)
        se = sse(np.delete(xb, 4, axis=1), yb)
        sg = sse(np.delete(xb, 3, axis=1), yb)
        # Paired resampling: the two partial R-squareds share every country draw.
        records.append([b[4], (se - ss)/se, (sg - ss)/sg, (se - ss)/se - (sg - ss)/sg])
    b = pd.DataFrame(records, columns=["education_beta", "education_partial_r2", "gini_partial_r2", "partial_r2_difference"])
    b.to_csv(TABLES / "country_bootstrap_draws.csv", index=False)
    result = [{"quantity": c, "bootstrap_median": b[c].median(), "ci_low": b[c].quantile(.025),
               "ci_high": b[c].quantile(.975), "successful_draws": len(b)} for c in b]
    pd.DataFrame(result).to_csv(TABLES / "country_bootstrap_summary.csv", index=False)
    return result


def cross_validation(d):
    sets = {"Mean only": [], "Education gap": ["gap10"], "Gini": ["gini10"],
            "Prosperity": ["log_gdp"], "Prosperity + attainment": ["log_gdp", "completion10"],
            "Baseline": BASE, "Baseline + education gap": FULL}
    rows = []; predictions = []
    y = d.ladder.to_numpy(); n = len(d)
    for repeat in range(CFG["cv_repeats"]):
        splits = list(KFold(CFG["cv_folds"], shuffle=True, random_state=CFG["seed"] + repeat).split(d))
        for name, columns in sets.items():
            out = np.empty(n)
            for fold, (tr, te) in enumerate(splits):
                if columns:
                    estimator = LinearRegression().fit(d.iloc[tr][columns], y[tr])
                    pred = estimator.predict(d.iloc[te][columns])
                else: pred = np.repeat(y[tr].mean(), len(te))
                out[te] = pred
                for i, v in zip(te, pred): predictions.append([repeat, fold, name, d.iloc[i].iso_code, y[i], v])
            err = y - out
            rows.append({"repeat": repeat, "model": name, "rmse": np.sqrt(np.mean(err**2)),
                         "mae": np.mean(np.abs(err)), "oof_r2": 1 - np.sum(err**2)/np.sum((y-y.mean())**2)})
    p = pd.DataFrame(predictions, columns=["repeat", "fold", "model", "iso_code", "actual", "predicted"])
    p.to_csv(TABLES / "cv_predictions.csv", index=False)
    scores = pd.DataFrame(rows); scores.to_csv(TABLES / "cv_repeats.csv", index=False)
    summary = scores.groupby("model", sort=False).agg(rmse_mean=("rmse", "mean"),
                  rmse_split_sd=("rmse", "std"), mae_mean=("mae", "mean"), oof_r2_mean=("oof_r2", "mean"))
    summary.to_csv(TABLES / "cv_summary.csv")
    pivot = scores.pivot(index="repeat", columns="model", values="rmse")
    delta = pivot["Baseline + education gap"] - pivot["Baseline"]
    paired = {"rmse_difference_full_minus_baseline": delta.mean(), "split_sd": delta.std(),
              "min_across_splits": delta.min(), "max_across_splits": delta.max(),
              "repeats_full_better": int((delta < 0).sum()), "repeats": len(delta),
              "interpretation": "Variation across reused random partitions, not a sampling confidence interval or independent hypothesis test."}
    # Exact PRESS predictions for OLS provide a partition-free check.
    loo = []
    for name, cols in sets.items():
        if cols:
            m = fit(d, cols, robust=False); h = m.get_influence().hat_matrix_diag
            errors = m.resid.to_numpy() / (1 - h)
        else: errors = (y - y.mean()) / (1 - 1/n)
        loo.append({"model": name, "loocv_rmse": np.sqrt(np.mean(errors**2))})
    pd.DataFrame(loo).to_csv(TABLES / "loocv.csv", index=False)
    # Region transport is a stress test of predictions, not the main estimand.
    regional = []
    for tr, te in LeaveOneGroupOut().split(d, y, groups=d.region_group):
        reg = d.iloc[te].region_group.iloc[0]
        for name, cols in [("Baseline", BASE), ("Baseline + education gap", FULL)]:
            pred = LinearRegression().fit(d.iloc[tr][cols], y[tr]).predict(d.iloc[te][cols])
            regional.append({"held_out_region": reg, "n_test": len(te), "model": name,
                             "rmse": np.sqrt(np.mean((y[te]-pred)**2))})
    pd.DataFrame(regional).to_csv(TABLES / "region_transport.csv", index=False)
    return summary.reset_index(), paired


def diagnostics(d):
    m = fit(d, FULL, robust=False); inf = m.get_influence()
    z = d[["iso_code", "country"]].copy()
    z["fitted"] = m.fittedvalues; z["residual"] = m.resid
    z["cooks_d"] = inf.cooks_distance[0]; z["leverage"] = inf.hat_matrix_diag
    z["studentized_residual"] = inf.resid_studentized_external
    z["flag_cook"] = z.cooks_d > 4/len(d)
    z.to_csv(TABLES / "influence.csv", index=False)
    bp = het_breuschpagan(m.resid, m.model.exog)
    reset = linear_reset(fit(d, FULL), power=2, use_f=True, cov_type="HC3")
    x = m.model.exog
    vif = pd.DataFrame({"term": m.model.exog_names[1:],
                        "vif": [variance_inflation_factor(x, i) for i in range(1, x.shape[1])]})
    vif.to_csv(TABLES / "vif.csv", index=False)
    # FWL residualization is descriptive. Inference uses the original full model.
    controls = sm.add_constant(d[BASE], has_constant="add")
    fwl = d[["iso_code", "country"]].copy()
    fwl["gap_residual"] = sm.OLS(d.gap10, controls).fit().resid
    fwl["ladder_residual"] = sm.OLS(d.ladder, controls).fit().resid
    fwl.to_csv(TABLES / "partial_regression.csv", index=False)
    slope = np.dot(fwl.gap_residual, fwl.ladder_residual) / np.dot(fwl.gap_residual, fwl.gap_residual)
    assert np.isclose(slope, m.params.gap10, atol=1e-10)
    # Influence diagnostics never silently delete the countries that matter most.
    leave = []
    for i, row in d.iterrows():
        leave.append({"omitted_iso": row.iso_code, "omitted_country": row.country,
                      "education_beta": fit(d.drop(index=i), FULL).params.gap10})
    pd.DataFrame(leave).to_csv(TABLES / "leave_one_country_out.csv", index=False)
    return z, {"breusch_pagan_lm_p": bp[1], "reset_hc3_p": float(reset.pvalue),
               "max_vif": vif.vif.max(), "condition_number_unscaled": m.condition_number,
               "flagged_countries": z.loc[z.flag_cook, "country"].tolist(),
               "fwl_slope_check": slope, "residual_df": m.df_resid}


def sensitivity(d, expanded, influence):
    rows = []
    def record(name, sample, features=FULL, term="gap10"):
        if len(sample) <= len(features) + 5: return
        rows.append(model_row(name, fit(sample, features), term))
    record("Primary specification", d)
    record("Education surveys from 2010 onward", expanded)
    record("Education surveys from 2018 onward", d[d.education_year >= 2018])
    record("Gini observations from 2020 onward", d[d.gini_year >= 2020])
    record("DHS or MICS surveys only", d[d.survey.isin(["DHS", "MICS"])])
    record("Reported Q1 and Q5 n >= 100", d[(d.q1_n >= 100) & (d.q5_n >= 100)])
    bad = set(influence.loc[influence.flag_cook, "iso_code"])
    record("Exclude Cook-flagged countries", d[~d.iso_code.isin(bad)])
    q = d.copy(); q["log_gdp_squared"] = q.log_gdp**2
    record("Allow quadratic log prosperity", q, FULL + ["log_gdp_squared"])
    q["completion_squared"] = q.completion10**2
    record("Allow quadratic completion", q, FULL + ["completion_squared"])
    q["education_age"] = 2022 - q.education_year
    record("Adjust for education survey age", q, FULL + ["education_age"])
    # A singleton region has leverage 1 with its own intercept, invalidating
    # HC3's residual/(1-h) correction. Exclude singleton strata for this check.
    region_n = d.groupby("region_group").iso_code.transform("size")
    regional = d[region_n >= 2].copy()
    region_dummy = pd.get_dummies(regional.region_group, prefix="region", drop_first=True, dtype=float)
    regional = pd.concat([regional, region_dummy], axis=1)
    rows.append(model_row("Region indicators, non-singleton regions", fit(regional, FULL + list(region_dummy.columns))))
    # This rescaling changes the estimand. Keep it in a separate output table.
    alternative = []
    for term, title in [("relative_gap", "Relative Q5-Q1 gap, per unit"),
                         ("gradient10", "Five-quintile rank gradient, per 10 pp")]:
        dd = d.dropna(subset=[term])
        alternative.append(model_row(title, fit(dd, BASE + [term]), term))
    pd.DataFrame(alternative).to_csv(TABLES / "alternative_measures.csv", index=False)
    res = pd.DataFrame(rows); res.to_csv(TABLES / "sensitivity.csv", index=False)
    # Refit the primary model with inverse reported ladder-variance weights only
    # as a diagnostic: those intervals omit country-level model error.
    wm = sm.WLS(d.ladder, sm.add_constant(d[FULL], has_constant="add"), weights=1/d.ladder_se_approx**2).fit(cov_type="HC3", use_t=True)
    pd.DataFrame([model_row("Inverse ladder-variance weights (diagnostic)", wm)]).to_csv(TABLES / "weighted_diagnostic.csv", index=False)
    return res


def selection(audit, universe):
    rows = []
    for var in ["ladder", "log_gdp", "gini"]:
        kept = audit.loc[audit.included, var].dropna()
        lost = audit.loc[~audit.included, var].dropna()
        pooled = np.sqrt((kept.var(ddof=1) + lost.var(ddof=1))/2)
        rows.append({"variable": var, "included_n": len(kept), "excluded_n": len(lost),
                     "included_mean": kept.mean(), "excluded_mean": lost.mean(),
                     "standardized_mean_difference": (kept.mean()-lost.mean())/pooled})
    pd.DataFrame(rows).to_csv(TABLES / "sample_selection.csv", index=False)
    # WIDE metadata exists for countries even when no eligible wealth survey does.
    aa = audit.drop(columns=["region_group", "income_group"]).merge(
        universe[["iso_code", "region_group", "income_group"]], on="iso_code", how="left", validate="one_to_one")
    aa.groupby(["income_group", "included"], dropna=False).size().unstack(fill_value=0).to_csv(TABLES / "coverage_by_income_group.csv")


def save_figure(fig, name):
    fig.savefig(FIGURES / (name + ".png"), dpi=200, bbox_inches="tight", facecolor="white")
    fig.savefig(FIGURES / (name + ".pdf"), bbox_inches="tight", facecolor="white")
    plt.close(fig)


def figures(d, ladder, cv, sensitivity_table, influence):
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "text.color": C["ink"],
                        "axes.labelcolor": C["ink"], "axes.spines.top": False, "axes.spines.right": False,
                        "axes.edgecolor": "#9AADB8", "xtick.color": C["muted"], "ytick.color": C["muted"],
                        "axes.titleweight": "bold", "axes.titlesize": 13, "figure.dpi": 120})
    # Visible indicators, not a latent index.
    fig, ax = plt.subplots(figsize=(9, 5.2))
    ordered = d.sort_values("completion_pp")
    for _, r in ordered.iterrows():
        ax.plot([r["Quintile 1"]*100, r["Quintile 5"]*100], [r.ladder]*2, color=C["pale"], lw=1)
    ax.scatter(d["Quintile 1"]*100, d.ladder, color=C["blue"], s=22, label="Lowest SES quintile (Q1)")
    ax.scatter(d["Quintile 5"]*100, d.ladder, color=C["amber"], s=22, marker="D", label="Highest SES quintile (Q5)")
    ax.set(xlabel="Upper-secondary completion (%)", ylabel="Life evaluation (2022-2024, 0-10)",
           title="The gap and the overall completion level differ")
    ax.legend(frameon=False, loc="lower right", fontsize=9); fig.tight_layout(); save_figure(fig, "01_group_completion")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
    regions = sorted(d.region_group.unique()); markers = ['o', 's', '^', 'D', 'v', 'P', 'X']
    fwl = pd.read_csv(TABLES / "partial_regression.csv")
    for j, reg in enumerate(regions):
        mask = d.region_group.eq(reg)
        axes[0].scatter(d.loc[mask, "gap_pp"], d.loc[mask, "ladder"], marker=markers[j],
                        s=33, alpha=.8, color=plt.cm.tab10(j), label=reg)
    x = np.linspace(d.gap_pp.min(), d.gap_pp.max(), 100)
    b = np.polyfit(d.gap_pp, d.ladder, 1); axes[0].plot(x, np.polyval(b, x), color=C["ink"], lw=1.5)
    axes[0].set(xlabel="Q5-Q1 completion gap (percentage points)", ylabel="Life evaluation (0-10)", title="Unadjusted comparison")
    axes[1].scatter(fwl.gap_residual*10, fwl.ladder_residual, color=C["blue"], s=30, alpha=.8)
    m = fit(d, FULL); x = np.linspace(fwl.gap_residual.min(), fwl.gap_residual.max(), 100)
    axes[1].plot(x*10, x*m.params.gap10, color=C["ink"], lw=1.5)
    axes[1].axhline(0, color="#BBBBBB", lw=.6); axes[1].axvline(0, color="#BBBBBB", lw=.6)
    axes[1].set(xlabel="Residual completion gap (percentage points)", ylabel="Residual life evaluation", title="After prosperity, attainment and Gini")
    fig.tight_layout(); save_figure(fig, "02_raw_and_adjusted")

    fig, ax = plt.subplots(figsize=(9, 4.7))
    rows = ladder[ladder.term.eq("gap10")].iloc[::-1]
    for j, (_, r) in enumerate(rows.iterrows()):
        ax.errorbar(r.estimate, j, xerr=[[r.estimate-r.ci_low],[r.ci_high-r.estimate]], fmt="o", color=C["blue"], capsize=3)
    ax.set_yticks(range(len(rows)), rows.label)
    ax.axvline(0, color=C["muted"], ls="--", lw=1)
    ax.set(xlabel="Life-ladder points per 10 pp larger education gap (95% HC3 interval)", title=f"The same {len(d)} countries in every specification")
    fig.tight_layout(); save_figure(fig, "03_model_ladder")

    fig, ax = plt.subplots(figsize=(9, 4.8))
    cv = cv.iloc[::-1]
    ax.barh(cv.model, cv.rmse_mean, color=[C["blue"] if n=="Baseline + education gap" else C["pale"] for n in cv.model], edgecolor=C["muted"], lw=.5)
    for j, (_, r) in enumerate(cv.iterrows()): ax.text(r.rmse_mean+.015, j, f"{r.rmse_mean:.3f}", va="center", fontsize=10)
    ax.set(xlabel="Held-out RMSE in ladder points (lower is better)", title="Paired five-fold cross-validation, 20 repeated partitions")
    ax.set_xlim(0, cv.rmse_mean.max()*1.18); fig.tight_layout(); save_figure(fig, "04_prediction")

    fig, ax = plt.subplots(figsize=(10, 5.6))
    for j, (_, r) in enumerate(sensitivity_table.iloc[::-1].iterrows()):
        ax.errorbar(r.estimate, j, xerr=[[r.estimate-r.ci_low],[r.ci_high-r.estimate]], fmt="o", color=C["blue"], capsize=3)
    ax.set_yticks(range(len(sensitivity_table)), [f"{r.model} (n={r.n})" for _, r in sensitivity_table.iloc[::-1].iterrows()])
    ax.axvline(0, color=C["muted"], ls="--", lw=1)
    ax.set(xlabel="Life-ladder points per 10 pp larger gap (95% HC3 interval)", title="Sensitivity to defensible design changes")
    fig.tight_layout(); save_figure(fig, "05_sensitivity")

    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8))
    axes[0].scatter(influence.fitted, influence.residual, s=24, color=C["blue"], alpha=.8)
    axes[0].axhline(0, color=C["muted"], lw=1)
    axes[0].set(xlabel="Fitted life evaluation", ylabel="Residual", title="Residual pattern")
    stats.probplot(influence.residual, dist="norm", plot=axes[1]); axes[1].set_title("Residual quantiles")
    axes[1].get_lines()[0].set(markerfacecolor=C["blue"], markeredgecolor=C["blue"], markersize=3)
    top = influence.nlargest(8, "cooks_d").sort_values("cooks_d")
    axes[2].barh(top.country, top.cooks_d, color=C["pale"], edgecolor=C["muted"], lw=.5)
    axes[2].axvline(4/len(d), color=C["amber"], ls="--", lw=1)
    axes[2].set(xlabel="Cook's distance", title="Influence, with 4/n flag")
    fig.tight_layout(); save_figure(fig, "06_diagnostics")

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].hist(d.education_year, bins=np.arange(2014.5,2022,1), color=C["blue"], edgecolor="white")
    axes[0].set(xlabel="Selected education survey year", ylabel="Countries", title="Education predates the outcome window")
    axes[1].hist(d.gini_year, bins=np.arange(2014.5,2025,1), color=C["amber"], edgecolor="white")
    axes[1].set(xlabel="Selected Gini survey year", ylabel="Countries", title="Gini observations have unequal dates")
    fig.tight_layout(); save_figure(fig, "07_data_vintages")


def main():
    for p in [PROCESSED, TABLES, FIGURES]: p.mkdir(parents=True, exist_ok=True)
    manifest = verify_inputs()
    universe, surveys, cleaning = prepare_wide()
    happy = prepare_happiness(); gini = prepare_gini(); gdp, api_meta = prepare_gdp()
    edu = latest_education(surveys, CFG["education_start_year"], CFG["education_end_year"])
    d, audit = merge_sources(universe, edu, happy, gini, gdp)
    expanded, _ = merge_sources(universe, latest_education(surveys, 2010, CFG["education_end_year"]), happy, gini, gdp, "expanded")
    models, ladder, partial = regressions(d)
    boot = bootstrap(d); cv, paired = cross_validation(d)
    influence, diag = diagnostics(d); sens = sensitivity(d, expanded, influence)
    selection(audit, universe); figures(d, ladder, cv, sens, influence)
    description = d[["ladder", "gap_pp", "completion_pp", "gini", "log_gdp", "education_year", "gini_year"]].describe().T
    description.to_csv(TABLES / "descriptive_statistics.csv")
    # Spearman/Pearson describe the unconditional relationship. No extra primary tests.
    correlations = []
    for x in ["gap_pp", "gini", "completion_pp", "log_gdp"]:
        correlations.append({"variable": x, "pearson_r": d[x].corr(d.ladder),
                             "spearman_r": stats.spearmanr(d[x], d.ladder).statistic})
    pd.DataFrame(correlations).to_csv(TABLES / "correlations.csv", index=False)
    primary = model_row("M5", models["M5"])
    counts = {"happiness_countries": len(happy), "wide_countries": len(universe),
              "paired_recent_education_countries": len(edu),
              "happiness_with_education": int(audit.has_education.sum()),
              "with_education_and_gini": int((audit.has_education & audit.has_gini).sum()),
              "primary_countries": len(d), "expanded_countries": len(expanded),
              "regions_in_primary": d.region_group.nunique()}
    all_results = {"configuration": CFG, "sample": counts, "cleaning": cleaning,
                   "primary": primary, "unadjusted": model_row("M1", models["M1"]),
                   "partial_r2": partial, "bootstrap": boot, "cv_paired": paired,
                   "diagnostics": diag, "gdp_api_metadata": api_meta,
                   "min_education_year": int(d.education_year.min()),
                   "max_education_year": int(d.education_year.max()),
                   "min_gini_year": int(d.gini_year.min()),
                   "max_gini_year": int(d.gini_year.max())}
    write_json(ROOT / "outputs/results.json", all_results)
    versions = {p: importlib.metadata.version(p) for p in ["pandas", "numpy", "scipy", "statsmodels", "scikit-learn", "matplotlib", "openpyxl", "pycountry"]}
    write_json(ROOT / "outputs/run_metadata.json", {"python": platform.python_version(), "packages": versions,
        "configuration_sha256": hash_file(ROOT / "config.json"),
        "analysis_source_sha256": hash_file(Path(__file__)), "input_manifest": manifest,
        "source_code_sha256": {str(p.relative_to(ROOT)): hash_file(p) for p in sorted((ROOT / "src").glob("*.py"))},
        "note": "No live data requests. All reported estimates use the bundled frozen source files."})
    print(json.dumps({"sample": counts, "primary": primary, "cv_paired": paired, "diagnostics": diag}, indent=2))


if __name__ == "__main__": main()
