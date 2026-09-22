"""tiered-autonomy-sim: a reproducible Monte Carlo evaluation of tiered,
blast-radius-aware autonomy for CI/CD self-healing agents.

All parameters are synthetic and explicitly configurable. Nothing here is
derived from production data.
"""
from dataclasses import dataclass, field, replace
import math, random, statistics

# Remediation categories: (share of incidents, blast-radius range)
CATEGORIES = {
    "flaky_test_retry":  (0.35, (0.001, 0.01)),
    "dependency_bump":   (0.25, (0.01, 0.10)),
    "config_change":     (0.15, (0.05, 0.30)),
    "infra_scaling":     (0.12, (0.05, 0.20)),
    "secret_rotation":   (0.08, (0.30, 0.80)),
    "schema_migration":  (0.05, (0.40, 1.00)),
}

@dataclass
class Params:
    n_incidents: int = 1000
    est_noise_sigma: float = 0.5     # lognormal noise on blast-radius estimate
    miscalibration: float = 0.3      # confidence overstates correctness by miscal*B
    verify_catch: float = 0.8        # P(verification gate catches a wrong action)
    verify_residual: float = 0.1     # fraction of B incurred when gate catches & reverts
    human_catch: float = 0.95        # P(human reviewer rejects a wrong proposal)

@dataclass
class Incident:
    category: str
    blast: float
    blast_est: float
    confidence: float
    correct: bool

def generate(p: Params, rng: random.Random):
    names = list(CATEGORIES); weights = [CATEGORIES[k][0] for k in names]
    out = []
    for _ in range(p.n_incidents):
        cat = rng.choices(names, weights)[0]
        lo, hi = CATEGORIES[cat][1]
        b = rng.uniform(lo, hi)
        b_est = min(1.0, b * math.exp(rng.gauss(0.0, p.est_noise_sigma)))
        c = rng.betavariate(8, 2)                        # agents are usually confident
        q = max(0.0, min(1.0, c - p.miscalibration * b)) # true P(action correct)
        out.append(Incident(cat, b, b_est, c, rng.random() < q))
    return out

# Tiers: 0 Observe (human acts), 1 Propose (human approves), 2 Execute+verify, 3 Execute unsupervised
HUMAN_LOAD = {0: 2.0, 1: 1.0, 2: 0.0, 3: 0.0}

def policy_human_only(i): return 1
def policy_full_autonomy(i): return 3
def policy_conf_gated(i): return 3 if i.confidence >= 0.8 else 1
def policy_conf_gated_verify(i): return 2 if i.confidence >= 0.8 else 1

@dataclass
class TierThresholds:
    t3_blast: float = 0.02
    t3_conf: float = 0.7
    t2_blast: float = 0.20
    t1_blast: float = 0.50

def make_tiered(th: TierThresholds = TierThresholds(), use_true_blast=False):
    def pol(i):
        b = i.blast if use_true_blast else i.blast_est
        if b < th.t3_blast and i.confidence >= th.t3_conf: return 3
        if b < th.t2_blast: return 2
        if b < th.t1_blast: return 1
        return 0
    return pol

def evaluate(policy, incidents, p: Params, rng: random.Random):
    harm = 0.0; escapes = 0; load = 0.0; autonomous = 0
    for i in incidents:
        tier = policy(i)
        load += HUMAN_LOAD[tier]
        if tier >= 2: autonomous += 1
        if i.correct: continue
        if tier == 3:
            harm += i.blast; escapes += 1
        elif tier == 2:
            if rng.random() < p.verify_catch: harm += p.verify_residual * i.blast
            else: harm += i.blast; escapes += 1
        else:  # tiers 0 and 1: human reviews
            if rng.random() >= p.human_catch: harm += i.blast; escapes += 1
    n = len(incidents)
    return dict(harm=harm, escapes=escapes, load=load, autonomy=100.0*autonomous/n)

POLICIES = {
    "Human review of all": policy_human_only,
    "Full autonomy": policy_full_autonomy,
    "Confidence-gated": policy_conf_gated,
    "Confidence-gated + verify": policy_conf_gated_verify,
    "Tiered (estimated blast)": make_tiered(),
    "Tiered (oracle blast)": make_tiered(use_true_blast=True),
}

def run(p: Params = Params(), seeds=range(30), policies=POLICIES):
    res = {k: [] for k in policies}
    for s in seeds:
        inc = generate(p, random.Random(s))
        for k, pol in policies.items():
            res[k].append(evaluate(pol, inc, p, random.Random(10_000 + s)))
    summary = {}
    for k, rows in res.items():
        summary[k] = {m: (statistics.fmean(r[m] for r in rows), statistics.stdev(r[m] for r in rows)) for m in rows[0]}
    return summary
