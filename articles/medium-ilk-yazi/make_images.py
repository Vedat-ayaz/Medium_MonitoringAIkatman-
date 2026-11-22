# Medium için sade görseller: gerçek ekran görüntüleri (shots/) + açık zeminli sade grafikler
import json, collections, os
from PIL import Image, ImageOps
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
for f in os.listdir("/usr/share/fonts/opentype/inter"): fm.fontManager.addfont("/usr/share/fonts/opentype/inter/"+f)
O="img/"; INK="#242424"; MUT="#757575"; ACC="#e0623a"; GRY="#dedad3"; DK="#6e6a64"
plt.rcParams.update({"font.family":"Inter","axes.spines.top":False,"axes.spines.right":False,"axes.spines.left":False,"axes.edgecolor":"#d6d3cc","text.color":INK,"axes.labelcolor":MUT,"xtick.color":MUT,"ytick.color":MUT})
def border(im,pad=0,col=(215,215,215)): return ImageOps.expand(im.convert("RGB"),border=3,fill=col)

# real screenshots
z=Image.open("shots/zbx-crop.png").convert("RGB"); p=Image.open("shots/prom-alerts.png").convert("RGB")
border(z).save(O+"02-zabbix-problems.png"); border(p).save(O+"01-prometheus-alerts.png")
border(Image.open("shots/prom-graph.png")).save(O+"03-prometheus-cpu.png")
# kapak: neredeyse yazısız. 100 alarm, 7'si turuncu.
fig=plt.figure(figsize=(16,8.4),dpi=125,facecolor="#FAF7F2"); ax=fig.add_axes([0,0,1,1]); ax.set_xlim(0,1600); ax.set_ylim(0,840); ax.axis("off")
x0,y0,d,g=130,95,56,12
for i in range(100):
    r,c=divmod(i,10); x=x0+c*(d+g); y=y0+(9-r)*(d+g)
    ax.add_patch(plt.Circle((x+d/2,y+d/2),d/2-2,color=ACC if i<7 else "#dcd5c8"))
ax.text(960,455,"7",fontsize=210,color=ACC,fontweight="bold",va="center")
ax.text(1130,420,"/ 100",fontsize=70,color="#1c1c1c",fontweight="bold",va="center")
ax.text(965,200,"Monitoring'e AI Katmanı",fontsize=18,color="#6b6558",va="center")
ax.text(965,160,"sentetik veri, 30 gün",fontsize=14,color="#9a937f",va="center")
fig.savefig(O+"00-kapak.png",facecolor="#FAF7F2"); plt.close()

# charts: sade, yumuşak renk, doğrudan etiket, ızgara yok
def clean(ax,y=False):
    ax.tick_params(length=0); ax.set_axisbelow(True)
    if not y: ax.set_yticks([]) 
ev=[json.loads(l) for l in open("../../data/samples/synthetic_30d.jsonl")]
cnt=collections.Counter(e["rule"] for e in ev); rules=[r for r,_ in cnt.most_common()]
fig,ax=plt.subplots(figsize=(10,5.4),dpi=150)
ax.barh(range(len(rules)),[cnt[r] for r in rules],color=[ACC if i<3 else GRY for i in range(len(rules))],height=.62)
ax.set_yticks(range(len(rules))); ax.set_yticklabels(rules,fontsize=11); ax.invert_yaxis(); ax.tick_params(length=0)
ax.set_xticks([])
for sp in ax.spines.values(): sp.set_visible(False)
for i,r in enumerate(rules): ax.text(cnt[r]+25,i,f"{cnt[r]:,}".replace(",","."),va="center",fontsize=11,color=INK if i<3 else MUT,fontweight="bold" if i<3 else "normal")
ax.set_xlim(0,2200)
ax.text(1150,6.3,"İlk üç kural tüm alarmların\n%93'ünü üretiyor",fontsize=16,color=ACC,fontweight="bold",va="center",linespacing=1.4)
ax.text(0,-1.1,"Kural başına alarm sayısı, 30 gün (sentetik veri)",fontsize=11,color=MUT,transform=ax.transData)
fig.tight_layout(); fig.savefig(O+"04-pareto.png"); plt.close()

def bars(ax,labels,vals,cols,fmt,ymax):
    b=ax.bar(labels,vals,color=cols,width=.5)
    for r,v in zip(b,vals): ax.text(r.get_x()+r.get_width()/2,v+ymax*.02,fmt(v),ha="center",fontsize=20,fontweight="bold",color=INK)
    ax.set_ylim(0,ymax); ax.set_yticks([]); ax.tick_params(length=0,labelsize=12)
    for sp in ax.spines.values(): sp.set_visible(False)
    ax.spines["bottom"].set_visible(True); ax.spines["bottom"].set_color("#d6d3cc")
fig,ax=plt.subplots(figsize=(8,4.8),dpi=150)
bars(ax,["Zamana bakan\ngruplama","Gerçek\nincident"],[601,12],[ACC,DK],lambda v:f"{v}",700)
ax.text(0,270,"589'u\nsadece gürültü",ha="center",color="white",fontsize=13,fontweight="bold",linespacing=1.4)
fig.tight_layout(); fig.savefig(O+"05-burst.png"); plt.close()

fig,(a,b)=plt.subplots(1,2,figsize=(10,4.8),dpi=150)
bars(a,["Önce","Susturunca"],[5570,370],[GRY,DK],lambda v:f"{v:,}".replace(",","."),6500); a.set_title("Alarm sayısı",loc="left",fontsize=13,color=MUT)
bars(b,["Aksiyon gerektiren\noran","Kaybolan\ngerçek sinyal"],[59,42],[DK,ACC],lambda v:f"%{v}",70); b.set_title("Yüzde",loc="left",fontsize=13,color=MUT)
fig.tight_layout(w_pad=4); fig.savefig(O+"06-susturma-bedeli.png"); plt.close()

fig,ax=plt.subplots(figsize=(8,3.6),dpi=150)
b=ax.barh(["Ham 30 günlük\nJSONL","Özet rapor"],[445000,700],color=[ACC,DK],height=.5)
ax.set_xscale("log"); ax.invert_yaxis(); ax.set_xlim(100,3e7); ax.set_xticks([]); ax.minorticks_off(); ax.tick_params(length=0,labelsize=12)
for sp in ax.spines.values(): sp.set_visible(False)
ax.text(445000*1.2,0,"~445.000 token",va="center",fontsize=15,fontweight="bold")
ax.text(700*1.6,1,"~700 token",va="center",fontsize=15,fontweight="bold")
ax.text(100,-.62,"Token sayısı (tahmin, karakter/3,5). Eksen logaritmik.",fontsize=10.5,color=MUT)
fig.tight_layout(); fig.savefig(O+"07-token.png"); plt.close()

from matplotlib.patches import FancyBboxPatch
def box(ax,x,y,w,h,ec,fc="none",lw=1.8): ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0,rounding_size=.15",fill=fc!="none",fc=fc,ec=ec,lw=lw))
with plt.xkcd(scale=.5,length=140,randomness=1):
    fig,ax=plt.subplots(figsize=(10,4.6),dpi=150); ax.axis("off"); ax.set_xlim(0,10); ax.set_ylim(0,4.6)
    for i,n in enumerate(["Zabbix","Prometheus","ELK"]):
        y=3.2-i*1.3; box(ax,.2,y,2,.8,DK); ax.text(1.2,y+.4,n,ha="center",va="center",fontsize=15)
        ax.annotate("",xy=(3.8,2.3),xytext=(2.25,y+.4),arrowprops=dict(arrowstyle="->",lw=1.6,color=MUT))
    box(ax,3.9,1.7,2.2,1.2,ACC,"#fdeee8",2.2); ax.text(5,2.3,"ortak şema\n(AlertEvent)",ha="center",va="center",fontsize=15,color=ACC)
    ax.annotate("",xy=(6.9,2.3),xytext=(6.2,2.3),arrowprops=dict(arrowstyle="->",lw=1.6,color=MUT))
    box(ax,7,.5,2.8,3.6,DK); ax.text(8.4,3.7,"8 sayı",ha="center",fontsize=15,fontweight="bold")
    for i,m in enumerate(["hacim","yoğunlaşma","gürültü oranı","aksiyon oranı","MTTA / MTTR","gece sayfalama","korelasyon"]): ax.text(7.25,3.25-i*.4,m,fontsize=12,color=INK)
    fig.savefig(O+"08-akis.png",bbox_inches="tight"); plt.close()

with plt.xkcd(scale=.5,length=140,randomness=1):
    fig,ax=plt.subplots(figsize=(10,4.4),dpi=150); ax.axis("off"); ax.set_xlim(0,10); ax.set_ylim(0,4.4)
    for x,t,items,c,fc in [(.2,"Sezon 1: gör ve anla",["alarm sağlık raporu (bu yazı)","veri hattı","AI ile eşik","alert tasarımı","hızlı korelasyon","kök neden ajanı"],DK,"#f4f2ee"),(5.2,"Sezon 2: hatırla, harekete geç",["vaka hafızası","benzer vakadan aksiyon","güvenli yürütme","değerlendirme, maliyet","yerel model, fine-tune","kapanış, satıcı karşılaştırması"],ACC,"#fdeee8")]:
        box(ax,x,.2,4.6,4,c,fc); ax.text(x+.25,3.75,t,fontsize=13,fontweight="bold",color=c)
        for i,it in enumerate(items): ax.text(x+.25,3.15-i*.48,f"{i+1}. {it}",fontsize=12,color=INK)
    fig.savefig(O+"09-yol-haritasi.png",bbox_inches="tight"); plt.close()
