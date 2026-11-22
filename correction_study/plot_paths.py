"""Render the language-neutral four-panel atlas figure from index-paths.json."""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MultipleLocator


def render(folder):
    study=json.loads((folder/'index-paths.json').read_text())
    figure, axes=plt.subplots(2,2,figsize=(10,7),sharex=True,sharey=True,layout='constrained')
    figure.patch.set_facecolor('#101b27')
    extent=max(abs(value) for r in study['indices'].values() for value in r.get('path',[]))
    limit=5*(int(extent/5)+1)
    for ax,r in zip(axes.flat,study['indices'].values()):
        ax.set_facecolor('#142333')
        ax.tick_params(colors='#cad8e5',labelsize=9)
        for spine in ax.spines.values():
            spine.set_color('#425466')
        ax.set(xlim=(0,63),ylim=(-limit,limit),xticks=[0,21,42,63])
        ax.yaxis.set_major_locator(MultipleLocator(5 if limit<=20 else 10))
        ax.yaxis.set_major_formatter(FuncFormatter(lambda y,_:f'{y:g}%'))
        ax.grid(axis='y',color='#334559',alpha=.65)
        ax.axhline(0,color='#8697a8',lw=.8)
        ax.set_title(r['name'].replace(' Industrial Average',''),loc='left',color='white',weight='bold',fontsize=15,pad=12)
        if r['winner'] is None:
            continue
        color={'up':'#63ddbb','down':'#ffa382','range':'#aabfee'}[r['winner']]
        label={'up':'+5%','down':'−5%','range':'±5%'}[r['winner']]
        ax.set_title(f"{label}   ·   {100*r['hits']/r['n']:.0f}%",loc='right',color=color,fontsize=12,pad=12)
        values=r['path']
        ax.plot(values,color=color,lw=2)
        ax.scatter(0,0,s=22,color='white',zorder=3,clip_on=False)
        if r['winner']!='range':
            sign=1 if r['winner']=='up' else -1
            first=next(i for i,v in enumerate(values) if sign*v>=5)
            ax.axhline(sign*5,color=color,lw=.9,ls='--',alpha=.7)
            ax.scatter(first,values[first],s=42,color=color,edgecolor='#142333',zorder=3)
        ax.text(.02,.04,f"{r['exemplar']}   ·   {r['hits']}/{r['n']}",transform=ax.transAxes,
                color='#f4f6fa',fontsize=10,bbox=dict(facecolor='#142333',edgecolor='none',alpha=.85))
    figure.savefig(folder/'index-paths.png',dpi=150)
    plt.close(figure)


if __name__=='__main__':
    render(Path(sys.argv[1]))
