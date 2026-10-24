import copy
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import roomcalc as rc  # noqa: E402

EXAMPLE = os.path.join(HERE, "..", "examples", "party.json")


def base_plan(**event):
    ev = {"kind": "close", "service": "plated", "hours": 2, "serve_at": "12:00"}
    ev.update(event)
    return {
        "event": ev,
        "guests": [{"name": f"g{i}", "rsvp": "yes", "age": "adult"} for i in range(10)],
        "menu": [{"dish": "Pasta", "course": "main", "per_person": 100, "unit": "g",
                  "contains": ["gluten"], "hold": "hot"}],
    }


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = rc.main(argv)
    return code, out.getvalue(), err.getvalue()


def write(plan):
    f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    json.dump(plan, f)
    f.close()
    return f.name


class Heads(unittest.TestCase):
    def test_close_yes_rate(self):
        h = rc.heads(base_plan())
        self.assertAlmostEqual(h["people"]["expected"], 9.2)
        self.assertEqual(h["plan_for"], 10)

    def test_free_small_kicks_in_under_50(self):
        h = rc.heads(base_plan(kind="free"))
        self.assertEqual(h["kind"], "free-small")
        self.assertAlmostEqual(h["people"]["expected"], 6.3)

    def test_free_large_uses_free_rate(self):
        p = base_plan(kind="free")
        p["guests"] = [{"name": str(i), "rsvp": "yes"} for i in range(60)]
        self.assertAlmostEqual(rc.heads(p)["people"]["expected"], 42.0)

    def test_override_rate_from_history(self):
        p = base_plan()
        p["show_rate"] = {"yes": 0.5}
        self.assertAlmostEqual(rc.heads(p)["people"]["expected"], 5.0)

    def test_declined_ignored_and_plus_counted(self):
        p = base_plan()
        p["guests"] = [{"name": "a", "rsvp": "no", "plus": 3},
                       {"name": "b", "rsvp": "yes", "plus": 1}]
        h = rc.heads(p)
        self.assertAlmostEqual(h["people"]["expected"], 1.84)
        self.assertEqual(h["by_rsvp"]["no"], 4)

    def test_age_weights_change_eaters_not_people(self):
        p = base_plan()
        p["guests"] = [{"name": "kid", "rsvp": "yes", "age": "child"},
                       {"name": "baby", "rsvp": "yes", "age": "toddler"}]
        h = rc.heads(p)
        self.assertAlmostEqual(h["people"]["expected"], 1.84)
        self.assertAlmostEqual(h["eaters"]["expected"], 0.46)

    def test_range_is_clamped(self):
        p = base_plan()
        p["show_rate"] = {"yes": 0.97}
        h = rc.heads(p)
        self.assertAlmostEqual(h["people"]["high"], 10.0)

    def test_walk_ins_added_to_expected_and_high_only(self):
        h = rc.heads(base_plan(walk_ins=3))
        self.assertAlmostEqual(h["people"]["expected"], 12.2)
        self.assertAlmostEqual(h["people"]["low"], 8.2)

    def test_unknown_age_is_an_error(self):
        p = base_plan()
        p["guests"][0]["age"] = "giant"
        with self.assertRaises(rc.PlanError):
            rc.heads(p)


class Cover(unittest.TestCase):
    def guest(self, **kw):
        g = {"name": "x", "rsvp": "yes"}
        g.update(kw)
        return g

    def test_allergy_blocks_may_contain(self):
        v, why = rc.verdict(self.guest(allergy=["peanut"]),
                            {"dish": "d", "contains": [], "may_contain": ["peanut"]})
        self.assertEqual(v, "NO")
        self.assertIn("may contain", why)

    def test_diet_ignores_may_contain(self):
        v, _ = rc.verdict(self.guest(diet=["vegetarian"]),
                          {"dish": "d", "contains": [], "may_contain": ["fish"]})
        self.assertEqual(v, "SAFE")

    def test_unlabelled_dish_unknown_only_for_restricted(self):
        d = {"dish": "mystery"}
        self.assertEqual(rc.verdict(self.guest(diet=["vegan"]), d)[0], "UNKNOWN")
        self.assertEqual(rc.verdict(self.guest(), d)[0], "SAFE")

    def test_halal_needs_marked_meat(self):
        g = self.guest(diet=["halal"])
        self.assertEqual(rc.verdict(g, {"dish": "c", "contains": ["poultry"]})[0], "NO")
        self.assertEqual(rc.verdict(g, {"dish": "c", "contains": ["poultry"], "halal_meat": True})[0], "SAFE")

    def test_vegan_blocks_honey_and_dairy(self):
        g = self.guest(diet=["vegan"])
        self.assertEqual(rc.verdict(g, {"dish": "t", "contains": ["honey"]})[0], "NO")
        self.assertEqual(rc.verdict(g, {"dish": "t", "contains": ["dairy"]})[0], "NO")

    def test_problem_when_course_empty(self):
        p = base_plan()
        p["guests"].append({"name": "Nina", "rsvp": "yes", "diet": ["gluten-free"]})
        res = rc.cover(p)
        self.assertTrue(any("Nina" in x for x in res["problems"]))
        code, out, _ = run(["cover", write(p)])
        self.assertEqual(code, 1)

    def test_set_aside_for_allergy_and_thin_choice(self):
        res = rc.cover(json.load(open(EXAMPLE)))
        self.assertEqual(res["problems"], [])
        self.assertIn("Leo", res["set_aside"])
        self.assertIn("Sam", res["set_aside"])

    def test_draft_flags_unlabelled_samosas(self):
        draft = os.path.join(HERE, "..", "examples", "party.draft.json")
        code, out, _ = run(["cover", draft])
        self.assertEqual(code, 1)
        self.assertIn("cannot verify Grandma's potato samosas", out)


class Quantities(unittest.TestCase):
    def test_single_dish_plated(self):
        q = rc.qty(base_plan())
        line = q["lines"][0]
        self.assertAlmostEqual(line["need"], 9.2 * 100 * 1.05, places=1)

    def test_split_between_two_dishes(self):
        p = base_plan()
        p["menu"].append({"dish": "Rice", "course": "main", "per_person": 100, "contains": []})
        q = rc.qty(p)
        self.assertAlmostEqual(q["lines"][0]["need"], 9.2 * 60 * 1.05, places=1)

    def test_restricted_guest_puts_full_portion_on_safe_dish(self):
        p = base_plan()
        p["guests"] = [{"name": "gf", "rsvp": "yes", "diet": ["gluten-free"]}]
        p["show_rate"] = {"yes": 1.0}
        p["menu"].append({"dish": "Rice", "course": "main", "per_person": 100, "contains": []})
        q = {l["dish"]: l for l in rc.qty(p)["lines"]}
        self.assertEqual(q["Pasta"]["need"], 0)
        self.assertAlmostEqual(q["Rice"]["need"], 105.0)

    def test_pack_rounding_and_yield(self):
        p = base_plan()
        p["show_rate"] = {"yes": 1.0}
        p["menu"][0].update({"pack": 500, "yield": 0.7})
        line = rc.qty(p)["lines"][0]
        # need 1050 on the plate -> 1500 bought -> 3 packs
        self.assertEqual(line["packs"], 3)
        self.assertEqual(line["buy"], 1500)

    def test_each_dish_ignores_split_and_age(self):
        p = base_plan()
        p["show_rate"] = {"yes": 1.0}
        p["guests"] = [{"name": "kid", "rsvp": "yes", "age": "child"}]
        p["menu"] = [{"dish": "Cake", "course": "dessert", "per_person": 1, "each": True, "contains": []},
                     {"dish": "Fruit", "course": "dessert", "per_person": 100, "contains": []}]
        q = {l["dish"]: l for l in rc.qty(p)["lines"]}
        self.assertAlmostEqual(q["Cake"]["need"], 1.1)
        self.assertAlmostEqual(q["Fruit"]["need"], 52.5, places=1)

    def test_instead_of_only_for_those_who_cannot_eat_original(self):
        q = {l["dish"]: l for l in rc.qty(json.load(open(EXAMPLE)))["lines"]}
        # only Nina (child, gluten-free) takes a cupcake
        self.assertAlmostEqual(q["Gluten-free cupcakes"]["need"], round(0.92 * 1.15, 1))

    def test_reserve_sized_to_gap(self):
        q = rc.qty(json.load(open(EXAMPLE)))
        crisps = [l for l in q["lines"] if l["course"] == "reserve"][0]
        gap = q["heads"]["eaters"]["high"] - q["heads"]["eaters"]["expected"]
        self.assertAlmostEqual(crisps["need"], round(gap * 30, 1))

    def test_short_at_high_without_reserve_exits_1(self):
        p = base_plan(service="buffet")
        code, out, _ = run(["qty", write(p)])
        self.assertEqual(code, 1)
        self.assertIn("short", out)

    def test_hot_venue_more_ice(self):
        a = rc.qty(base_plan())["supplies"]["ice_kg"]
        b = rc.qty(base_plan(hot_venue=True))["supplies"]["ice_kg"]
        self.assertGreater(b, a)


class Money(unittest.TestCase):
    def test_even_split_adds_up(self):
        parts = rc.even_split(100.0, 3)
        self.assertEqual(parts, [33.34, 33.33, 33.33])
        self.assertAlmostEqual(sum(parts), 100.0)

    def test_split_zero_payers(self):
        with self.assertRaises(rc.PlanError):
            rc.even_split(10, 0)

    def test_verdicts(self):
        p = base_plan()
        p["menu"][0].update({"pack": 1000, "pack_price": 50})
        p["event"]["budget_total"] = 40
        self.assertEqual(rc.budget(p)["verdict"], "OVER")
        p["event"]["budget_total"] = 52
        self.assertEqual(rc.budget(p)["verdict"], "TIGHT")
        p["event"]["budget_total"] = 500
        self.assertEqual(rc.budget(p)["verdict"], "UNDER")

    def test_over_budget_exit_code(self):
        p = base_plan()
        p["menu"][0].update({"pack": 1000, "pack_price": 50})
        p["event"]["budget_total"] = 10
        self.assertEqual(run(["budget", write(p)])[0], 1)


class Clock(unittest.TestCase):
    def test_two_hour_limit_indoors(self):
        c = rc.clock(base_plan(hours=3))
        row = c["rows"][0]
        self.assertEqual(row["batches"], 2)
        self.assertEqual(row["swaps"], ["14:00"])
        self.assertEqual(row["off_by"], "16:00")

    def test_hot_venue_halves_window(self):
        c = rc.clock(base_plan(hours=2, hot_venue=True))
        self.assertEqual(c["limit_min"], 60)
        self.assertEqual(c["rows"][0]["batches"], 2)

    def test_shelf_and_held_items_skip_limit(self):
        p = base_plan(hours=5)
        p["menu"].append({"dish": "Crisps", "hold": "shelf", "per_person": 1, "contains": []})
        p["menu"][0]["held"] = True
        rows = rc.clock(p)["rows"]
        self.assertTrue(all(r["off_by"] is None for r in rows))

    def test_out_at_respected(self):
        p = base_plan(hours=3)
        p["menu"][0]["out_at"] = "14:30"
        self.assertEqual(rc.clock(p)["rows"][0]["batches"], 1)


class After(unittest.TestCase):
    def test_tally_example(self):
        ex = os.path.join(HERE, "..", "examples")
        res = rc.tally(json.load(open(os.path.join(ex, "party.json"))),
                       json.load(open(os.path.join(ex, "result.json"))))
        by = {d["dish"]: d for d in res["dishes"]}
        self.assertEqual(by["Chicken skewers"]["status"], "RAN OUT")
        self.assertEqual(by["Cheese & veg wraps"]["status"], "TOO MUCH")
        self.assertIn("pack rounding", by["Corn cups"]["note"])
        self.assertIn("crowd_appetite", res)
        self.assertAlmostEqual(res["turnout_vs_prediction"], 1.01)


class Lint(unittest.TestCase):
    def test_example_clean(self):
        self.assertEqual(rc.lint(json.load(open(EXAMPLE))), [])

    def test_catches_problems(self):
        p = base_plan()
        p["menu"].append({"dish": "Pasta", "per_person": 1, "contains": ["nutz"]})
        p["menu"].append({"dish": "Alt", "per_person": 1, "contains": [], "instead_of": "Ghost"})
        issues = " | ".join(rc.lint(p))
        self.assertIn("duplicate", issues)
        self.assertIn("nutz", issues)
        self.assertIn("Ghost", issues)

    def test_bad_file_exit_2(self):
        self.assertEqual(run(["heads", "/nonexistent.json"])[0], 2)


if __name__ == "__main__":
    unittest.main()
