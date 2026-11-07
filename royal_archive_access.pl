% =====================================================================
% royal_archive_access.pl
% Problem 3 - Royal Archive access verification by resolution refutation
%
% Group members: <Name 1> (<Roll No>), <Name 2> (<Roll No>), ...
%
% Run (SWI-Prolog):   swipl royal_archive_access.pl
% The program prints every transformation step and then the resolution
% proof, ending with the empty clause [].
% =====================================================================

:- initialization(main, main).

% ---------------------------------------------------------------------
% Step 1: Predicate logic representation
% ---------------------------------------------------------------------
% Predicates (arity):
%   archivist/1, verifies/2, trusted/1, access/2, sealed/1,
%   permitted/2, inspects/2, finds_mark/2, stored_in_archive/1
% Constants : mira, scroll_7
% Variables : x (a person), r (a record)
%
% Formulas are stored as terms built from
%   forall(V,F)  implies(A,B)  and(A,B)  or(A,B)  not(A)
% fol(Id, English text, Formula)

fol(f1, 'Every archivist who verifies a record is trusted',
    forall(x, forall(r, implies(and(archivist(x), verifies(x, r)), trusted(x))))).
fol(f2, 'Every trusted person with access to a sealed record is permitted to inspect it',
    forall(x, forall(r, implies(and(trusted(x), and(access(x, r), sealed(r))), permitted(x, r))))).
fol(f3, 'Anyone who inspects a record and finds a hidden mark in it verifies it',
    forall(x, forall(r, implies(and(inspects(x, r), finds_mark(x, r)), verifies(x, r))))).
fol(f4, 'Every record stored in the royal archive is sealed',
    forall(r, implies(stored_in_archive(r), sealed(r)))).
fol(f5, 'scroll_7 is stored in the royal archive',
    stored_in_archive(scroll_7)).
fol(f6, 'Mira has access to scroll_7',
    access(mira, scroll_7)).
fol(f7, 'Mira inspects scroll_7 and finds a hidden mark in it',
    and(inspects(mira, scroll_7), finds_mark(mira, scroll_7))).
fol(f8, 'Mira is an archivist',
    archivist(mira)).

goal(trusted(mira)).

% ---------------------------------------------------------------------
% Step 2: Negation of the goal
% ---------------------------------------------------------------------
negated_goal(not(trusted(mira))).

% ---------------------------------------------------------------------
% Step 3: Implication removal      (A => B  becomes  ~A v B)
% ---------------------------------------------------------------------
step3(f1, forall(x, forall(r, or(not(and(archivist(x), verifies(x, r))), trusted(x))))).
step3(f2, forall(x, forall(r, or(not(and(trusted(x), and(access(x, r), sealed(r)))), permitted(x, r))))).
step3(f3, forall(x, forall(r, or(not(and(inspects(x, r), finds_mark(x, r))), verifies(x, r))))).
step3(f4, forall(r, or(not(stored_in_archive(r)), sealed(r)))).
step3(f5, stored_in_archive(scroll_7)).
step3(f6, access(mira, scroll_7)).
step3(f7, and(inspects(mira, scroll_7), finds_mark(mira, scroll_7))).
step3(f8, archivist(mira)).
step3(ng, not(trusted(mira))).

% ---------------------------------------------------------------------
% Step 4: Negation movement        (De Morgan: ~(A & B) = ~A v ~B)
% ---------------------------------------------------------------------
step4(f1, forall(x, forall(r, or(or(not(archivist(x)), not(verifies(x, r))), trusted(x))))).
step4(f2, forall(x, forall(r, or(or(not(trusted(x)), or(not(access(x, r)), not(sealed(r)))), permitted(x, r))))).
step4(f3, forall(x, forall(r, or(or(not(inspects(x, r)), not(finds_mark(x, r))), verifies(x, r))))).
step4(f4, forall(r, or(not(stored_in_archive(r)), sealed(r)))).
step4(f5, stored_in_archive(scroll_7)).
step4(f6, access(mira, scroll_7)).
step4(f7, and(inspects(mira, scroll_7), finds_mark(mira, scroll_7))).
step4(f8, archivist(mira)).
step4(ng, not(trusted(mira))).

% ---------------------------------------------------------------------
% Step 5: Standardization of variables (a different name in every formula)
% ---------------------------------------------------------------------
step5(f1, forall(x1, forall(r1, or(or(not(archivist(x1)), not(verifies(x1, r1))), trusted(x1))))).
step5(f2, forall(x2, forall(r2, or(or(not(trusted(x2)), or(not(access(x2, r2)), not(sealed(r2)))), permitted(x2, r2))))).
step5(f3, forall(x3, forall(r3, or(or(not(inspects(x3, r3)), not(finds_mark(x3, r3))), verifies(x3, r3))))).
step5(f4, forall(r4, or(not(stored_in_archive(r4)), sealed(r4)))).
step5(f5, stored_in_archive(scroll_7)).
step5(f6, access(mira, scroll_7)).
step5(f7, and(inspects(mira, scroll_7), finds_mark(mira, scroll_7))).
step5(f8, archivist(mira)).
step5(ng, not(trusted(mira))).

% ---------------------------------------------------------------------
% Step 6: Skolemization
% There is no existential quantifier anywhere in the knowledge base, so
% no Skolem constant or function is needed.  All remaining quantifiers
% are universal, so they are dropped (variables are implicitly universal).
% ---------------------------------------------------------------------
step6(f1, or(or(not(archivist(x1)), not(verifies(x1, r1))), trusted(x1))).
step6(f2, or(or(not(trusted(x2)), or(not(access(x2, r2)), not(sealed(r2)))), permitted(x2, r2))).
step6(f3, or(or(not(inspects(x3, r3)), not(finds_mark(x3, r3))), verifies(x3, r3))).
step6(f4, or(not(stored_in_archive(r4)), sealed(r4))).
step6(f5, stored_in_archive(scroll_7)).
step6(f6, access(mira, scroll_7)).
step6(f7, and(inspects(mira, scroll_7), finds_mark(mira, scroll_7))).
step6(f8, archivist(mira)).
step6(ng, not(trusted(mira))).

% ---------------------------------------------------------------------
% Step 7: CNF clauses
% A clause is a list of literals pos(Atom) / neg(Atom).  Here the
% variables are real Prolog variables, which the resolution step needs.
% f7 is a conjunction, so it splits into two unit clauses.
% ---------------------------------------------------------------------
clause_kb(f1,  [neg(archivist(X)), neg(verifies(X, R)), pos(trusted(X))]).
clause_kb(f2,  [neg(trusted(X)), neg(access(X, R)), neg(sealed(R)), pos(permitted(X, R))]).
clause_kb(f3,  [neg(inspects(X, R)), neg(finds_mark(X, R)), pos(verifies(X, R))]).
clause_kb(f4,  [neg(stored_in_archive(R)), pos(sealed(R))]).
clause_kb(f5,  [pos(stored_in_archive(scroll_7))]).
clause_kb(f6,  [pos(access(mira, scroll_7))]).
clause_kb(f7a, [pos(inspects(mira, scroll_7))]).
clause_kb(f7b, [pos(finds_mark(mira, scroll_7))]).
clause_kb(f8,  [pos(archivist(mira))]).
clause_kb(ng,  [neg(trusted(mira))]).

% ---------------------------------------------------------------------
% Pretty printing helpers
% ---------------------------------------------------------------------
show(forall(V, F)) :- !, format('forall ~w. ', [V]), show(F).
show(implies(A, B)) :- !, write('('), show(A), write(' => '), show(B), write(')').
show(and(A, B)) :- !, write('('), show(A), write(' & '), show(B), write(')').
show(or(A, B)) :- !, write('('), show(A), write(' v '), show(B), write(')').
show(not(A)) :- !, write('~'), show(A).
show(A) :- write(A).

bind_vars([], _).
bind_vars([V|T], N) :-
    atom_concat('V', N, V),
    N1 is N + 1,
    bind_vars(T, N1).

print_lit(pos(A)) :- write(A).
print_lit(neg(A)) :- write('~'), write(A).

print_lits([L]) :- !, print_lit(L).
print_lits([L|T]) :- print_lit(L), write(' v '), print_lits(T).

print_clause([]) :- !, write('[]  (empty clause)').
print_clause(C) :-
    copy_term(C, C2),
    term_variables(C2, Vs),
    bind_vars(Vs, 1),
    print_lits(C2).

heading(Text) :-
    nl,
    write('============================================================'), nl,
    write(Text), nl,
    write('============================================================'), nl.

% ---------------------------------------------------------------------
% Stage printers
% ---------------------------------------------------------------------
stage1 :-
    heading('Step 1: Predicate logic representation'),
    write('Predicates: archivist/1 verifies/2 trusted/1 access/2 sealed/1'), nl,
    write('            permitted/2 inspects/2 finds_mark/2 stored_in_archive/1'), nl,
    write('Constants : mira, scroll_7        Variables: x (person), r (record)'), nl, nl,
    forall(fol(Id, Text, F),
           ( format('~w  ~w~n      ', [Id, Text]), show(F), nl )),
    goal(G),
    write('goal'), write('  Prove: '), show(G), nl.

stage2 :-
    heading('Step 2: Negation of the goal'),
    negated_goal(NG),
    write('ng  '), show(NG), nl.

print_stage(Pred) :-
    forall(call(Pred, Id, F),
           ( format('~w  ', [Id]), show(F), nl )).

stage3 :- heading('Step 3: Implication removal'), print_stage(step3).
stage4 :- heading('Step 4: Negation movement'),   print_stage(step4).
stage5 :- heading('Step 5: Standardization of variables'), print_stage(step5).
stage6 :-
    heading('Step 6: Skolemization'),
    write('No existential quantifiers occur, so no Skolem terms are introduced.'), nl,
    write('Universal quantifiers are dropped:'), nl,
    print_stage(step6).

stage7 :-
    heading('Step 7: CNF clauses'),
    forall(clause_kb(Id, C),
           ( format('~w : ', [Id]), print_clause(C), nl )).

% ---------------------------------------------------------------------
% Step 8: Resolution refutation
% Linear resolution that starts from the negated goal and resolves the
% current clause with a (renamed) clause of the knowledge base at each
% step, with iterative deepening on the number of steps.  Every
% resolvent is recorded so the whole derivation can be printed.
% ---------------------------------------------------------------------
complementary(pos(A), neg(B)) :- A = B.
complementary(neg(A), pos(B)) :- A = B.

member_eq(X, [Y|T]) :- ( X == Y -> true ; member_eq(X, T) ).

remove_dups([], []).
remove_dups([L|T], R) :-
    (   member_eq(L, T)
    ->  remove_dups(T, R)
    ;   R = [L|R1],
        remove_dups(T, R1)
    ).

% resolve_pair(+Top, +Side, -Resolvent, -ResolvedLiteral)
resolve_pair(Top, Side, Resolvent, LTop) :-
    select(LTop, Top, RestTop),
    select(LSide, Side, RestSide),
    complementary(LTop, LSide),
    append(RestTop, RestSide, R0),
    remove_dups(R0, Resolvent).

prove(Top, KB, Steps) :-
    between(1, 12, Limit),
    prove_(Top, KB, Limit, [], Rev),
    !,
    reverse(Rev, Steps).

prove_([], _, _, Acc, Acc) :- !.
prove_(Top, KB, N, Acc, Steps) :-
    N > 0,
    member(clause(Id, Side0), KB),
    copy_term(Top, TopSnapshot),
    copy_term(Side0, Side),                 % rename the side clause apart
    resolve_pair(Top, Side, Resolvent, LTop),
    copy_term(LTop, LitSnapshot),
    copy_term(Resolvent, ResSnapshot),
    N1 is N - 1,
    prove_(Resolvent, KB, N1,
           [step(TopSnapshot, Id, LitSnapshot, ResSnapshot) | Acc], Steps).

print_steps([], _).
print_steps([step(Top, Id, Lit, Res) | T], N) :-
    format('Step ~w~n', [N]),
    write('   current clause : '), print_clause(Top), nl,
    clause_kb(Id, C),
    format('   resolve with ~w : ', [Id]), print_clause(C), nl,
    write('   on literal     : '), print_lit(Lit), nl,
    write('   resolvent      : '), print_clause(Res), nl, nl,
    N1 is N + 1,
    print_steps(T, N1).

used_ids([], []).
used_ids([step(_, Id, _, _) | T], [Id | R]) :- used_ids(T, R).

stage8 :-
    heading('Step 8: Resolution refutation'),
    findall(clause(Id, C), clause_kb(Id, C), KB),
    member(clause(ng, Start0), KB),
    copy_term(Start0, Start),
    write('Start from the negated goal: '), print_clause(Start), nl, nl,
    (   prove(Start, KB, Steps)
    ->  print_steps(Steps, 1),
        used_ids(Steps, Used),
        findall(I, ( member(clause(I, _), KB), I \== ng, \+ memberchk(I, Used) ), Unused),
        format('Empty clause [] derived: the knowledge base plus ~~trusted(mira) is contradictory.~n', []),
        write('Therefore trusted(mira) follows from the facts and rules.'), nl,
        format('Clauses used in the proof : ~w~n', [Used]),
        format('Clauses not needed        : ~w~n', [Unused])
    ;   write('No refutation found.'), nl
    ).

% ---------------------------------------------------------------------
main :-
    stage1, stage2, stage3, stage4, stage5, stage6, stage7, stage8.
