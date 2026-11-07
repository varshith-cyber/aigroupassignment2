;; Mars rover sample collection - domain
;; Only :strips and :typing are used (no negative preconditions, no numbers).
;; Because negative preconditions are not allowed, soft and hard rocks are
;; marked with two separate predicates and each has its own collect action.

(define (domain mars-rover)
  (:requirements :strips :typing)

  (:types
    rover location rock bay drill)

  (:predicates
    (rover-at ?rv - rover ?l - location)        ; where the rover currently is
    (connected ?from - location ?to - location) ; directed edge (static)
    (rock-at ?r - rock ?l - location)           ; rock lying on the ground
    (in-bay ?r - rock ?b - bay)                 ; rock stored in a bay
    (bay-empty ?b - bay)                        ; bay is free
    (soft ?r - rock)                            ; static: collectable directly
    (hard ?r - rock)                            ; static: needs the drill
    (drill-at ?d - drill ?l - location)         ; drill lying on the ground
    (has-drill ?rv - rover ?d - drill))         ; rover carries the drill

  ;; Move along a directed edge. Two-way routes are two connected facts,
  ;; the one-way slope has only one.
  (:action move
    :parameters (?rv - rover ?from - location ?to - location)
    :precondition (and (rover-at ?rv ?from)
                       (connected ?from ?to))
    :effect (and (rover-at ?rv ?to)
                 (not (rover-at ?rv ?from))))

  ;; The drill is kept for the rest of the mission, so there is no drop action.
  (:action pick-drill
    :parameters (?rv - rover ?d - drill ?l - location)
    :precondition (and (rover-at ?rv ?l)
                       (drill-at ?d ?l))
    :effect (and (has-drill ?rv ?d)
                 (not (drill-at ?d ?l))))

  (:action collect-soft
    :parameters (?rv - rover ?r - rock ?l - location ?b - bay)
    :precondition (and (rover-at ?rv ?l)
                       (rock-at ?r ?l)
                       (soft ?r)
                       (bay-empty ?b))
    :effect (and (in-bay ?r ?b)
                 (not (rock-at ?r ?l))
                 (not (bay-empty ?b))))

  (:action collect-hard
    :parameters (?rv - rover ?r - rock ?l - location ?b - bay ?d - drill)
    :precondition (and (rover-at ?rv ?l)
                       (rock-at ?r ?l)
                       (hard ?r)
                       (has-drill ?rv ?d)
                       (bay-empty ?b))
    :effect (and (in-bay ?r ?b)
                 (not (rock-at ?r ?l))
                 (not (bay-empty ?b))))

  ;; Deposit at the rover's current location only.
  (:action deposit
    :parameters (?rv - rover ?r - rock ?l - location ?b - bay)
    :precondition (and (rover-at ?rv ?l)
                       (in-bay ?r ?b))
    :effect (and (rock-at ?r ?l)
                 (bay-empty ?b)
                 (not (in-bay ?r ?b))))
)
