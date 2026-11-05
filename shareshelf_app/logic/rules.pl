:- dynamic item/7, wanted/4, lent/2.

% ---------- Conditions ----------

condition('New').
condition('Gently Used').
condition('Functional').

% meets(Preference, Condition): an item's condition is what the seeker asked for.
meets('Flexible', Condition) :- condition(Condition).
meets(Condition, Condition) :- condition(Condition).

% ---------- Availability and matching ----------

% An item can be handed out while it has stock and isn't paused.
available(Item) :-
    item(Item, _, _, _, _, Qty, false),
    Qty > 0.

% matches(Request, Item): another student is giving away an available item
% in the same category, in a condition the seeker accepts.
matches(Request, Item) :-
    wanted(Request, Seeker, Category, Preference),
    item(Item, Owner, give, Category, Condition, _, _),
    Owner \== Seeker,
    available(Item),
    meets(Preference, Condition).

% ---------- Request life cycle ----------

% step(Kind, Role, From, To, StockChange): who may move a request from one
% status to another, and what happens to the item's stock. Kind is how the
% item is shared: give (it's gone for good) or lend (it comes back).
% An underscore means the step works for both kinds.
step(_,    seeker, open,      requested,  0).   % ask for a suggested item
step(_,    seeker, open,      cancelled,  0).
step(_,    seeker, requested, cancelled,  0).
step(_,    sharer, requested, matched,   -1).   % accepting sets one unit aside
step(_,    sharer, requested, declined,   0).
step(_,    seeker, matched,   cancelled,  1).   % the set-aside unit goes back
step(give, Role,   matched,   fulfilled,  0) :- member(Role, [seeker, sharer]).
step(lend, Role,   matched,   lent,       0) :- member(Role, [seeker, sharer]).
step(lend, sharer, lent,      returned,   1).   % it came back, so the unit does too

max_stock(20).

% A step that takes a unit needs one in stock on an item that isn't paused.
stock_ok(Change, _, _) :- Change >= 0.
stock_ok(Change, Qty, false) :- Change < 0, Qty + Change >= 0.

% allowed(Kind, Role, From, To, Qty, Paused, NewQty): the step is legal, and
% the item's stock becomes NewQty (never more than the maximum).
allowed(Kind, Role, From, To, Qty, Paused, NewQty) :-
    step(Kind, Role, From, To, Change),
    stock_ok(Change, Qty, Paused),
    max_stock(Max),
    NewQty is min(Qty + Change, Max).

% ---------- Borrowing ----------

% loan_problem(LimitDays, From, ReturnBy, Today, Problem): what's wrong with
% the dates a borrower proposed. No answer means the dates are fine.
% LimitDays is 0 when the item has no lending limit.
loan_problem(_, From, _, Today, starts_in_past) :-
    From < Today.
loan_problem(_, From, ReturnBy, _, ends_before_start) :-
    ReturnBy =< From.
loan_problem(Limit, From, ReturnBy, _, too_long) :-
    Limit > 0,
    ReturnBy > From,
    ReturnBy - From > Limit.

% overdue(Request, Today): a lent item should already have come back.
overdue(Request, Today) :-
    lent(Request, ReturnBy),
    ReturnBy < Today.

% ---------- Queries Django runs ----------
% Each prints its answers one per line so Python can read them back.

print_matches :-
    forall(matches(Request, Item), format("~w ~w~n", [Request, Item])).

print_allowed(Kind, Role, From, To, Qty, Paused) :-
    (   allowed(Kind, Role, From, To, Qty, Paused, NewQty)
    ->  writeln(NewQty)
    ;   writeln(no)
    ).

print_loan_problems(Limit, From, ReturnBy, Today) :-
    forall(loan_problem(Limit, From, ReturnBy, Today, Problem), writeln(Problem)).

print_overdue(Today) :-
    forall(overdue(Request, Today), writeln(Request)).
