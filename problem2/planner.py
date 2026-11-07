"""
Mini STRIPS planner + plan validator for the Mars rover task.

No PDDL planner (Fast Downward, pyperplan, VAL ...) could be installed in
our environment, so this file does the whole job:
  * parses Domain.pddl / Problem*.pddl (:strips + :typing subset)
  * grounds the actions
  * searches with three configurations
        - greedy best-first search with h_add   (satisficing)
        - A* with h_max                          (optimal, admissible)
        - breadth-first search                   (optimal, used as a cross-check)
  * validates each plan by simulating it step by step on the *lifted* actions

Usage:  python3 planner.py            (runs everything, writes ./outputs)
"""
import heapq
import itertools
import os
import sys
import time
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "outputs")
os.makedirs(OUT, exist_ok=True)

INF = 10 ** 9


# ----------------------------------------------------------------------
# PDDL parsing (s-expressions)
# ----------------------------------------------------------------------
def tokenize(text):
    lines = [l.split(";")[0] for l in text.splitlines()]
    text = " ".join(lines).replace("(", " ( ").replace(")", " ) ")
    return text.lower().split()


def read_sexp(tokens, i=0):
    if tokens[i] != "(":
        return tokens[i], i + 1
    out, i = [], i + 1
    while tokens[i] != ")":
        item, i = read_sexp(tokens, i)
        out.append(item)
    return out, i + 1


def parse_file(path):
    with open(path) as f:
        return read_sexp(tokenize(f.read()))[0]


def typed_list(items):
    """['a','b','-','t','c','-','u'] -> [('a','t'),('b','t'),('c','u')]"""
    out, pending, i = [], [], 0
    while i < len(items):
        if items[i] == "-":
            t = items[i + 1]
            out += [(n, t) for n in pending]
            pending, i = [], i + 2
        else:
            pending.append(items[i])
            i += 1
    out += [(n, "object") for n in pending]
    return out


def conj(expr):
    if expr[0] == "and":
        return expr[1:]
    return [expr]


class Action:
    def __init__(self, name, params, pre, add, dele):
        self.name, self.params = name, params          # params: [(var,type)]
        self.pre, self.add, self.dele = pre, add, dele  # lists of atom lists


def parse_domain(path):
    d = parse_file(path)
    actions, preds_in_effects = [], set()
    for sec in d[2:]:
        if sec[0] == ":action":
            name = sec[1]
            body = dict(zip(sec[2::2], sec[3::2]))
            params = typed_list(body[":parameters"])
            pre = conj(body[":precondition"])
            add, dele = [], []
            for e in conj(body[":effect"]):
                if e[0] == "not":
                    dele.append(e[1])
                else:
                    add.append(e)
                preds_in_effects.add((e[1] if e[0] == "not" else e)[0])
            if any(p[0] == "not" for p in pre):
                raise ValueError("negative precondition found")
            actions.append(Action(name, params, pre, add, dele))
    return actions, preds_in_effects


def parse_problem(path):
    p = parse_file(path)
    objs, init, goal = [], [], []
    for sec in p[1:]:
        if sec[0] == ":objects":
            objs = typed_list(sec[1:])
        elif sec[0] == ":init":
            init = [tuple(a) for a in sec[1:]]
        elif sec[0] == ":goal":
            goal = [tuple(a) for a in conj(sec[1])]
    return objs, init, goal


# ----------------------------------------------------------------------
# Grounding
# ----------------------------------------------------------------------
def subst(atom, binding):
    return tuple([atom[0]] + [binding.get(a, a) for a in atom[1:]])


class Task:
    def __init__(self, domain_path, problem_path):
        self.actions, effect_preds = parse_domain(domain_path)
        self.objs, self.init, self.goal = parse_problem(problem_path)
        self.static_preds = {a[0] for a in self.init} - effect_preds
        self.init_set = set(self.init)
        self.ground()

    def ground(self):
        by_type = {}
        for o, t in self.objs:
            by_type.setdefault(t, []).append(o)
        ground = []
        for a in self.actions:
            domains = [by_type.get(t, []) for _, t in a.params]
            for combo in itertools.product(*domains):
                b = {v: o for (v, _), o in zip(a.params, combo)}
                pre = [subst(x, b) for x in a.pre]
                # drop actions whose static preconditions are false
                if any(x[0] in self.static_preds and x not in self.init_set for x in pre):
                    continue
                pre = [x for x in pre if x[0] not in self.static_preds]
                ground.append(((a.name,) + combo, pre,
                               [subst(x, b) for x in a.add],
                               [subst(x, b) for x in a.dele]))
        facts = set(x for x in self.init if x[0] not in self.static_preds)
        facts |= set(self.goal)
        for _, pre, add, dele in ground:
            facts |= set(pre) | set(add) | set(dele)
        self.fact_list = sorted(facts)
        self.fid = {f: i for i, f in enumerate(self.fact_list)}
        self.ops = []
        for name, pre, add, dele in ground:
            self.ops.append(dict(
                name=name,
                pre_ids=[self.fid[x] for x in pre],
                add_ids=[self.fid[x] for x in add],
                pre=sum(1 << self.fid[x] for x in pre),
                add=sum(1 << self.fid[x] for x in add),
                dele=sum(1 << self.fid[x] for x in dele)))
        self.s0 = sum(1 << self.fid[x] for x in self.init if x in self.fid)
        self.goal_mask = sum(1 << self.fid[x] for x in self.goal)
        self.goal_ids = [self.fid[x] for x in self.goal]


# ----------------------------------------------------------------------
# Heuristics (delete relaxation)
# ----------------------------------------------------------------------
def relaxed_costs(task, state, mode):
    n = len(task.fact_list)
    dist = [INF] * n
    for i in range(n):
        if state >> i & 1:
            dist[i] = 0
    changed = True
    while changed:
        changed = False
        for op in task.ops:
            ids = op["pre_ids"]
            if not ids:
                c = 0
            else:
                vals = [dist[i] for i in ids]
                if max(vals) >= INF:
                    continue
                c = max(vals) if mode == "max" else sum(vals)
            c += 1
            for f in op["add_ids"]:
                if c < dist[f]:
                    dist[f] = c
                    changed = True
    return dist


def h_value(task, state, mode):
    dist = relaxed_costs(task, state, mode)
    vals = [dist[i] for i in task.goal_ids]
    if max(vals) >= INF:
        return INF
    return max(vals) if mode == "max" else sum(vals)


# ----------------------------------------------------------------------
# Domain-specific admissible heuristic
# ----------------------------------------------------------------------
class RoverHeuristic:
    """Lower bound on the number of remaining actions.

    Actions fall into disjoint classes (deposit, collect, pick-drill, move),
    so a lower bound on each class can simply be added:
      * every rock that is not at Base needs at least one deposit,
      * every such rock still on the ground also needs one collect,
      * if a hard rock is still on the ground and the drill is not held,
        pick-drill is needed at least once,
      * moves: the rover must still visit every location holding a rock
        (and the drill, if it is needed) and then be at Base, so the
        farthest such detour is a lower bound (directed shortest paths).
    """

    def __init__(self, task):
        self.task = task
        fid = task.fid
        locs = [o for o, t in task.objs if t == "location"]
        self.rocks = [o for o, t in task.objs if t == "rock"]
        bays = [o for o, t in task.objs if t == "bay"]
        rover = next(o for o, t in task.objs if t == "rover")
        drill = next(o for o, t in task.objs if t == "drill")
        self.base = next(g[2] for g in task.goal if g[0] == "rock-at")
        self.hard = {a[1] for a in task.init if a[0] == "hard"}
        d = {(a, b): (0 if a == b else INF) for a in locs for b in locs}
        for op in task.ops:
            if op["name"][0] == "move":
                d[(op["name"][2], op["name"][3])] = 1
        for k in locs:
            for i in locs:
                for j in locs:
                    if d[(i, k)] + d[(k, j)] < d[(i, j)]:
                        d[(i, j)] = d[(i, k)] + d[(k, j)]
        self.d = d
        self.rover_ids = {l: fid[("rover-at", rover, l)] for l in locs}
        self.home = {r: fid[("rock-at", r, self.base)] for r in self.rocks}
        self.ground = {r: [(l, fid[("rock-at", r, l)]) for l in locs] for r in self.rocks}
        self.bay_ids = {r: [fid[("in-bay", r, b)] for b in bays] for r in self.rocks}
        self.has_drill = fid[("has-drill", rover, drill)]
        self.drill_ids = [(l, fid[("drill-at", drill, l)]) for l in locs
                          if ("drill-at", drill, l) in fid]

    def __call__(self, s):
        bit = lambda i: s >> i & 1
        rl = next(l for l, i in self.rover_ids.items() if bit(i))
        deposits = collects = pick = 0
        required, hard_ground = set(), False
        for r in self.rocks:
            if bit(self.home[r]):
                continue
            deposits += 1
            if any(bit(i) for i in self.bay_ids[r]):
                continue
            collects += 1
            required.add(next(l for l, i in self.ground[r] if bit(i)))
            hard_ground = hard_ground or r in self.hard
        if hard_ground and not bit(self.has_drill):
            pick = 1
            required.add(next(l for l, i in self.drill_ids if bit(i)))
        d, base = self.d, self.base
        moves = max([d[(rl, p)] + d[(p, base)] for p in required] or [d[(rl, base)]])
        if moves >= INF:
            return INF
        return deposits + collects + pick + moves


# ----------------------------------------------------------------------
# Search
# ----------------------------------------------------------------------
def successors(task, s):
    for op in task.ops:
        if op["pre"] & ~s == 0:
            yield op, (s & ~op["dele"]) | op["add"]


def extract(parent, s):
    plan = []
    while parent[s] is not None:
        s, name = parent[s]
        plan.append(name)
    return plan[::-1]


def search(task, config, time_limit=600, max_states=4_000_000):
    t0 = time.time()
    parent = {task.s0: None}
    expanded = generated = 0

    if config == "bfs":
        q = deque([task.s0])
        while q:
            s = q.popleft()
            if s & task.goal_mask == task.goal_mask:
                return extract(parent, s), expanded, generated, time.time() - t0
            expanded += 1
            for op, s2 in successors(task, s):
                generated += 1
                if s2 not in parent:
                    parent[s2] = (s, op["name"])
                    q.append(s2)
            if time.time() - t0 > time_limit or len(parent) > max_states:
                return None, expanded, generated, time.time() - t0
        return None, expanded, generated, time.time() - t0

    astar = config.startswith("astar")
    if config == "gbfs":
        hfun = lambda st: h_value(task, st, "add")
    elif config == "astar":
        hfun = lambda st: h_value(task, st, "max")
    else:                                   # astar_rover
        hfun = RoverHeuristic(task)
    g = {task.s0: 0}
    counter = itertools.count()
    h0 = hfun(task.s0)
    heap = [(h0, h0, next(counter), task.s0)]        # (f, h, tie, state)
    closed = set()
    hcache = {task.s0: h0}
    while heap:
        f, h, _, s = heapq.heappop(heap)
        if astar:
            # stale queue entry (a cheaper path to s was found later)
            if f != g[s] + hcache[s]:
                continue
        elif s in closed:
            continue
        if s & task.goal_mask == task.goal_mask:
            return extract(parent, s), expanded, generated, time.time() - t0
        closed.add(s)
        expanded += 1
        for op, s2 in successors(task, s):
            generated += 1
            ng = g[s] + 1
            if astar:
                if s2 in g and g[s2] <= ng:
                    continue
            else:
                if s2 in parent:
                    continue
            g[s2] = ng
            parent[s2] = (s, op["name"])
            if s2 not in hcache:
                hcache[s2] = hfun(s2)
            h2 = hcache[s2]
            if h2 >= INF:
                continue
            key = ng + h2 if astar else h2
            heapq.heappush(heap, (key, h2, next(counter), s2))
        if time.time() - t0 > time_limit or len(parent) > max_states:
            return None, expanded, generated, time.time() - t0
    return None, expanded, generated, time.time() - t0


# ----------------------------------------------------------------------
# Validator: simulates the plan on the lifted domain, independent of grounding
# ----------------------------------------------------------------------
def fmt(a):
    return "(" + " ".join(a) + ")"


def validate(domain_path, problem_path, plan, log):
    actions, _ = parse_domain(domain_path)
    by_name = {a.name: a for a in actions}
    _, init, goal = parse_problem(problem_path)
    state = set(init)
    log("  initial state has %d facts" % len(state))
    for i, step in enumerate(plan, 1):
        a = by_name[step[0]]
        b = {v: o for (v, _), o in zip(a.params, step[1:])}
        pre = [subst(x, b) for x in a.pre]
        missing = [x for x in pre if x not in state]
        if missing:
            log(f"  step {i}: {fmt(step)} NOT applicable, missing {[fmt(m) for m in missing]}")
            return False
        dele = [subst(x, b) for x in a.dele]
        add = [subst(x, b) for x in a.add]
        state -= set(dele)
        state |= set(add)
        log(f"  step {i:2d}: {fmt(step):52s} -{len(dele)} +{len(add)}")
    log("\n  Final state (dynamic facts):")
    for f in sorted(state):
        if f[0] in ("rover-at", "rock-at", "in-bay", "bay-empty", "has-drill", "drill-at"):
            log("    " + fmt(f))
    missing = [x for x in goal if x not in state]
    ok = not missing
    log("  Goal satisfied: %s" % ok)
    if missing:
        log("  unsatisfied: %s" % [fmt(m) for m in missing])
    return ok


# ----------------------------------------------------------------------
CONFIGS = [("gbfs", "Greedy best-first search, h_add (satisficing)"),
           ("astar_rover", "A* with a problem-specific admissible heuristic (optimal)"),
           ("astar", "A* with h_max (optimal, admissible)"),
           ("bfs", "Breadth-first search (optimal)")]
# the two weak/blind optimal searches are given a time budget (seconds) in the
# bigger extended scenario; the pure-python implementation cannot finish them
LIMITS = {("extended", "astar"): 90, ("extended", "bfs"): 90}
SCENARIOS = [("original", "Problem.pddl"), ("extended", "Problem_extended.pddl")]


def main():
    dom = os.path.join(HERE, "Domain.pddl")
    summary = []
    for sname, pfile in SCENARIOS:
        task = Task(dom, os.path.join(HERE, pfile))
        print(f"\n##### Scenario: {sname} ({pfile}) - {len(task.ops)} ground actions, "
              f"{len(task.fact_list)} dynamic facts")
        for cfg, desc in CONFIGS:
            lines = []

            def log(s):
                lines.append(s)
                print(s)

            log(f"=== {sname} | {desc}")
            plan, exp, gen, secs = search(task, cfg, LIMITS.get((sname, cfg), 600))
            if plan is None:
                log(f"  NO PLAN within the budget: stopped after {exp} expansions, {secs:.1f}s")
                summary.append((sname, cfg, None, exp, gen, secs))
                with open(os.path.join(OUT, f"plan_{sname}_{cfg}.txt"), "w") as f:
                    f.write("\n".join(lines) + "\n")
                continue
            log(f"  plan length          : {len(plan)}")
            log(f"  actions in plan      : {len(plan)}")
            log(f"  states expanded      : {exp}")
            log(f"  states generated     : {gen}")
            log(f"  planning time (s)    : {secs:.3f}")
            log("  plan:")
            for i, st in enumerate(plan, 1):
                log(f"    {i:2d}. {fmt(st)}")
            log("  validation:")
            ok = validate(dom, os.path.join(HERE, pfile), plan, log)
            if cfg == "astar_rover":
                # sanity check: on an optimal plan the true cost-to-go of step i
                # is len(plan)-i, so an admissible h can never exceed it
                hf, s, good = RoverHeuristic(task), task.s0, True
                byname = {op["name"]: op for op in task.ops}
                for i, st in enumerate(plan):
                    good &= hf(s) <= len(plan) - i
                    op = byname[st]
                    s = (s & ~op["dele"]) | op["add"]
                log(f"  heuristic never exceeds true cost-to-go along this plan: {good}")
            summary.append((sname, cfg, len(plan), exp, gen, secs))
            with open(os.path.join(OUT, f"plan_{sname}_{cfg}.txt"), "w") as f:
                f.write("\n".join(lines) + "\n")
            with open(os.path.join(OUT, f"plan_{sname}_{cfg}.plan"), "w") as f:
                f.write("\n".join(fmt(s) for s in plan) + "\n")
    print("\n##### Summary")
    print(f"{'scenario':10s}{'config':8s}{'length':>8s}{'expanded':>10s}{'generated':>11s}{'time(s)':>9s}")
    for s, c, L, e, g, t in summary:
        print(f"{s:10s}{c:12s}{str(L):>8s}{e:>10d}{g:>11d}{t:>9.3f}")


if __name__ == "__main__":
    main()
