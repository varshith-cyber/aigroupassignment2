"""
Python cross-check of the Prolog resolution step.

SWI-Prolog was not available in our environment, so we re-implemented the same
algorithm (linear resolution from the negated goal, iterative deepening,
same clause order and literal selection order) to confirm that the proof
really ends in the empty clause and to see what the Prolog output should look
like. The real submission is royal_archive_access.pl.
"""


class Var:
    pass


def v():
    return Var()


# literal = (sign, atom), atom = (predicate, arg1, arg2, ...); args are str or Var
def kb():
    X, R = v(), v()
    X2, R2 = v(), v()
    X3, R3 = v(), v()
    R4 = v()
    return [
        ("f1", [("-", ("archivist", X)), ("-", ("verifies", X, R)), ("+", ("trusted", X))]),
        ("f2", [("-", ("trusted", X2)), ("-", ("access", X2, R2)), ("-", ("sealed", R2)),
                ("+", ("permitted", X2, R2))]),
        ("f3", [("-", ("inspects", X3, R3)), ("-", ("finds_mark", X3, R3)), ("+", ("verifies", X3, R3))]),
        ("f4", [("-", ("stored_in_archive", R4)), ("+", ("sealed", R4))]),
        ("f5", [("+", ("stored_in_archive", "scroll_7"))]),
        ("f6", [("+", ("access", "mira", "scroll_7"))]),
        ("f7a", [("+", ("inspects", "mira", "scroll_7"))]),
        ("f7b", [("+", ("finds_mark", "mira", "scroll_7"))]),
        ("f8", [("+", ("archivist", "mira"))]),
        ("ng", [("-", ("trusted", "mira"))]),
    ]


def walk(t, s):
    while isinstance(t, Var) and t in s:
        t = s[t]
    return t


def unify(a, b, s):
    a, b = walk(a, s), walk(b, s)
    if a is b or (isinstance(a, str) and isinstance(b, str) and a == b):
        return s
    if isinstance(a, Var):
        s = dict(s); s[a] = b; return s
    if isinstance(b, Var):
        s = dict(s); s[b] = a; return s
    if isinstance(a, tuple) and isinstance(b, tuple) and len(a) == len(b) and a[0] == b[0]:
        for x, y in zip(a[1:], b[1:]):
            s = unify(x, y, s)
            if s is None:
                return None
        return s
    return None


def apply(t, s):
    t = walk(t, s)
    if isinstance(t, tuple):
        return tuple([t[0]] + [apply(x, s) for x in t[1:]])
    return t


def apply_lit(l, s):
    return (l[0], apply(l[1], s))


def rename(clause):
    m = {}

    def go(t):
        if isinstance(t, Var):
            m.setdefault(t, Var())
            return m[t]
        if isinstance(t, tuple):
            return tuple([t[0]] + [go(x) for x in t[1:]])
        return t
    return [(sg, go(a)) for sg, a in clause]


def same(a, b):
    if isinstance(a, tuple) and isinstance(b, tuple):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return a is b or (isinstance(a, str) and a == b)


def remove_dups(lits):
    out = []
    for i, l in enumerate(lits):
        if not any(l[0] == m[0] and same(l[1], m[1]) for m in lits[i + 1:]):
            out.append(l)
    return out


def dfs(top, n, acc, base):
    if not top:
        return acc
    if n == 0:
        return None
    for cid, side0 in base:
        side = rename(side0)
        for i, lt in enumerate(top):
            for j, ls in enumerate(side):
                if lt[0] == ls[0]:
                    continue
                s = unify(lt[1], ls[1], {})
                if s is None:
                    continue
                rest = ([apply_lit(l, s) for k, l in enumerate(top) if k != i] +
                        [apply_lit(l, s) for k, l in enumerate(side) if k != j])
                res = remove_dups(rest)
                r = dfs(res, n - 1, acc + [(top, cid, apply_lit(lt, s), res)], base)
                if r is not None:
                    return r
    return None


def names(clause):
    order = []

    def go(t):
        if isinstance(t, Var):
            if t not in order:
                order.append(t)
        elif isinstance(t, tuple):
            for x in t[1:]:
                go(x)
    for _, a in clause:
        go(a)
    return {x: f"V{i + 1}" for i, x in enumerate(order)}


def term(t, nm):
    if isinstance(t, Var):
        return nm[t]
    if isinstance(t, tuple):
        return t[0] + "(" + ",".join(term(x, nm) for x in t[1:]) + ")"
    return t


def lit(l, nm):
    return ("~" if l[0] == "-" else "") + term(l[1], nm)


def clause_str(c):
    if not c:
        return "[]  (empty clause)"
    nm = names(c)
    return " v ".join(lit(l, nm) for l in c)


def main():
    base = kb()
    print("Step 7: CNF clauses")
    for cid, c in base:
        print(f"{cid} : {clause_str(c)}")
    start = rename(dict(base)["ng"])
    print("\nStep 8: Resolution refutation")
    print("Start from the negated goal:", clause_str(start), "\n")
    steps = None
    for limit in range(1, 13):
        steps = dfs(start, limit, [], base)
        if steps is not None:
            break
    if steps is None:
        print("No refutation found.")
        return
    d = dict(base)
    for n, (top, cid, l, res) in enumerate(steps, 1):
        print(f"Step {n}")
        print("   current clause :", clause_str(top))
        print(f"   resolve with {cid} :", clause_str(d[cid]))
        print("   on literal     :", lit(l, names([l])))
        print("   resolvent      :", clause_str(res), "\n")
    used = [s[1] for s in steps]
    unused = [cid for cid, _ in base if cid != "ng" and cid not in used]
    print("Empty clause [] derived: the knowledge base plus ~trusted(mira) is contradictory.")
    print("Therefore trusted(mira) follows from the facts and rules.")
    print("Clauses used in the proof :", used)
    print("Clauses not needed        :", unused)


if __name__ == "__main__":
    main()
