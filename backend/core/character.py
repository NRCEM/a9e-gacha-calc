# ==== Rates / pity ====
BASE_6_RATE = 0.008
SOFT_PITY_START = 66
SOFT_PITY_STEP = 0.05
HARD_PITY_6 = 80

# Banner mechanics
HARD_PITY_LIMITED = 120  # "MP": guaranteed current limited at 120 if not obtained before
P_CUR_LIMITED = 0.50
P_OTHER_LIMITED_TOTAL = 0.1428
P_OFF = 1.0 - P_CUR_LIMITED - P_OTHER_LIMITED_TOTAL

# Simplified 5★/4★ split when "no 6★"
RATE_5 = 0.08
RATE_4 = 0.912
DENOM_54 = RATE_5 + RATE_4
P5_COND = RATE_5 / DENOM_54  # P(5★ | not 6★)
P4_COND = RATE_4 / DENOM_54  # P(4★ | not 6★)


def rate_6star(pity6: int) -> float:
    if pity6 < SOFT_PITY_START:
        return BASE_6_RATE
    if pity6 < HARD_PITY_6 - 1:
        return BASE_6_RATE + SOFT_PITY_STEP * (pity6 - SOFT_PITY_START + 1)
    return 1.0


def limited_curve(rolls: int, pity6: int, mp: int):
    """
    Curve of P(get current banner limited at least once) vs pulls.
    Uses absorbing success DP (stops tracking once limited is obtained).
    """
    pity6 = max(0, min(HARD_PITY_6 - 1, pity6))
    mp = max(0, min(HARD_PITY_LIMITED - 1, mp))

    dp = [[0.0] * HARD_PITY_LIMITED for _ in range(HARD_PITY_6)]
    dp[pity6][mp] = 1.0

    p_cur = 0.0
    curve = [{"x": 0, "y": 0.0}]

    for i in range(rolls):
        nxt = [[0.0] * HARD_PITY_LIMITED for _ in range(HARD_PITY_6)]

        for p in range(HARD_PITY_6):
            for m in range(HARD_PITY_LIMITED):
                w = dp[p][m]
                if w == 0.0:
                    continue

                # Forced current limited at MP == 119
                if m == HARD_PITY_LIMITED - 1:
                    p_cur += w
                    continue

                r6 = rate_6star(p)

                # current limited (absorbing)
                p_cur += w * r6 * P_CUR_LIMITED

                # any other 6★ keeps rolling, pity resets, MP increases
                w_other6 = w * r6 * (1.0 - P_CUR_LIMITED)
                if w_other6:
                    nxt[0][m + 1] += w_other6

                # no 6★: pity increases, MP increases
                w_n6 = w * (1.0 - r6)
                if w_n6:
                    nxt[min(p + 1, HARD_PITY_6 - 1)][m + 1] += w_n6

        dp = nxt
        curve.append({"x": i + 1, "y": min(1.0, p_cur)})

        if p_cur >= 1.0 - 1e-15:
            for r in range(i + 2, rolls + 1):
                curve.append({"x": r, "y": 1.0})
            break

    return curve


def min_guaranteed_6star(rolls: int, pity6: int, mp: int) -> int:
    """
    Deterministic worst-luck minimum 6★ count:
    - Only triggers at hard pity 80 (pity6 == 79 before a roll)
    - And MP hard guarantee 120 (mp == 119 before a roll), which forces current limited
    MP guarantee happens "before RNG" in worst-luck simulation.
    """
    pity6 = max(0, min(HARD_PITY_6 - 1, pity6))
    mp = max(0, min(HARD_PITY_LIMITED - 1, mp))

    n6 = 0
    p = pity6
    m = mp

    for _ in range(rolls):
        # MP hard guarantee
        if m == HARD_PITY_LIMITED - 1:
            n6 += 1
            p = 0
            m = 0
            continue

        # 6★ hard pity (80th)
        if p == HARD_PITY_6 - 1:
            n6 += 1
            p = 0
            m = m + 1
            continue

        # Otherwise: no 6★ in worst-luck
        p = min(p + 1, HARD_PITY_6 - 1)
        m = m + 1

    return n6


def expected_5star(rolls: int, pity6: int, mp: int) -> float:
    """
    E[#5★] with 10-pull guarantee:
      - Every 10 pulls, you are guaranteed at least one 5★+ (5★ or 6★).
      - We model the guarantee exactly by tracking t = consecutive pulls since last 5★+ (0..9).
      - If t == 9 (10th pull without 5★+), and the roll would be 4★, it is forced to 5★.
    Note: This still uses the simplified 5★/4★ split when "no 6★".
    """
    pity6 = max(0, min(HARD_PITY_6 - 1, pity6))
    mp = max(0, min(HARD_PITY_LIMITED - 1, mp))

    # dp[pity6][mp][t]
    dp = [[[0.0] * 10 for _ in range(HARD_PITY_LIMITED)] for _ in range(HARD_PITY_6)]
    dp[pity6][mp][0] = 1.0

    e5 = 0.0

    for _ in range(rolls):
        nxt = [[[0.0] * 10 for _ in range(HARD_PITY_LIMITED)] for _ in range(HARD_PITY_6)]

        for p in range(HARD_PITY_6):
            for m in range(HARD_PITY_LIMITED):
                for t in range(10):
                    w = dp[p][m][t]
                    if w == 0.0:
                        continue

                    # Forced current limited: guaranteed 6★ (counts as 5★+), resets t and mp
                    if m == HARD_PITY_LIMITED - 1:
                        nxt[0][0][0] += w
                        continue

                    r6 = rate_6star(p)

                    # --- 6★ happens (5★+ satisfied) ---
                    w6 = w * r6
                    if w6:
                        # current limited resets mp
                        w_cur = w6 * P_CUR_LIMITED
                        if w_cur:
                            nxt[0][0][0] += w_cur
                        # other 6★ continues mp
                        w_other6 = w6 * (1.0 - P_CUR_LIMITED)
                        if w_other6:
                            nxt[0][m + 1][0] += w_other6

                    # --- not 6★: split 5★ / 4★ with 10-pull guarantee ---
                    w_n6 = w * (1.0 - r6)
                    if not w_n6:
                        continue

                    # If this is the 10th pull without 5★+ (t == 9), then 4★ is forced to 5★
                    if t == 9:
                        # forced 5★
                        e5 += w_n6
                        nxt[min(p + 1, HARD_PITY_6 - 1)][m + 1][0] += w_n6
                    else:
                        # normal 5★
                        w5 = w_n6 * P5_COND
                        if w5:
                            e5 += w5
                            nxt[min(p + 1, HARD_PITY_6 - 1)][m + 1][0] += w5

                        # normal 4★
                        w4 = w_n6 * P4_COND
                        if w4:
                            nxt[min(p + 1, HARD_PITY_6 - 1)][m + 1][t + 1] += w4

        dp = nxt

    return e5


def prob_at_least_one_category(rolls: int, pity6: int, mp: int, p_cat_on_6: float) -> float:
    """
    Probability of seeing a given 6★ category at least once (absorbing).
    Category happens on any non-forced 6★ with probability p_cat_on_6.
    MP forced roll is always current limited, so it never counts for OFF/OTHER categories.
    """
    pity6 = max(0, min(HARD_PITY_6 - 1, pity6))
    mp = max(0, min(HARD_PITY_LIMITED - 1, mp))

    dp = [[0.0] * HARD_PITY_LIMITED for _ in range(HARD_PITY_6)]
    dp[pity6][mp] = 1.0

    hit = 0.0

    for _ in range(rolls):
        nxt = [[0.0] * HARD_PITY_LIMITED for _ in range(HARD_PITY_6)]

        for p in range(HARD_PITY_6):
            for m in range(HARD_PITY_LIMITED):
                w = dp[p][m]
                if w == 0.0:
                    continue

                # Forced current limited: can't be OFF/OTHER
                if m == HARD_PITY_LIMITED - 1:
                    nxt[0][0] += w
                    continue

                r6 = rate_6star(p)

                # category hit
                w_hit = w * r6 * p_cat_on_6
                hit += w_hit

                # 6★ not category
                w_6_not = w * r6 * (1.0 - p_cat_on_6)
                if w_6_not:
                    w_cur = w_6_not * (P_CUR_LIMITED / (1.0 - p_cat_on_6)) if (1.0 - p_cat_on_6) > 0 else 0.0
                    w_notcur = w_6_not - w_cur

                    if w_cur:
                        nxt[0][0] += w_cur
                    if w_notcur:
                        nxt[0][m + 1] += w_notcur

                # no 6★
                w_n6 = w * (1.0 - r6)
                if w_n6:
                    nxt[min(p + 1, HARD_PITY_6 - 1)][m + 1] += w_n6

        dp = nxt

    return hit


def analyze(rolls: int, pity6: int, mp: int) -> dict:
    curve = limited_curve(rolls, pity6, mp)
    p_current = curve[-1]["y"]
    p_off = prob_at_least_one_category(rolls, pity6, mp, P_OFF)
    p_other = prob_at_least_one_category(rolls, pity6, mp, P_OTHER_LIMITED_TOTAL)

    return {
        "p_current_limited": p_current,
        "p_off": p_off,
        "p_other_limited": p_other,
        "min_6star": min_guaranteed_6star(rolls, pity6, mp),
        "e_5star": expected_5star(rolls, pity6, mp),
        "curve": curve,
    }
