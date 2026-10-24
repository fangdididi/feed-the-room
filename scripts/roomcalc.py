#!/usr/bin/env python3
"""roomcalc.py - food-for-a-crowd arithmetic for the feed-the-room skill.

Standard library only. Every subcommand reads one plan file (party.json).

  heads   RSVP list -> expected eaters with a low/high range
  cover   who can safely eat what; flags guests without a full plate
  qty     how much of each dish to buy or cook, rounded up to packs
  budget  cost, cost per head, cap verdict, optional even split
  clock   table times: out at, swap at, off the table by
  tally   after the party: actual vs planned -> calibration for next time
  lint    check the plan file for missing or unknown fields

Exit code 0 = fine, 1 = a problem the host must look at, 2 = bad input.
"""
import argparse
import json
import math
import sys

# ---------------------------------------------------------------- constants

# Share of "yes" replies that actually turn up, by kind of gathering.
SHOW_RATE_YES = {
    "close": 0.92,    # family, close friends, a home party
    "work": 0.90,     # team lunch in working hours
    "paid": 0.85,     # people paid or put down a deposit
    "free": 0.70,     # free public / community RSVP
    "free-small": 0.63,  # free, fewer than 50 invited
}
SHOW_RATE_MAYBE = 0.35
SHOW_RATE_SILENT = {"close": 0.30, "work": 0.20}  # others: 0.10
SILENT_DEFAULT = 0.10
RANGE_SWING = 0.10  # +/- percentage points on every rate for low/high

AGE_WEIGHT = {"adult": 1.0, "teen": 1.2, "child": 0.5, "toddler": 0.0}

# Extra on top of computed need, by who controls the portion.
SERVICE_BUFFER = {
    "plated": 0.05,
    "boxed": 0.05,
    "family": 0.10,
    "buffet": 0.15,
    "grazing": 0.18,
}

# When a course offers k dishes a guest can eat, each is taken at this
# fraction of its single-dish portion (people take a bit of several).
SPLIT = {1: 1.0, 2: 0.6, 3: 0.45}
SPLIT_MANY = 0.35

FLAGS = {
    "beef", "pork", "poultry", "lamb", "fish", "shellfish", "egg", "dairy",
    "gluten", "peanut", "treenut", "sesame", "soy", "alcohol", "mustard",
    "celery", "lupin", "mollusc", "sulphite", "honey", "gelatin",
}
MEATS = {"beef", "pork", "poultry", "lamb", "gelatin"}
ANIMAL = MEATS | {"fish", "shellfish", "mollusc"}

# Diet -> flags a dish must not contain.
DIETS = {
    "vegetarian": ANIMAL,
    "vegan": ANIMAL | {"egg", "dairy", "honey"},
    "pescatarian": MEATS,
    "no-pork": {"pork"},
    "no-beef": {"beef"},
    "halal": {"pork", "alcohol"},  # plus: any meat must be halal_meat
    "gluten-free": {"gluten"},
    "dairy-free": {"dairy"},
    "no-alcohol": {"alcohol"},
}

HOLD_LIMIT_MIN = 120       # perishable at room temperature
HOLD_LIMIT_HOT_MIN = 60    # venue above 32 C / 90 F
PERISHABLE = {"hot", "cold", "ambient"}  # "shelf" = chips, bread, sealed drinks


class PlanError(Exception):
    pass


# ---------------------------------------------------------------- helpers

def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        raise PlanError(f"cannot read {path}: {e}")


def event_kind(plan):
    ev = plan.get("event", {})
    kind = ev.get("kind", "free")
    if kind == "free":
        invited = sum(1 + int(g.get("plus", 0)) for g in plan.get("guests", []))
        if invited < 50:
            kind = "free-small"
    return kind


def rates(plan):
    """Return {'yes','maybe','silent'} show rates, honouring overrides."""
    kind = event_kind(plan)
    r = {
        "yes": SHOW_RATE_YES.get(kind, SHOW_RATE_YES["free"]),
        "maybe": SHOW_RATE_MAYBE,
        "silent": SHOW_RATE_SILENT.get(kind, SILENT_DEFAULT),
    }
    r.update(plan.get("show_rate", {}) or {})
    return r


def guest_weight(g):
    w = AGE_WEIGHT.get(g.get("age", "adult"))
    if w is None:
        raise PlanError(f"guest {g.get('name')}: unknown age {g.get('age')!r}")
    return w * float(g.get("appetite", 1.0))


def rsvp_class(g):
    s = (g.get("rsvp") or "none").lower()
    if s in ("yes", "y", "going", "confirmed"):
        return "yes"
    if s in ("maybe", "tentative"):
        return "maybe"
    if s in ("no", "declined"):
        return "no"
    return "silent"


def clamp(x):
    return max(0.0, min(1.0, x))


def heads(plan):
    r = rates(plan)
    out = {"people": {"low": 0.0, "expected": 0.0, "high": 0.0},
           "eaters": {"low": 0.0, "expected": 0.0, "high": 0.0},
           "by_rsvp": {}, "rates": r, "kind": event_kind(plan), "walk_ins": 0}
    for g in plan.get("guests", []):
        c = rsvp_class(g)
        n = 1 + int(g.get("plus", 0))
        out["by_rsvp"][c] = out["by_rsvp"].get(c, 0) + n
        if c == "no":
            continue
        base = r[c]
        w = guest_weight(g)
        for key, p in (("low", clamp(base - RANGE_SWING)), ("expected", base),
                       ("high", clamp(base + RANGE_SWING))):
            out["people"][key] += n * p
            out["eaters"][key] += n * p * w
    walk = int(plan.get("event", {}).get("walk_ins", 0))
    out["walk_ins"] = walk
    for key in ("expected", "high"):
        out["people"][key] += walk
        out["eaters"][key] += walk
    for grp in ("people", "eaters"):
        for k in out[grp]:
            out[grp][k] = round(out[grp][k], 2)
    out["plan_for"] = math.ceil(out["eaters"]["expected"])
    out["reserve_for"] = math.ceil(out["eaters"]["high"])
    return out


def guest_needs(g):
    """Flags this guest must avoid, and whether any of them is an allergy."""
    avoid = set()
    for d in g.get("diet", []) or []:
        if d not in DIETS:
            raise PlanError(f"guest {g.get('name')}: unknown diet {d!r}")
        avoid |= DIETS[d]
    allergy = set(g.get("allergy", []) or [])
    bad = allergy - FLAGS
    if bad:
        raise PlanError(f"guest {g.get('name')}: unknown allergen {sorted(bad)}")
    return avoid, allergy


def verdict(g, dish):
    """SAFE, NO, or UNKNOWN for this guest and this dish, with a reason."""
    avoid, allergy = guest_needs(g)
    restricted = bool(avoid or allergy)
    if "contains" not in dish:
        return ("UNKNOWN", "dish has no ingredient list") if restricted else ("SAFE", "")
    contains = set(dish.get("contains", []))
    may = set(dish.get("may_contain", []))
    hit = allergy & contains
    if hit:
        return "NO", "allergy: contains " + ",".join(sorted(hit))
    hit = allergy & may
    if hit:
        return "NO", "allergy: may contain " + ",".join(sorted(hit))
    hit = avoid & contains
    if hit:
        return "NO", "diet: contains " + ",".join(sorted(hit))
    if "halal" in (g.get("diet") or []) and (contains & {"beef", "lamb", "poultry"}):
        if not dish.get("halal_meat"):
            return "NO", "diet: meat not marked halal"
    return "SAFE", ""


def courses(plan):
    out = {}
    for d in plan.get("menu", []):
        if d.get("reserve"):
            continue
        out.setdefault(d.get("course", "main"), []).append(d)
    return out


def cover(plan):
    req = plan.get("event", {}).get("must_cover", ["main"])
    rows, problems, set_aside = [], [], []
    by_course = courses(plan)
    for g in plan.get("guests", []):
        if rsvp_class(g) == "no" or guest_weight(g) == 0:
            continue
        avoid, allergy = guest_needs(g)
        row = {"guest": g.get("name"), "restricted": bool(avoid or allergy),
               "severe": bool(allergy), "courses": {}, "unknown": [], "blocked": []}
        for course, dishes in by_course.items():
            safe = []
            for d in dishes:
                v, why = verdict(g, d)
                if v == "SAFE":
                    safe.append(d["dish"])
                elif v == "UNKNOWN":
                    row["unknown"].append(d["dish"])
                else:
                    row["blocked"].append(f"{d['dish']} ({why})")
            row["courses"][course] = safe
        row["thin"] = [c for c in req if len(row["courses"].get(c, [])) == 1]
        for course in req:
            if not row["courses"].get(course):
                problems.append(f"{g.get('name')}: nothing safe in course '{course}'")
        if row["thin"] or (row["severe"] and row["restricted"]):
            set_aside.append(g.get("name"))
        if row["unknown"]:
            problems.append(f"{g.get('name')}: cannot verify {', '.join(row['unknown'])}")
        rows.append(row)
    return {"rows": rows, "problems": problems, "must_cover": req, "set_aside": set_aside}


def takes_original(g, dish, menu_by_name):
    """True if dish is an 'instead_of' alternative and this guest can eat the original."""
    ref = dish.get("instead_of")
    if not ref:
        return False
    orig = menu_by_name.get(ref)
    if orig is None:
        raise PlanError(f"{dish.get('dish')}: instead_of refers to unknown dish {ref!r}")
    return verdict(g, orig)[0] == "SAFE"


def split_factor(k):
    return SPLIT.get(k, SPLIT_MANY) if k > 0 else 0.0


def qty(plan):
    ev = plan.get("event", {})
    service = ev.get("service", "buffet")
    if service not in SERVICE_BUFFER:
        raise PlanError(f"unknown service style {service!r}")
    buf = float(ev.get("buffer", SERVICE_BUFFER[service]))
    h = heads(plan)
    r = h["rates"]
    by_course = courses(plan)
    menu_by_name = {d.get("dish"): d for d in plan.get("menu", [])}
    demand = {d["dish"]: {"expected": 0.0, "high": 0.0} for ds in by_course.values() for d in ds}
    for g in plan.get("guests", []):
        c = rsvp_class(g)
        if c == "no":
            continue
        n = 1 + int(g.get("plus", 0))
        w = guest_weight(g)
        if w == 0:
            continue
        for course, dishes in by_course.items():
            safe = [d for d in dishes if verdict(g, d)[0] == "SAFE"
                    and not takes_original(g, d, menu_by_name)]
            shared = [d for d in safe if not d.get("each")]
            f = split_factor(len(shared))
            for d in safe:
                share = 1.0 if d.get("each") else f
                weight = 1.0 if d.get("each") else w  # a slice of cake is a slice at any age
                for key, p in (("expected", r[c]), ("high", clamp(r[c] + RANGE_SWING))):
                    demand[d["dish"]][key] += n * p * weight * share * float(d["per_person"])
    walk = int(ev.get("walk_ins", 0))
    if walk:  # walk-ins are unknown: assume no restrictions
        for course, dishes in by_course.items():
            plain = [d for d in dishes if not d.get("instead_of")]
            f = split_factor(len([d for d in plain if not d.get("each")]))
            for d in plain:
                share = 1.0 if d.get("each") else f
                for key in ("expected", "high"):
                    demand[d["dish"]][key] += walk * share * float(d["per_person"])
    lines = []
    for ds in by_course.values():
        for d in ds:
            need = demand[d["dish"]]["expected"] * (1 + buf)
            high = demand[d["dish"]]["high"] * (1 + buf)
            yield_ = float(d.get("yield", 1.0))  # usable share after trim/bone/peel/shrink
            purchase = need / yield_
            pack = float(d.get("pack", 0) or 0)
            packs = math.ceil(round(purchase / pack, 6)) if pack else None
            buy = packs * pack if pack else math.ceil(purchase)
            if pack:
                cost = packs * float(d.get("pack_price", 0))
            else:
                cost = buy * float(d.get("unit_price", 0))
            lines.append({
                "dish": d["dish"], "course": d.get("course", "main"),
                "unit": d.get("unit", "g"), "need": round(need, 1),
                "need_high": round(high, 1), "yield": yield_, "packs": packs,
                "buy": round(buy, 1),
                "short_at_high": round(max(0.0, high / yield_ - buy) * yield_, 1),
                "cost": round(cost, 2),
            })
    # Reserve items: cheap shelf-stable food sized to the gap at the high count.
    gap = max(0.0, h["eaters"]["high"] - h["eaters"]["expected"])
    for d in plan.get("menu", []):
        if not d.get("reserve"):
            continue
        need = gap * float(d["per_person"])
        pack = float(d.get("pack", 0) or 0)
        packs = math.ceil(round(need / pack, 6)) if pack else None
        lines.append({
            "dish": d["dish"], "course": "reserve", "unit": d.get("unit", "g"),
            "need": round(need, 1), "need_high": round(need, 1), "packs": packs,
            "buy": round(packs * pack if pack else math.ceil(need), 1),
            "yield": 1.0, "short_at_high": 0.0,
            "cost": round((packs or 0) * float(d.get("pack_price", 0)), 2),
        })
    hours = float(ev.get("hours", 2))
    hot = bool(ev.get("hot_venue"))
    people = h["people"]["expected"]
    supplies = {
        "drinks_servings": math.ceil(people * (2 + max(0.0, hours - 1)) * (1.25 if hot else 1.0)),
        "ice_kg": math.ceil(people * 0.5 * (1.5 if hot else 1.0)),
        "plates": math.ceil(people * 1.5),
        "cups": math.ceil(people * 2),
        "napkins": math.ceil(people * 3),
    }
    if not ev.get("drinks", True):
        supplies.pop("drinks_servings")
    return {"service": service, "buffer": buf, "heads": h, "lines": lines, "supplies": supplies}


def even_split(total, n):
    """Split total (2 decimals) into n shares that add back exactly."""
    if n <= 0:
        raise PlanError("split needs at least one payer")
    cents = int(round(total * 100))
    base, extra = divmod(cents, n)
    return [(base + (1 if i < extra else 0)) / 100 for i in range(n)]


def budget(plan, payers=None):
    q = qty(plan)
    total = round(sum(l["cost"] for l in q["lines"]) + float(plan.get("event", {}).get("other_costs", 0)), 2)
    people = q["heads"]["people"]["expected"]
    cap = plan.get("event", {}).get("budget_total")
    out = {"total": total, "per_head": round(total / people, 2) if people else None,
           "cap": cap, "verdict": "NO CAP"}
    if cap is not None:
        cap = float(cap)
        if total > cap:
            out["verdict"] = "OVER"
        elif total > 0.9 * cap:
            out["verdict"] = "TIGHT"
        else:
            out["verdict"] = "UNDER"
        out["headroom"] = round(cap - total, 2)
    lines = sorted(q["lines"], key=lambda l: -l["cost"])
    out["biggest"] = [(l["dish"], l["cost"]) for l in lines[:3]]
    if payers:
        out["split"] = even_split(total, payers)
    return out


def hm(s):
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def fmt(m):
    m %= 24 * 60
    return f"{m // 60:02d}:{m % 60:02d}"


def clock(plan):
    ev = plan.get("event", {})
    start = hm(ev.get("serve_at", ev.get("start", "12:00")))
    end = start + int(round(float(ev.get("hours", 2)) * 60))
    limit = HOLD_LIMIT_HOT_MIN if ev.get("hot_venue") else HOLD_LIMIT_MIN
    rows = []
    for d in plan.get("menu", []):
        hold = d.get("hold", "ambient")
        out_at = hm(d["out_at"]) if d.get("out_at") else start
        if hold not in PERISHABLE or d.get("held"):
            rows.append({"dish": d["dish"], "hold": hold, "out": fmt(out_at),
                         "batches": 1, "swaps": [], "off_by": None,
                         "note": "temperature-held: check every 2 h" if d.get("held") else "shelf-stable"})
            continue
        span = max(0, end - out_at)
        batches = max(1, math.ceil(span / limit))
        swaps = [fmt(out_at + limit * i) for i in range(1, batches)]
        off_by = out_at + limit * batches
        note = (f"{batches} small platters; put a fresh one out at each swap, never top up"
                if batches > 1 else "one platter")
        rows.append({"dish": d["dish"], "hold": hold, "out": fmt(out_at),
                     "batches": batches, "swaps": swaps, "off_by": fmt(off_by),
                     "note": note + "; leftovers into the fridge or bin by off-by time"})
    return {"limit_min": limit, "start": fmt(start), "end": fmt(end), "rows": rows}


def tally(plan, result):
    """Compare what happened with the plan; return calibration numbers."""
    q = qty(plan)
    h = q["heads"]
    actual = result.get("actual_people")
    out = {"predicted_people": h["people"]["expected"], "actual_people": actual, "dishes": []}
    if actual is not None and h["people"]["expected"]:
        out["turnout_vs_prediction"] = round(actual / h["people"]["expected"], 2)
    menu_by_name = {d.get("dish"): d for d in plan.get("menu", [])}
    ratios = []
    for l in q["lines"]:
        if l["course"] == "reserve":
            continue
        r = (result.get("dishes") or {}).get(l["dish"])
        if r is None:
            continue
        left = float(r.get("left", 0))
        eaten = (1 - left) * l["buy"] * l["yield"]
        row = {"dish": l["dish"], "bought": l["buy"], "eaten": round(eaten, 1),
               "left_share": left}
        if r.get("ran_out_at"):
            row["status"] = "RAN OUT"
            row["note"] = f"ran out at {r['ran_out_at']}: true demand was higher; raise next time"
        else:
            base = l["need"] / (1 + q["buffer"])  # demand before the service buffer
            ratio = eaten / base if base else None
            row["eaten_vs_plan"] = round(ratio, 2) if ratio is not None else None
            if ratio is not None:
                ratios.append(ratio)
            row["status"] = "TOO MUCH" if left >= 0.25 else "ABOUT RIGHT"
            if ratio is not None and menu_by_name.get(l["dish"], {}).get("instead_of"):
                ratios.pop()  # alternatives get nibbled by everyone; not a fair appetite signal
            rounding = l["buy"] * l["yield"] - l["need"]
            if left > 0 and rounding > 0 and left * l["buy"] * l["yield"] <= rounding + 1e-9:
                row["note"] = "leftover is no more than the pack rounding; a smaller pack size fixes it"
        out["dishes"].append(row)
    if ratios:
        s = sorted(ratios)
        mid = len(s) // 2
        med = s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2
        out["crowd_appetite"] = round(med, 2)
    return out


def lint(plan):
    issues = []
    ev = plan.get("event")
    if not isinstance(ev, dict):
        issues.append("missing 'event' block")
        ev = {}
    for k in ("kind", "service", "hours"):
        if k not in ev:
            issues.append(f"event.{k} missing (a default will be used)")
    if not plan.get("guests"):
        issues.append("no guests listed")
    if not plan.get("menu"):
        issues.append("no menu")
    for g in plan.get("guests", []):
        try:
            guest_needs(g)
            guest_weight(g)
        except PlanError as e:
            issues.append(str(e))
    names = set()
    for d in plan.get("menu", []):
        n = d.get("dish")
        if not n:
            issues.append("a menu item has no 'dish' name")
            continue
        if n in names:
            issues.append(f"duplicate dish name {n!r}")
        names.add(n)
        if "per_person" not in d:
            issues.append(f"{n}: per_person missing")
        if "contains" not in d:
            issues.append(f"{n}: no 'contains' list - restricted guests will treat it as unsafe")
        if d.get("instead_of") and d["instead_of"] not in {m.get("dish") for m in plan.get("menu", [])}:
            issues.append(f"{n}: instead_of points at unknown dish {d['instead_of']!r}")
        for f in set(d.get("contains", [])) | set(d.get("may_contain", [])):
            if f not in FLAGS:
                issues.append(f"{n}: unknown flag {f!r}")
    return issues


# ---------------------------------------------------------------- printing

def print_heads(h):
    print(f"kind: {h['kind']}  rates: yes {h['rates']['yes']:.2f} maybe {h['rates']['maybe']:.2f} "
          f"silent {h['rates']['silent']:.2f}")
    print("replies: " + ", ".join(f"{k} {v}" for k, v in sorted(h["by_rsvp"].items())))
    p, e = h["people"], h["eaters"]
    print(f"people  low {p['low']:.1f}  expected {p['expected']:.1f}  high {p['high']:.1f}")
    print(f"eaters  low {e['low']:.1f}  expected {e['expected']:.1f}  high {e['high']:.1f}  (adult = 1)")
    print(f"plan perishables for {h['plan_for']} eaters; reserve covers up to {h['reserve_for']}")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="roomcalc", description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=["heads", "cover", "qty", "budget", "clock", "tally", "lint"])
    ap.add_argument("plan")
    ap.add_argument("--result", help="tally: JSON with actual_people and per-dish leftovers")
    ap.add_argument("--split", type=int, help="budget: number of payers for an even split")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        plan = load(a.plan)
        if a.cmd == "heads":
            res = heads(plan)
            if a.json:
                print(json.dumps(res, ensure_ascii=False, indent=1))
            else:
                print_heads(res)
            return 0
        if a.cmd == "cover":
            res = cover(plan)
            if a.json:
                print(json.dumps(res, ensure_ascii=False, indent=1))
            else:
                for r in res["rows"]:
                    if not r["restricted"]:
                        continue
                    mark = "ALLERGY" if r["severe"] else "diet"
                    parts = "; ".join(f"{c}: {', '.join(v) or '-'}" for c, v in r["courses"].items())
                    print(f"{r['guest']} [{mark}] {parts}")
                    for b in r["blocked"]:
                        print(f"    x {b}")
                    for c in r["thin"]:
                        print(f"    ! only one safe choice in '{c}'")
                if res["set_aside"]:
                    print("SET ASIDE a labelled plate before service for: " + ", ".join(res["set_aside"]))
                print("OK: every guest has a safe plate" if not res["problems"] else "PROBLEMS:")
                for p in res["problems"]:
                    print("  - " + p)
            return 1 if res["problems"] else 0
        if a.cmd == "qty":
            res = qty(plan)
            if a.json:
                print(json.dumps(res, ensure_ascii=False, indent=1))
                return 0
            print(f"service {res['service']}, buffer {res['buffer']:.0%}, "
                  f"plan for {res['heads']['plan_for']} eaters (high {res['heads']['reserve_for']})")
            for l in res["lines"]:
                packs = f"{l['packs']} packs = " if l["packs"] is not None else ""
                raw = f" (usable share {l['yield']:.0%})" if l["yield"] != 1.0 else ""
                warn = f"  short {l['short_at_high']} at high" if l["short_at_high"] > 0 else ""
                print(f"{l['course']:<8} {l['dish']:<28} need {l['need']:>8} {l['unit']:<4} buy {packs}{l['buy']}{raw}{warn}")
            for k, v in res["supplies"].items():
                print(f"supply   {k:<28} {v}")
            reserve = any(l["course"] == "reserve" for l in res["lines"])
            short = any(l["short_at_high"] > 0 for l in res["lines"])
            if short and not reserve:
                print("NOTE: some dishes run short if the high count turns up and there is no reserve item")
                return 1
            return 0
        if a.cmd == "budget":
            res = budget(plan, a.split)
            if a.json:
                print(json.dumps(res, ensure_ascii=False, indent=1))
            else:
                cur = plan.get("event", {}).get("currency", "")
                print(f"total {cur}{res['total']:.2f}  per head {cur}{res['per_head']:.2f}  "
                      f"cap {res['cap']}  verdict {res['verdict']}")
                print("biggest lines: " + ", ".join(f"{d} {cur}{c:.2f}" for d, c in res["biggest"]))
                if "split" in res:
                    print("even split: " + " / ".join(f"{cur}{s:.2f}" for s in res["split"]))
            return 1 if res["verdict"] == "OVER" else 0
        if a.cmd == "clock":
            res = clock(plan)
            if a.json:
                print(json.dumps(res, ensure_ascii=False, indent=1))
            else:
                print(f"party {res['start']}-{res['end']}, room-temperature limit {res['limit_min']} min")
                for r in res["rows"]:
                    sw = (" swap " + ", ".join(r["swaps"])) if r["swaps"] else ""
                    off = f" off by {r['off_by']}" if r["off_by"] else ""
                    print(f"{r['dish']:<28} {r['hold']:<8} out {r['out']}{sw}{off}  [{r['note']}]")
            return 0
        if a.cmd == "tally":
            if not a.result:
                raise PlanError("tally needs --result FILE")
            res = tally(plan, load(a.result))
            print(json.dumps(res, ensure_ascii=False, indent=1))
            return 0
        if a.cmd == "lint":
            issues = lint(plan)
            for i in issues:
                print("- " + i)
            print("lint: clean" if not issues else f"lint: {len(issues)} issue(s)")
            return 1 if issues else 0
    except PlanError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
