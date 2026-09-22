import sys, json; sys.path.insert(0,'.')
from dataclasses import replace
from tiered_autonomy_sim.sim import *
out={}
# E1 main
out["main"]=run()
# E2 frontiers
front={"conf":[], "tiered":[]}
for c in [0.5,0.6,0.7,0.75,0.8,0.85,0.9,0.95,0.99]:
    pol=(lambda c: (lambda i: 2 if i.confidence>=c else 1))(c)
    s=run(policies={"x":pol})["x"]; front["conf"].append((c, s["load"][0], s["harm"][0], s["escapes"][0]))
for t2 in [0.03,0.05,0.1,0.2,0.3,0.4,0.5]:
    pol=make_tiered(TierThresholds(t2_blast=t2, t1_blast=max(0.5,t2)))
    s=run(policies={"x":pol})["x"]; front["tiered"].append((t2, s["load"][0], s["harm"][0], s["escapes"][0]))
out["front"]=front
# E3 sensitivity
sens={}
for name,kw in [("sigma",[0.0,0.5,1.0,1.5]),("miscal",[0.0,0.3,0.6]),("verify",[0.6,0.8,0.95])]:
    rows=[]
    for v in kw:
        p=Params(**{ {"sigma":"est_noise_sigma","miscal":"miscalibration","verify":"verify_catch"}[name]: v})
        s=run(p, policies={"cv":POLICIES["Confidence-gated + verify"],"t":POLICIES["Tiered (estimated blast)"]})
        rows.append((v, s["cv"]["harm"][0], s["cv"]["load"][0], s["t"]["harm"][0], s["t"]["load"][0]))
    sens[name]=rows
out["sens"]=sens
# E4 harm by category for the two main policies
from collections import defaultdict
cat={}
for k in ["Confidence-gated + verify","Tiered (estimated blast)"]:
    agg=defaultdict(float); pol=POLICIES[k]
    for s in range(30):
        p=Params(); inc=generate(p, random.Random(s)); rng=random.Random(10000+s)
        for i in inc:
            t=pol(i)
            if i.correct: continue
            if t==3: agg[i.category]+=i.blast
            elif t==2:
                agg[i.category]+= p.verify_residual*i.blast if rng.random()<p.verify_catch else i.blast
            else:
                if rng.random()>=p.human_catch: agg[i.category]+=i.blast
    cat[k]={c:round(v/30,2) for c,v in agg.items()}
out["cat"]=cat
json.dump(out, open("results.json","w"), indent=1)
for k,v in out["main"].items(): print(k, {m:(round(a,2),round(b,2)) for m,(a,b) in v.items()})
print("FRONT conf", [(c,round(l),round(h,2)) for c,l,h,e in front["conf"]])
print("FRONT tier", [(c,round(l),round(h,2)) for c,l,h,e in front["tiered"]])
for n,r in sens.items(): print("SENS",n,[tuple(round(x,2) for x in row) for row in r])
print("CAT",cat)
