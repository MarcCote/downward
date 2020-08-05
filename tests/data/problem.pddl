(define (problem textworld-game-1)
    (:domain textworld)
    (:objects
        P
        d_0
        r_0 r_1
        c_0
        s_0
        t_0 - t
    )
    (:init
        (is_player P)
        (is_container c_0)
        (is_supporter s_0)
        (is_room r_0)
        (is_room r_1)
        (is_door d_0)

        (openable d_0)
        (closable d_0)

        (openable c_0)
        (closable c_0)

        (portable t_0)

        (at P r_0)
        (at c_0 r_1)
        (at s_0 r_0)
        (closed d_0)
        (closed c_0)
        (in t_0 P)

        (link r_1 d_0 r_0)
        (link r_0 d_0 r_1)
        (east_of r_1 r_0)
        (west_of r_0 r_1)
        ; (free r_0 r_1)
        ; (free r_1 r_0)
    )
    (:goal
        (and
            ; (at P r_1)
            (examined P)
            (examined c_0)
        )
    )
)
