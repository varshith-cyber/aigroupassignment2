"""
Problem 1 - Smart Home Energy Consumption using a Bayesian Network.

pgmpy could not be installed in our environment, so the network, exact
inference (enumeration), d-separation, ancestral sampling, MLE and BDeu
estimation are all written by hand with numpy. The maths is the same
as what the library would do.

Group members: <Name 1> (<Roll No>), <Name 2> (<Roll No>), ...
"""
import itertools
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SEED = 42
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")
os.makedirs(OUT, exist_ok=True)

# ----------------------------------------------------------------------
# Network definition
# ----------------------------------------------------------------------
STATES = {
    "W": ["Hot", "Mild", "Cold"],
    "D": ["Weekday", "Weekend"],
    "O": ["High", "Low"],
    "A": ["On", "Off"],
    "L": ["Heavy", "Light"],
    "E": ["High", "Low"],
}
PARENTS = {
    "W": [], "D": [], "O": ["D"], "A": ["W", "O"], "L": ["O"], "E": ["A", "L"],
}
ORDER = ["W", "D", "O", "A", "L", "E"]          # topological order
NAMES = {"W": "Weather", "D": "DayType", "O": "Occupancy",
         "A": "AC", "L": "ApplianceLoad", "E": "Energy"}


def make_cpd(var, first_state_probs):
    """first_state_probs: dict parent-config tuple -> P(first state of var).
    Returns dict parent-config -> list of probabilities over STATES[var]."""
    cpd = {}
    for cfg, p in first_state_probs.items():
        cpd[cfg] = [p, 1 - p]
    return cpd


EXPERT = {
    "W": {(): [0.50, 0.30, 0.20]},
    "D": {(): [0.70, 0.30]},
    "O": make_cpd("O", {("Weekday",): 0.45, ("Weekend",): 0.80}),
    "A": make_cpd("A", {
        ("Hot", "High"): 0.90, ("Hot", "Low"): 0.60,
        ("Mild", "High"): 0.40, ("Mild", "Low"): 0.15,
        ("Cold", "High"): 0.10, ("Cold", "Low"): 0.05}),
    "L": make_cpd("L", {("High",): 0.75, ("Low",): 0.35}),
    "E": make_cpd("E", {
        ("On", "Heavy"): 0.92, ("On", "Light"): 0.68,
        ("Off", "Heavy"): 0.55, ("Off", "Light"): 0.12}),
}


def parent_configs(var):
    return list(itertools.product(*[STATES[p] for p in PARENTS[var]]))


def check_cpds(model, label="model"):
    """Every CPT row must sum to 1 and every parent configuration must exist."""
    ok = True
    for v in ORDER:
        cfgs = parent_configs(v)
        for c in cfgs:
            if c not in model[v]:
                print(f"  [{label}] missing row {NAMES[v]} | {c}")
                ok = False
                continue
            s = sum(model[v][c])
            if abs(s - 1.0) > 1e-9 or len(model[v][c]) != len(STATES[v]):
                print(f"  [{label}] bad row {NAMES[v]} | {c}: sum={s}")
                ok = False
    print(f"  [{label}] all CPT rows valid and sum to 1: {ok}")
    return ok


# ----------------------------------------------------------------------
# Exact inference by enumeration over the joint distribution
# ----------------------------------------------------------------------
def joint_prob(model, assignment):
    p = 1.0
    for v in ORDER:
        cfg = tuple(assignment[q] for q in PARENTS[v])
        p *= model[v][cfg][STATES[v].index(assignment[v])]
    return p


def all_assignments():
    for combo in itertools.product(*[STATES[v] for v in ORDER]):
        yield dict(zip(ORDER, combo))


def query(model, target, value, evidence=None):
    """P(target=value | evidence) by summing the full joint."""
    evidence = evidence or {}
    num = den = 0.0
    for a in all_assignments():
        if any(a[k] != v for k, v in evidence.items()):
            continue
        p = joint_prob(model, a)
        den += p
        if a[target] == value:
            num += p
    return num / den if den > 0 else float("nan")


QUERIES = [
    ("Q1", "P(E=High)",                          "E", "High", {}),
    ("Q2", "P(E=High | W=Hot)",                  "E", "High", {"W": "Hot"}),
    ("Q3", "P(E=High | D=Weekend)",              "E", "High", {"D": "Weekend"}),
    ("Q4", "P(E=High | W=Cold, O=High)",         "E", "High", {"W": "Cold", "O": "High"}),
    ("Q5", "P(W=Hot | E=High)",                  "W", "Hot",  {"E": "High"}),
    ("Q6", "P(A=On | E=High)",                   "A", "On",   {"E": "High"}),
    ("Q7", "P(A=On | E=High, L=Heavy)",          "A", "On",   {"E": "High", "L": "Heavy"}),
]


def run_queries(model):
    return [query(model, t, val, ev) for _, _, t, val, ev in QUERIES]


# ----------------------------------------------------------------------
# d-separation (moralised ancestral graph method)
# ----------------------------------------------------------------------
def ancestors(nodes):
    seen, stack = set(nodes), list(nodes)
    while stack:
        n = stack.pop()
        for p in PARENTS[n]:
            if p not in seen:
                seen.add(p)
                stack.append(p)
    return seen


def d_separated(x, y, z):
    keep = ancestors({x, y} | set(z))
    edges = set()
    for v in keep:
        ps = [p for p in PARENTS[v] if p in keep]
        for p in ps:
            edges.add(frozenset((p, v)))
        for a, b in itertools.combinations(ps, 2):      # marry parents
            edges.add(frozenset((a, b)))
    # remove observed nodes, then check connectivity x -> y
    alive = keep - set(z)
    frontier, seen = [x], {x}
    while frontier:
        n = frontier.pop()
        for e in edges:
            if n in e:
                (m,) = e - {n}
                if m in alive and m not in seen:
                    seen.add(m)
                    frontier.append(m)
    return y not in seen


# ----------------------------------------------------------------------
# Ancestral sampling (our own implementation)
# ----------------------------------------------------------------------
def ancestral_sample(model, n, seed):
    rng = np.random.default_rng(seed)
    data = {v: [] for v in ORDER}
    for _ in range(n):
        row = {}
        for v in ORDER:                              # topological order
            cfg = tuple(row[p] for p in PARENTS[v])
            probs = model[v][cfg]
            row[v] = STATES[v][rng.choice(len(probs), p=probs)]
        for v in ORDER:
            data[v].append(row[v])
    return data


# ----------------------------------------------------------------------
# Parameter learning
# ----------------------------------------------------------------------
def counts_for(data, var):
    cnt = {c: np.zeros(len(STATES[var])) for c in parent_configs(var)}
    n = len(data[var])
    for i in range(n):
        cfg = tuple(data[p][i] for p in PARENTS[var])
        cnt[cfg][STATES[var].index(data[var][i])] += 1
    return cnt


def learn_mle(data):
    model = {}
    for v in ORDER:
        cnt = counts_for(data, v)
        model[v] = {}
        for c, arr in cnt.items():
            tot = arr.sum()
            # a parent configuration never seen in the data has no estimate;
            # fall back to uniform so the CPT is still a valid distribution
            model[v][c] = list(arr / tot) if tot > 0 else [1 / len(arr)] * len(arr)
    return model


def learn_bdeu(data, ess=10):
    """BDeu: pseudo-count for state k under parent config j is
    ess / (r_v * q_v), r = #states of v, q = #parent configurations."""
    model = {}
    for v in ORDER:
        cnt = counts_for(data, v)
        r, q = len(STATES[v]), len(cnt)
        alpha = ess / (r * q)
        model[v] = {c: list((arr + alpha) / (arr.sum() + r * alpha))
                    for c, arr in cnt.items()}
    return model


# ----------------------------------------------------------------------
# Printing helpers
# ----------------------------------------------------------------------
def print_ac_cpt(models):
    print("\n  AC CPT  P(AC = On | Weather, Occupancy)")
    print(f"  {'Weather':8s}{'Occ':6s}" + "".join(f"{n:>10s}" for n in models))
    for cfg in parent_configs("A"):
        row = "".join(f"{m['A'][cfg][0]:10.4f}" for m in models.values())
        print(f"  {cfg[0]:8s}{cfg[1]:6s}{row}")


def draw_network(path):
    pos = {"W": (0, 3.0), "D": (3, 3.0), "O": (3, 1.5), "A": (1.5, 0.4),
           "L": (4.5, 0.4), "E": (3, -1.0)}
    fig, ax = plt.subplots(figsize=(7, 6))
    for v in ORDER:
        for p in PARENTS[v]:
            ax.annotate("", xy=pos[v], xytext=pos[p],
                        arrowprops=dict(arrowstyle="-|>", lw=1.6, shrinkA=38, shrinkB=38,
                                        mutation_scale=16, color="#333333"))
    for v, (x, y) in pos.items():
        ax.scatter([x], [y], s=3200, color="#cfe2f3", edgecolor="#3d6a99", zorder=3)
        ax.text(x, y, NAMES[v], ha="center", va="center", fontsize=9, zorder=4)
    ax.set_xlim(-1, 5.5); ax.set_ylim(-1.7, 3.6); ax.axis("off")
    ax.set_title("Smart-home Bayesian Network")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


# ----------------------------------------------------------------------
def main():
    print("=" * 70)
    print("PART A - Expert network")
    print("=" * 70)
    print("Edges:", [(NAMES[p], NAMES[v]) for v in ORDER for p in PARENTS[v]])
    check_cpds(EXPERT, "expert")
    draw_network(os.path.join(OUT, "network_structure.png"))

    expert_vals = run_queries(EXPERT)
    for (qid, text, *_), val in zip(QUERIES, expert_vals):
        print(f"  {qid}: {text:34s} = {val:.6f}")

    print("\nExplaining away: Q6 vs Q7")
    print(f"  P(AC=On | E=High)               = {expert_vals[5]:.6f}")
    print(f"  P(AC=On | E=High, Load=Heavy)   = {expert_vals[6]:.6f}")
    print("  Seeing a heavy appliance load already gives one reason for high energy,")
    print("  so the high reading is less evidence that the AC was on -> probability falls.")

    # hand calculation of Q1
    print("\nQ1 by hand (sum over A and L, with O marginalised first)")
    pO_high = 0.7 * 0.45 + 0.3 * 0.80
    print(f"  P(O=High) = 0.7*0.45 + 0.3*0.80 = {pO_high:.4f}")
    pA_given_O = {}
    for o in ["High", "Low"]:
        pA_given_O[o] = (0.5 * EXPERT["A"][("Hot", o)][0]
                         + 0.3 * EXPERT["A"][("Mild", o)][0]
                         + 0.2 * EXPERT["A"][("Cold", o)][0])
        print(f"  P(A=On | O={o}) = 0.5*{EXPERT['A'][('Hot', o)][0]} + "
              f"0.3*{EXPERT['A'][('Mild', o)][0]} + 0.2*{EXPERT['A'][('Cold', o)][0]}"
              f" = {pA_given_O[o]:.4f}")
    pL_given_O = {"High": 0.75, "Low": 0.35}
    total = 0.0
    for o, po in [("High", pO_high), ("Low", 1 - pO_high)]:
        for a_on, pa in [("On", pA_given_O[o]), ("Off", 1 - pA_given_O[o])]:
            for l_h, pl in [("Heavy", pL_given_O[o]), ("Light", 1 - pL_given_O[o])]:
                pe = EXPERT["E"][(a_on, l_h)][0]
                term = po * pa * pl * pe
                total += term
                print(f"   O={o:4s} A={a_on:3s} L={l_h:5s}: "
                      f"{po:.4f}*{pa:.4f}*{pl:.4f}*{pe:.2f} = {term:.6f}")
    print(f"  Sum = {total:.6f}   code gives {expert_vals[0]:.6f}   "
          f"match: {abs(total - expert_vals[0]) < 1e-9}")

    print("\n" + "=" * 70)
    print("PART B - Conditional independence")
    print("=" * 70)
    tests = [
        ("Weather _|_ DayType", "W", "D", []),
        ("Weather _|_ DayType | Energy", "W", "D", ["E"]),
        ("Weather _|_ ApplianceLoad | Occupancy", "W", "L", ["O"]),
    ]
    for name, x, y, z in tests:
        print(f"  {name:42s} d-separated: {d_separated(x, y, z)}")
    print("  Numerical checks:")
    a = query(EXPERT, "W", "Hot", {"E": "High"})
    b = query(EXPERT, "W", "Hot", {"E": "High", "D": "Weekend"})
    print(f"   P(W=Hot | E=High)                 = {a:.6f}")
    print(f"   P(W=Hot | E=High, D=Weekend)      = {b:.6f}   (differ -> dependent given E)")
    print(f"   P(W=Hot)                          = {query(EXPERT, 'W', 'Hot'):.6f}")
    print(f"   P(W=Hot | D=Weekend)              = {query(EXPERT, 'W', 'Hot', {'D': 'Weekend'}):.6f}")
    c = query(EXPERT, "W", "Hot", {"O": "High"})
    d = query(EXPERT, "W", "Hot", {"O": "High", "L": "Heavy"})
    print(f"   P(W=Hot | O=High)                 = {c:.6f}")
    print(f"   P(W=Hot | O=High, L=Heavy)        = {d:.6f}   (equal -> independent)")

    print("\n" + "=" * 70)
    print(f"PART C - Synthetic data (seed = {SEED})")
    print("=" * 70)
    sizes = [500, 5000, 20000]
    datasets = {}
    for n in sizes:
        data = ancestral_sample(EXPERT, n, SEED)
        datasets[n] = data
        print(f"\n  n = {n}")
        for s in STATES["W"]:
            k = data["W"].count(s)
            print(f"    Weather={s:5s} freq = {k / n:.4f}  (true {EXPERT['W'][()][STATES['W'].index(s)]:.2f})")
        print("    (Weather, Occupancy) counts:")
        for w in STATES["W"]:
            for o in STATES["O"]:
                k = sum(1 for i in range(n) if data["W"][i] == w and data["O"][i] == o)
                print(f"      ({w:4s}, {o:4s}) : {k}")

    print("\n" + "=" * 70)
    print("PART D / E - Learning and comparison")
    print("=" * 70)
    mad = {"MLE": [], "Bayesian": []}
    first_table_rows = None
    for n in sizes:
        mle = learn_mle(datasets[n])
        bay = learn_bdeu(datasets[n], ess=10)
        print(f"\n--- n = {n} ---")
        print_ac_cpt({"Expert": EXPERT, "MLE": mle, "BDeu": bay})
        vm, vb = run_queries(mle), run_queries(bay)
        print(f"\n  {'Query':6s}{'Expert':>10s}{'MLE':>10s}{'Bayes':>10s}{'|Diff|MLE':>12s}{'|Diff|Bay':>12s}")
        dm, db = [], []
        for (qid, *_), e, m, b in zip(QUERIES, expert_vals, vm, vb):
            dm.append(abs(e - m)); db.append(abs(e - b))
            print(f"  {qid:6s}{e:10.4f}{m:10.4f}{b:10.4f}{dm[-1]:12.4f}{db[-1]:12.4f}")
        mad["MLE"].append(np.mean(dm)); mad["Bayesian"].append(np.mean(db))
        print(f"  mean |diff|: MLE={mad['MLE'][-1]:.5f}  Bayesian={mad['Bayesian'][-1]:.5f}")
        if n == 500:
            worst = int(np.argmax(dm))
            print(f"  Largest MLE error at n=500: {QUERIES[worst][0]} ({QUERIES[worst][1]})")
            ev = QUERIES[worst][4]
            cnt = sum(all(datasets[500][k][i] == v for k, v in ev.items()) for i in range(500))
            print(f"  rows in the data matching that evidence: {cnt} of 500")
            print(f"  Per-query MLE errors: " + ", ".join(f"{QUERIES[i][0]}={dm[i]:.4f}" for i in range(7)))

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(sizes, mad["MLE"], "o-", label="MLE")
    ax.plot(sizes, mad["Bayesian"], "s--", label="Bayesian (BDeu, ESS=10)")
    ax.set_xscale("log"); ax.set_xlabel("dataset size"); ax.set_ylabel("mean |difference| over Q1-Q7")
    ax.set_title("Estimation error vs dataset size"); ax.grid(alpha=.3); ax.legend()
    fig.savefig(os.path.join(OUT, "mad_vs_size.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("\nSaved plots to", OUT)


if __name__ == "__main__":
    main()
