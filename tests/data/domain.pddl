(define (domain textworld)
    (:requirements
     :typing
     :derived-predicates
     :conditional-effects
     :existential-preconditions
     :negative-preconditions
     :disjunctive-preconditions :universal-preconditions)
    (:types
        ; object
        t
        ; r - object
        ; d - object
        ; c - t
        ; s - t
        ; o - t
        ; k - o
        ; f - o
    )
    ; (:constants
    ;     P
    ;     I
    ; )
    (:predicates
        (is_door ?t - t)
        (is_room ?t - t)
        (is_container ?t - t)
        (is_supporter ?t - t)
        (is_player ?t - t)
        ; (is_inventory ?t - t)

        (open ?t - t)
        (closed ?t - t)
        (locked ?t - t)
        (unlocked ?t - t)
        (eaten ?t - t)
        (examined ?t - t)

        (openable ?t - t)
        (closable ?t - t)
        (lockable ?t - t)
        (unlockable ?t - t)
        (portable ?t - t)
        (moveable ?t - t)
        (edible ?t - t)

        (visible ?P ?t - t)
        (reachable ?P ?t - t)

        (at ?t ?r - t)
        (in ?t ?c - t)
        (on ?t ?s - t)
        (free ?r1 ?r2 - t)
        (link ?r1 ?d ?r2 - t)
        (match ?k ?c - t)
        (north_of ?r1 ?r2 - t)
        (north_of-d ?r1 ?d ?r2 - t)
        (west_of ?r1 ?r2 - t)
        (east_of ?r1 ?r2 - t)
        (west_of-d ?r1 ?d ?r2 - t)
    )

    ; ----------------------------
    ; Derived predicates / Axioms
    ; ----------------------------

    (:derived (free ?r1 ?r2)
        (or
            (not
                (exists (?d)
                    (and
                        (is_door ?d)
                        (link ?r1 ?d ?r2)
                    )
                )
            )
            (exists (?d)
                (and
                    (is_door ?d)
                    (link ?r1 ?d ?r2)
                    (open ?d)
                )
            )
        )
    )

    (:derived (visible ?P ?t)
        (and
            (is_player ?P)
            (exists (?r)
                (and
                    (is_room ?r)
                    (at ?P ?r)
                    (at ?t ?r)
                )
            )
        )
    )

    (:derived (visible ?P ?d)
        (and
            (is_player ?P)
            (is_door ?d)
            (exists (?r1 ?r2)
                (and
                    (is_room ?r1)
                    (is_room ?r2)
                    (at ?P ?r1)
                    (or
                        (link ?r1 ?d ?r2)
                        (link ?r2 ?d ?r1)
                    )
                )
            )
        )
    )

    (:derived (visible ?P ?t)
        (and
            (is_player ?P)
            (in ?t ?P)
        )
    )

    (:derived (visible ?P ?t)
        (and
            (is_player ?P)
            (exists (?r ?s)
                (and
                    (is_room ?r)
                    (is_supporter ?s)
                    (at ?P ?r)
                    (at ?s ?r)
                    (on ?t ?s))
            )
        )
    )

    (:derived (visible ?P ?t)
        (and
            (is_player ?P)
            (exists (?r ?c)
                (and
                    (is_room ?r)
                    (is_container ?c)
                    (at ?P ?r)
                    (at ?c ?r)
                    (openable ?c)
                    (open ?c)
                    (in ?t ?c))
            )
        )
    )

    (:derived (reachable ?P ?t)
        (and
            (is_player ?P)
            (visible ?P ?t)  ; TODO: reachable shouldn't be like visible
        )
    )

    ; -------
    ; Actions
    ; -------

    (:action look
        :parameters (?P ?r)
        :precondition
            (and
                (is_player ?P)
                (is_room ?r)
                (at ?P ?r))
        :effect
            (and
                (examined ?r)
            )
    )

    (:action inventory
        :parameters (?P)
        :precondition
            (and
                (is_player ?P)
            )
        :effect
            (and
                (examined ?P)
            )
    )

    (:action examine
        :parameters (?P ?t)
        :precondition
            (and
                (is_player ?P)  ; Is it needed since reachable check for it?
                (visible ?P ?t)
            )
        :effect
            (and
                (examined ?t)
            )
    )

    (:action close
        :parameters (?P ?closable)
        :precondition
            (and
                (is_player ?P)  ; Is it needed since reachable check for it?
                (closable ?closable)
                (open ?closable)
                (reachable ?P ?closable)
            )
        :effect
            (and
                (closed ?closable)
                (not (open ?closable)))
    )

    (:action open
        :parameters (?P ?openable)
        :precondition
            (and
                (is_player ?P)  ; Is it needed since reachable check for it?
                (openable ?openable)
                (closed ?openable)
                (reachable ?P ?openable)
            )
        :effect
            (and
                (open ?openable)
                (not (closed ?openable)))
    )

    (:action insert
        :parameters (?P ?c ?o)
        :precondition
            (and
                (is_player ?P)
                (is_container ?c)
                (portable ?o)
                (reachable ?P ?c)
                (in ?o ?P)
                (open ?c)
            )
        :effect
            (and
                (in ?o ?c)
                (not (in ?o ?P)))
    )

    (:action put
        :parameters (?P ?s ?o)
        :precondition
            (and
                (is_player ?P)
                (is_supporter ?s)
                (portable ?o)
                (reachable ?P ?s)
                (in ?o ?P)
            )
        :effect
            (and
                (on ?o ?s)
                (not (in ?o ?P)))
    )

    (:action drop
        :parameters (?P ?r ?o)
        :precondition
            (and
                (is_player ?P)
                (is_room ?r)
                (portable ?o)
                (at ?P ?r)
                (in ?o ?P)
            )
        :effect
            (and
                (at ?o ?r)
                (not (in ?o ?P)))
    )

    (:action take
        :parameters (?P ?o)
        :precondition
            (and
                (is_player ?P)
                (portable ?o)
                (reachable ?P ?o)
                (not (in ?o ?P))
            )
        :effect
            (and
                (in ?o ?P)
                (forall (?r)
                    (when
                        (is_room ?r)
                        (not (at ?o ?r))
                    )
                )
                (forall (?c)
                    (when
                        (is_container ?c)
                        (not (in ?o ?c))
                    )
                )
                (forall (?s)
                    (when
                        (is_supporter ?s)
                        (not (on ?o ?s))
                    )
                )
            )
    )

    (:action eat
        :parameters (?P ?f)
        :precondition
            (and
                (is_player ?P)
                (in ?f ?P)
                (edible ?f))
        :effect
            (and
                (eaten ?f)
                (not (in ?f ?P)))
    )

    (:action go-east
        :parameters (?P ?r ?r2)
        :precondition
            (and
                (is_player ?P)
                (is_room ?r)
                (is_room ?r2)
                (at ?P ?r)
                (west_of ?r ?r2)
                (free ?r ?r2)
            )
        :effect
            (and
                (at ?P ?r2)
                (not (at ?P ?r))
            )
    )

    (:action go-north
        :parameters (?P ?r ?r2)
        :precondition
            (and
                (is_player ?P)
                (is_room ?r)
                (is_room ?r2)
                (at ?P ?r)
                (north_of ?r2 ?r)
                (free ?r ?r2)
            )
        :effect
            (and
                (at ?P ?r2)
                (not (at ?P ?r))
            )
    )

    (:action go-south
        :parameters (?P ?r ?r2)
        :precondition
            (and
                (is_player ?P)
                (is_room ?r)
                (is_room ?r2)
                (at ?P ?r)
                (north_of ?r ?r2)
                (free ?r ?r2)
            )
        :effect
            (and
                (at ?P ?r2)
                (not (at ?P ?r))
            )
    )

    (:action go-west
        :parameters (?P ?r ?r2)
        :precondition
            (and
                (is_player ?P)
                (is_room ?r)
                (is_room ?r2)
                (at ?P ?r)
                (west_of ?r2 ?r)
                (free ?r ?r2)
            )
        :effect
            (and
                (at ?P ?r2)
                (not (at ?P ?r))
            )
    )

    (:action lock
        :parameters (?P ?lockable ?k)
        :precondition
            (and
                (is_player ?P)
                (reachable ?P ?lockable)
                (lockable ?lockable)
                (in ?k ?P)
                (match ?k ?lockable)
                (closed ?lockable)
            )
        :effect
            (and
                (locked ?lockable)
                (not (closed ?lockable))
            )
    )

    (:action unlock
        :parameters (?P ?r ?I ?unlockable ?k)
        :precondition
            (and
                (is_player ?P)
                (reachable ?P ?unlockable)
                (unlockable ?unlockable)
                (in ?k ?P)
                (match ?k ?unlockable)
                (locked ?unlockable)
            )
        :effect
            (and
                (closed ?unlockable)
                (not (locked ?unlockable))
            )
    )
)
