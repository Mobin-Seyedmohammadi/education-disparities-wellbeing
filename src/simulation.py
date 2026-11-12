"""A schematic measurement experiment, explicitly separate from real evidence.

This does not estimate the world's DGP. It shows a mathematical possibility:
normalizing a disparity by an attainment level connects it to development.
"""
import numpy as np
import pandas as pd
from scipy.special import expit
from scipy import stats
import matplotlib.pyplot as plt
from .analysis import TABLES, ROOT, C, CFG, write_json, save_figure


def estimate(y, exposure, prosperity=None):
    columns = [np.ones(len(y)), exposure]
    if prosperity is not None: columns.append(prosperity)
    x = np.column_stack(columns)
    xx = np.linalg.inv(x.T@x); b = xx@x.T@y
    e = y-x@b; h = np.einsum("ij,jk,ik->i", x,xx,x)
    meat = x.T@(((e/(1-h))**2)[:,None]*x)
    se = np.sqrt(np.diag(xx@meat@xx))
    p = 2*stats.t.sf(abs(b[1]/se[1]), len(y)-x.shape[1])
    return b[1],p


def main():
    rng=np.random.default_rng(CFG["seed"]+900)
    repetitions=1000;n=150;records=[]
    for rep in range(repetitions):
        z=rng.normal(size=n)
        midpoint=.2+.6*expit(z)
        absolute=rng.uniform(.04,.16,size=n)
        q1=midpoint-absolute/2;q5=midpoint+absolute/2
        assert (q1>=0).all() and (q5<=1).all()
        y=5+.9*z+rng.normal(0,.7,size=n)
        relative=absolute/midpoint
        for measure,exposure in [("Absolute gap",absolute),("Relative gap",relative)]:
            for adjusted,covariate in [(False,None),(True,z)]:
                beta,p=estimate(y,exposure,covariate)
                records.append({"replication":rep,"measure":measure,"adjusted_for_prosperity":adjusted,
                                "coefficient":beta,"p_value":p,"negative_p_below_05":int(beta<0 and p<.05),
                                "p_below_05":int(p<.05)})
    draws=pd.DataFrame(records);draws.to_csv(TABLES/"simulation_draws.csv",index=False)
    summary=draws.groupby(["measure","adjusted_for_prosperity"],as_index=False).agg(
        mean_coefficient=("coefficient","mean"),negative_association_detection_rate=("negative_p_below_05","mean"),
        any_sign_detection_rate=("p_below_05","mean"))
    summary.to_csv(TABLES/"simulation_summary.csv",index=False)
    write_json(ROOT/"outputs/simulation_design.json",{
        "replications":repetitions,"countries_per_replication":n,"seed":CFG["seed"]+900,
        "dgp":{"prosperity_z":"N(0,1)","completion_midpoint":"0.2 + 0.6 * logistic(z)",
               "absolute_gap":"Uniform(0.04,0.16), independent of z and noise",
               "q1":"midpoint - absolute_gap/2","q5":"midpoint + absolute_gap/2",
               "relative_gap":"absolute_gap/midpoint","life_evaluation":"5 + 0.9*z + Normal(0,0.7^2)"},
        "interpretation":"A deliberately schematic example of denominator coupling. Both inequality measures are valid but answer different descriptive questions. A nonzero unconditional relative-gap association is real in this simulated population, so it is not a false rejection of zero association. It cannot be interpreted as an education-disparity treatment effect. The experiment is not fitted to or a validation of the empirical DGP."})
    fig,ax=plt.subplots(figsize=(9,4.2))
    names=[];values=[];colors=[]
    for _,r in summary.iterrows():
        names.append(r.measure+(' + prosperity control' if r.adjusted_for_prosperity else ', unadjusted'))
        values.append(r.negative_association_detection_rate*100)
        colors.append(C["blue"] if r.adjusted_for_prosperity else C["amber"])
    ax.barh(names,values,color=colors)
    for i,v in enumerate(values):ax.text(v+1,i,f'{v:.1f}%',va='center')
    ax.set(xlim=(0,112),xlabel="Replications with a negative coefficient and p < 0.05 (%)",
           title="Denominator coupling in a schematic model, 1,000 replications")
    ax.spines[['top','right']].set_visible(False)
    fig.tight_layout();save_figure(fig,"11_measurement_simulation")
    print(summary.to_string(index=False))


if __name__=="__main__":main()
