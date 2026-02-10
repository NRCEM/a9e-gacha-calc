from collections import defaultdict

# ==== Rates / pity ====
BASE_6_RATE = 0.008
SOFT_PITY_START = 66
SOFT_PITY_STEP = 0.05
HARD_PITY_6 = 80

# Banner mechanics
HARD_PITY_LIMITED = 120  # MP: guaranteed current limited at 120 if not obtained before
HARD_PITY_SPARK = 240    # CP: after getting current limited, MP is removed; CP guarantees at 240 since last limited

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
    Absorbing DP: once current limited is obtained, we stop tracking that path.
    Note: MP->CP change does not affect this curve because it only cares about the first current limited.
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


def _is_forced_limited(mode: int, counter: int) -> bool:
    # mode 0: pre-limited uses MP (0..119); forced at 119
    # mode 1: post-limited uses CP (0..239); forced at 239
    return (mode == 0 and counter == HARD_PITY_LIMITED - 1) or (mode == 1 and counter == HARD_PITY_SPARK - 1)


def _counter_max(mode: int) -> int:
    return (HARD_PITY_LIMITED - 1) if mode == 0 else (HARD_PITY_SPARK - 1)


def _inc_counter(mode: int, counter: int) -> int:
    mx = _counter_max(mode)
    return counter + 1 if counter < mx else mx


def min_guaranteed_6star(rolls: int, pity6: int, mp: int) -> int:
    """
    Deterministic "worst luck" minimum 6★ count:
    - Hard pity 80 always triggers a 6★.
    - Before first current limited: MP forces current limited at 120.
    - After current limited: CP forces current limited at 240 since last current limited.
    This assumes hard-pity 6★ is NOT the current limited (to keep guarantees as far as possible).
    """
    pity6 = max(0, min(HARD_PITY_6 - 1, pity6))
    mp = max(0, min(HARD_PITY_LIMITED - 1, mp))

    n6 = 0
    p = pity6

    mode = 0          # 0 = MP active, 1 = CP active
    counter = mp      # MP or CP depending on mode

    for _ in range(rolls):
        if _is_forced_limited(mode, counter):
            n6 += 1
            p = 0
            mode = 1
            counter = 0
            continue

        if p == HARD_PITY_6 - 1:
            n6 += 1
            p = 0
            counter = _inc_counter(mode, counter)
            continue

        p = min(p + 1, HARD_PITY_6 - 1)
        counter = _inc_counter(mode, counter)

    return n6


def expected_5star(rolls: int, pity6: int, mp: int) -> float:
    """
    E[#5★] with:
      - MP->CP rule:
          * Before first current limited: MP forces current limited at 120.
          * After getting current limited: MP is removed; CP forces at 240 since last current limited.
      - 10-pull guarantee:
          * Every 10 pulls, guaranteed at least one 5★+ (5★ or 6★).
          * Track t = consecutive pulls since last 5★+ (0..9).
          * If t == 9 and a non-6★ would be 4★, force it to 5★.
    Uses sparse DP: state = (pity6, mode, counter, t).
    """
    pity6 = max(0, min(HARD_PITY_6 - 1, pity6))
    mp = max(0, min(HARD_PITY_LIMITED - 1, mp))

    dp = defaultdict(float)
    dp[(pity6, 0, mp, 0)] = 1.0

    e5 = 0.0

    for _ in range(rolls):
        nxt = defaultdict(float)

        for (p, mode, counter, t), w in dp.items():
            if w == 0.0:
                continue

            # Forced current limited (MP/CP)
            if _is_forced_limited(mode, counter):
                nxt[(0, 1, 0, 0)] += w
                continue

            r6 = rate_6star(p)

            # ---- 6★ outcomes (counts as 5★+) ----
            w6 = w * r6
            if w6:
                # current limited: switches to CP mode, resets counter
                nxt[(0, 1, 0, 0)] += w6 * P_CUR_LIMITED

                # non-current 6★: keep mode, counter increases
                c2 = _inc_counter(mode, counter)
                nxt[(0, mode, c2, 0)] += w6 * (1.0 - P_CUR_LIMITED)

            # ---- not 6★: 5★/4★ with 10-pull guarantee ----
            wn6 = w * (1.0 - r6)
            if not wn6:
                continue

            p2 = min(p + 1, HARD_PITY_6 - 1)
            c2 = _inc_counter(mode, counter)

            if t == 9:
                # force 5★
                e5 += wn6
                nxt[(p2, mode, c2, 0)] += wn6
            else:
                w5 = wn6 * P5_COND
                if w5:
                    e5 += w5
                    nxt[(p2, mode, c2, 0)] += w5

                w4 = wn6 * P4_COND
                if w4:
                    nxt[(p2, mode, c2, t + 1)] += w4

        dp = nxt

    return e5


def prob_at_least_one_category(rolls: int, pity6: int, mp: int, category: str) -> float:
    """
    Probability of seeing a 6★ category at least once (absorbing), with MP->CP rule applied.
    category in {"off", "other"}:
      - "off"   : off-banner 6★
      - "other" : other-version limited 6★ (the 2 other limiteds in the same version)
    Forced limited (MP/CP) is always current limited, so it never counts for "off"/"other".
    Sparse DP: state = (pity6, mode, counter).
    """
    pity6 = max(0, min(HARD_PITY_6 - 1, pity6))
    mp = max(0, min(HARD_PITY_LIMITED - 1, mp))

    if category == "off":
        p_hit = P_OFF
        p_noncur_nonhit = P_OTHER_LIMITED_TOTAL
    elif category == "other":
        p_hit = P_OTHER_LIMITED_TOTAL
        p_noncur_nonhit = P_OFF
    else:
        raise ValueError("category must be 'off' or 'other'")

    dp = defaultdict(float)
    dp[(pity6, 0, mp)] = 1.0

    hit = 0.0

    for _ in range(rolls):
        nxt = defaultdict(float)

        for (p, mode, counter), w in dp.items():
            if w == 0.0:
                continue

            # Forced current limited: doesn't count as hit, switches to CP mode
            if _is_forced_limited(mode, counter):
                nxt[(0, 1, 0)] += w
                continue

            r6 = rate_6star(p)

            # 6★ happens
            w6 = w * r6
            if w6:
                # absorb on hit category
                hit += w6 * p_hit

                # current limited (non-hit): switch to CP mode, reset counter
                nxt[(0, 1, 0)] += w6 * P_CUR_LIMITED

                # other non-current non-hit category: keep mode, counter increases
                c2 = _inc_counter(mode, counter)
                nxt[(0, mode, c2)] += w6 * p_noncur_nonhit

            # no 6★
            wn6 = w * (1.0 - r6)
            if wn6:
                p2 = min(p + 1, HARD_PITY_6 - 1)
                c2 = _inc_counter(mode, counter)
                nxt[(p2, mode, c2)] += wn6

        dp = nxt

    return hit


def analyze(rolls: int, pity6: int, mp: int) -> dict:
    curve = limited_curve(rolls, pity6, mp)
    p_current = curve[-1]["y"]

    p_off = prob_at_least_one_category(rolls, pity6, mp, "off")
    p_other = prob_at_least_one_category(rolls, pity6, mp, "other")

    return {
        "p_current_limited": p_current,
        "p_off": p_off,
        "p_other_limited": p_other,
        "min_6star": min_guaranteed_6star(rolls, pity6, mp),
        "e_5star": expected_5star(rolls, pity6, mp),
        "curve": curve,
    }
