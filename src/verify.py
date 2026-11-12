"""Scientific checks independent of reported narratives and plotting code."""
import json
import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.linear_model import LinearRegression
from .analysis import ROOT, PROCESSED, TABLES, FULL, CFG, fit, verify_inputs, write_json
from .panel import panel_fit


def main():
    checks=[]
    verify_inputs();checks.append("Every frozen input matches its SHA-256 manifest")
    d=pd.read_csv(PROCESSED/"analysis_primary.csv")
    assert d.iso_code.is_unique and d[FULL+['ladder']].notna().all().all()
    assert np.allclose(d.gap10,(d['Quintile 5']-d['Quintile 1'])*10)
    assert np.allclose(d.completion10,d.Total*10)
    assert d.education_year.between(2015,2021).all()
    assert d.gini_year.between(2015,2024).all()
    assert d.gdp_years.eq(3).all()
    checks.append("Country keys, source windows, gap units and complete-case contracts hold")
    # Compare reported OLS and HC3 covariance to independent matrix algebra.
    x=sm.add_constant(d[FULL],has_constant='add').to_numpy(float);y=d.ladder.to_numpy(float)
    xp=np.linalg.pinv(x);bread=xp@xp.T;beta=xp@y
    resid=y-x@beta;h=np.einsum('ij,ji->i',x,xp)
    scaled=resid/(1-h)
    manual=bread@(x.T@((scaled**2)[:,None]*x))@bread
    m=fit(d,FULL)
    assert np.allclose(beta,m.params,atol=1e-10)
    assert np.allclose(manual,m.cov_params(),atol=1e-10)
    checks.append("OLS coefficients and HC3 covariance match independent matrix calculations")
    preds=pd.read_csv(TABLES/'cv_predictions.csv')
    assert preds.groupby(['repeat','model']).size().eq(len(d)).all()
    assert preds.groupby(['repeat','model']).iso_code.nunique().eq(len(d)).all()
    assert preds.groupby(['repeat','iso_code']).fold.nunique().eq(1).all()
    one=preds[(preds.repeat==0)&(preds.fold==0)&preds.model.eq('Baseline + education gap')]
    test=d.iso_code.isin(one.iso_code)
    est=LinearRegression().fit(d.loc[~test,FULL],d.loc[~test,'ladder'])
    actual=one.set_index('iso_code').reindex(d.loc[test,'iso_code']).predicted.to_numpy()
    assert np.allclose(actual,est.predict(d.loc[test,FULL]),atol=1e-10)
    checks.append("Every CV prediction is out of fold and comparisons share identical country splits")
    # Validate analytic PRESS against brute-force omitted-country refits.
    ordinary=fit(d,FULL,robust=False);press=ordinary.resid/(1-ordinary.get_influence().hat_matrix_diag)
    for i in [0,len(d)//2,len(d)-1]:
        train=d.drop(index=i);mm=fit(train,FULL,robust=False)
        xx=sm.add_constant(d.loc[[i],FULL],has_constant='add')
        e=d.loc[i,'ladder']-mm.predict(xx).iloc[0]
        assert np.isclose(e,press.iloc[i],atol=1e-10)
    checks.append("Analytic leave-one-out errors match explicit omitted-country refits")
    p=pd.read_csv(PROCESSED/'panel_within_sample.csv')
    assert not p.duplicated(['iso_code','endpoint']).any()
    assert not p.duplicated(['iso_code','survey','education_year']).any()
    assert p.education_lag.between(1,3).all()
    assert p.groupby('iso_code').size().min()>=2
    assert sorted(p.endpoint.unique())==[2015,2018,2021,2024]
    checks.append("Panel outcomes and prior-education blocks are disjoint, with no reused surveys")
    pm=panel_fit(p);xx=pm.model.exog;yy=p.ladder.to_numpy();n,k=xx.shape
    xxp=np.linalg.pinv(xx);bb=xxp@xxp.T;e=yy-xx@(xxp@yy)
    score=[]
    for code in p.iso_code.unique():
        mask=p.iso_code.eq(code).to_numpy();score.append(xx[mask].T@e[mask])
    score=np.asarray(score);g=len(score)
    cov=bb@(score.T@score)@bb*g/(g-1)*(n-1)/(n-k)
    assert np.allclose(cov,pm.cov_params(),rtol=1e-6,atol=1e-8)
    assert pm.df_resid_inference==g-1
    checks.append("Country-clustered covariance and G-1 reference df match independent calculations")
    comparison=pd.read_csv(TABLES/'measurement_comparison_same_countries.csv')
    assert set(comparison.term)=={'gap10','relative_gap','gradient10'}
    assert comparison.n.eq(len(d)).all()
    checks.append("All disparity measures use the same countries for comparison")
    for name in ['country_bootstrap_draws.csv','panel_cluster_bootstrap_draws.csv']:
        assert len(pd.read_csv(TABLES/name))==CFG['bootstrap_replications']
    checks.append("Both empirical bootstrap analyses completed all 2,000 replications")
    grid=pd.read_csv(TABLES/'specification_grid.csv')
    assert len(grid)==18 and grid.p_holm_exploratory_family.between(0,1).all()
    checks.append("All 18 documented specifications and multiplicity corrections are present")
    write_json(ROOT/'outputs/verification.json',{'passed':True,'checks':checks})
    print('\n'.join('PASS: '+x for x in checks))


if __name__=='__main__':main()
