"""Compare three educational-disparity concepts on identical country samples."""
import pandas as pd
import matplotlib.pyplot as plt
from .analysis import PROCESSED, TABLES, C, fit, model_row, save_figure


def main():
    d=pd.read_csv(PROCESSED/'analysis_primary.csv')
    rows=[]
    for term in ['gap10','relative_gap','gradient10']:
        for label,features in [('Unadjusted',[term]),('Adjusted',['log_gdp','completion10','gini10',term])]:
            rows.append(model_row(label,fit(d,features),term))
    result=pd.DataFrame(rows)
    result.to_csv(TABLES/'measurement_comparison_same_countries.csv',index=False)
    plot=result[result.model.eq('Unadjusted')]
    labels={'relative_gap':'Relative completion gap','gap10':'Absolute completion gap','gradient10':'Five-quintile rank gradient'}
    fig,ax=plt.subplots(figsize=(8,3.6))
    ax.barh([labels[t] for t in plot.term],plot.r2,color=[C['amber'],C['blue'],C['purple']])
    for j,(_,row) in enumerate(plot.iterrows()):ax.text(row.r2+.01,j,f'{row.r2:.3f}',va='center')
    ax.set(xlim=(0,.5),xlabel='Unadjusted in-sample R-squared',title=f'Different disparity measures on the same {len(d)} countries')
    ax.spines[['top','right']].set_visible(False)
    fig.tight_layout();save_figure(fig,'13_measurement_comparison')
    print(result.to_string(index=False))


if __name__=='__main__':main()
