;; Mars rover - original scenario

(define (problem mars-rover-1)
  (:domain mars-rover)

  (:objects
    curiosity - rover
    base sitea siteb sitec sited sitee sitef - location
    rock1 rock2 rock3 rock4 rock5 - rock
    bay1 bay2 - bay
    drill1 - drill)

  (:init
    ;; two-way routes
    (connected base sitea)  (connected sitea base)
    (connected base siteb)  (connected siteb base)
    (connected sitea sitec) (connected sitec sitea)
    (connected siteb sited) (connected sited siteb)
    (connected sitec sitee) (connected sitee sitec)
    (connected sited sitee) (connected sitee sited)
    (connected sitee sitef) (connected sitef sitee)
    ;; one-way steep slope: SiteC -> SiteD only
    (connected sitec sited)

    (rover-at curiosity base)
    (bay-empty bay1)
    (bay-empty bay2)
    (drill-at drill1 sitee)

    (rock-at rock1 sitea) (soft rock1)
    (rock-at rock2 siteb) (soft rock2)
    (rock-at rock3 sitec) (hard rock3)
    (rock-at rock4 sited) (soft rock4)
    (rock-at rock5 sitef) (hard rock5))

  (:goal (and
    (rock-at rock1 base)
    (rock-at rock2 base)
    (rock-at rock3 base)
    (rock-at rock4 base)
    (rock-at rock5 base)
    (bay-empty bay1)
    (bay-empty bay2)
    (rover-at curiosity base)))
)
