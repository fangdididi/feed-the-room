---
name: feed-the-room
description: Work out how much food and drink a gathering really needs, and make sure everyone has something safe to eat. Turns an RSVP list into a realistic head count with a low/expected/high range, maps every guest's diet and allergies against the menu (unlabelled dishes count as unsafe), sizes each dish by service style with pack rounding and a cheap reserve for the high count, checks the budget, schedules when each platter goes out and comes off the table, and after the party turns leftovers into calibration for next time. Use for birthday parties, team lunches, family dinners, potlucks, picnics, meetups, club nights and any "how much should I order / cook for N people" question. It plans; it never places orders or pays.
---

# feed-the-room

**Plan for the people who will actually come, give every guest a safe plate, and put food on the table only for as long as it stays safe.**

## What this skill is

Feeding a group goes wrong in a few predictable ways. People order for the invite list and
throw a third of it away. They order for the people who said yes and run out when the
plus-ones arrive. The one vegan guest finds a single bowl of fruit. A child with a peanut
allergy picks up a spring roll whose dipping sauce "might contain nuts". The cake sits in the
sun for three hours. And next year the host starts from zero again, because nobody wrote down
what was left.

`feed-the-room` turns that into a short, checkable plan:

1. a **party card** with the facts that change the numbers (service style, length, heat, budget);
2. a **head count** with a range, using show-up rates for this kind of gathering instead of the RSVP total;
3. a **safe-plate map**: for every guest with a diet or allergy, which dishes they can and cannot eat, and why;
4. **quantities** per dish, sized by who controls the portion, rounded up to real pack sizes,
   with a cheap shelf-stable reserve that covers the high count;
5. a **budget check** with a cap verdict and a trimming order that never cuts safety;
6. a **table clock**: when each dish goes out, when a fresh platter replaces it, and when it must be off the table;
7. a **feast sheet** (one page the host can print) and, afterwards, a **tally** that turns leftovers into better numbers next time.

The helper `scripts/roomcalc.py` (Python 3, standard library only) does the arithmetic from one
plan file, so the numbers are repeatable and easy to change.

### What it will not do

- It does not place orders, book tables or pay anyone. It produces the list; the host orders.
- It does not decide that a dish is safe for an allergy from its name or a photo. If the
  ingredients are not known, the dish is **UNKNOWN**, which is treated as unsafe for anyone
  with a restriction until someone who made or sold it confirms.
- It is not medical advice. Severe allergies are confirmed with the guest or their guardian.

## When to use

- "How much pizza / how many sandwiches / how much meat for 25 people?"
- Planning a birthday, team lunch, farewell, family dinner, picnic, potluck, meetup or game night.
- Several guests with different diets or allergies and one shared menu.
- Free events where many people RSVP and fewer show up.
- Outdoor or hot-weather gatherings where food sits out.
- After a party, to learn from what ran out and what was thrown away.

Not for: restaurant menu engineering, nutrition targets for one person, or professional
catering under a food licence (follow your local food code there; this skill's rules are the
home and small-group version).

## Files

```
SKILL.md                 this guide (Chinese: SKILL.zh-CN.md)
scripts/roomcalc.py      heads / cover / qty / budget / clock / tally / lint
references/portions.md   per-person amounts, split rule, yields, drinks and supplies
references/headcount.md  show-up rates by kind of gathering, how to calibrate
references/safe-plates.md diets, allergen flags, labels, set-aside plates, holding times
examples/                a worked birthday picnic: draft, fixed plan, results, tally
```

## Step by step

### Step 1 - Party card

Ask only what changes the numbers. Ten questions at most, all at once:

| Ask | Why it matters |
|---|---|
| What is the occasion and who is coming (adults, teens, children, toddlers)? | Children eat about half; teens eat more. |
| Date, serving time and how long people stay | Length drives drinks, appetizer counts and the table clock. |
| Is it at a mealtime, or between meals? | A 12:30 lunch needs a meal; 15:00 needs snacks and cake. |
| Service style: plated, boxed, family-style, buffet, grazing? | Who controls the portion sets the buffer (5% to 18%). |
| Indoors or out, and how hot? Above 32 C / 90 F? | Halves how long perishable food may sit out. |
| Budget cap, currency, and who pays? | Verdict, trimming order, even split. |
| What is cooked, bought, delivered or brought by guests? | Pack sizes, prices, who owns the ingredient list. |
| Fridge, oven, cooler, chafing dishes, ice? | Whether hot/cold holding is possible at all. |
| How did people reply (form, chat, word of mouth)? Free or paid? | Picks the show-up rates. |
| Any numbers from a similar past event? | Your own history beats any default. |

Write the answers into the `event` block of a plan file (see `examples/party.json`). Use the
fields `kind` (`close`, `work`, `paid`, `free`), `service`, `hours`, `serve_at`, `hot_venue`,
`walk_ins`, `currency`, `budget_total`, `other_costs`, `must_cover`.

### Step 2 - Head count with a range

List guests with `rsvp` (`yes`, `maybe`, `no`, `none`), `age`, `plus` (extra people in the same
party) and optionally `appetite` (1.0 = normal). Then:

```bash
python3 scripts/roomcalc.py heads party.json
```

You get people and "eaters" (adult-equivalents) at low, expected and high. Defaults for the
share of "yes" replies who come: close friends and family 0.92, work 0.90, paid 0.85, free
0.70, free with fewer than 50 invited 0.63; "maybe" 0.35; no reply 0.10 to 0.30. Low and high
are 10 points either side. If the host has real numbers from a similar event, put them in
`show_rate` and say so in the plan.

The rule that follows: **perishable food is sized to the expected count; the gap up to the
high count is covered by a cheap, shelf-stable reserve** (crisps, bread, crackers, a frozen
pizza) that is fine to keep if nobody needs it.

### Step 3 - Safe-plate map

For each guest, record restrictions in two separate fields:

- `diet`: `vegetarian`, `vegan`, `pescatarian`, `halal`, `no-pork`, `no-beef`, `gluten-free`,
  `dairy-free`, `no-alcohol`. A diet rules out dishes that **contain** the flag.
- `allergy`: one or more flags (`peanut`, `treenut`, `sesame`, `shellfish`, `egg`, `dairy`, ...).
  An allergy also rules out dishes that **may contain** it, and it puts the guest on the
  set-aside list.

For each dish, record `contains` and `may_contain` from the recipe, the package or the
seller. A dish with no `contains` list is UNKNOWN to anyone restricted. Then:

```bash
python3 scripts/roomcalc.py cover party.json
```

Read the output as a host would:

- every restricted guest must have at least one safe dish in each course listed in
  `must_cover` (default: `main`); if not, the command exits 1 and lists who is missing out;
- "only one safe choice" means that one dish is the guest's whole meal: set a labelled plate
  aside **before** the table opens;
- "SET ASIDE" lists everyone with an allergy or a single safe choice.

Fix gaps by adding or changing a dish, not by telling the guest to "eat around it". When a
dish exists only as an alternative (gluten-free cupcakes for those who cannot have the cake),
give it `"instead_of": "Birthday cake"` so it is sized for those guests only.

For severe allergies, ask the guest or guardian directly: exactly which foods, whether traces
matter, and whether they carry their own medicine. Never fill this in from a guess.

### Step 4 - Shape the menu

- Match the service style and the time of day (see `references/portions.md`).
- Aim for one safe main for every restriction group, ideally a dish everyone wants anyway
  (a good vegan main gets eaten by everyone - the helper already counts that).
- Prefer more variety over bigger piles of one thing; people take a little of several.
- Mark "one each" items (cake, favours, a boxed lunch) with `"each": true`. They are counted one
  per person regardless of age or how many other choices exist.
- Write `per_person` as the amount one adult would take **if it were the only dish in that
  course**. The helper scales it down when there are several: 2 dishes 60% each, 3 dishes 45%
  each, 4 or more 35% each.
- For food that loses weight to bone, peel, rind or cooking, set `yield` (usable share).
- Use the seller's real `pack` size and `pack_price`, or `unit_price` for things made at home.

### Step 5 - Quantities

```bash
python3 scripts/roomcalc.py qty party.json
```

For each dish: need on the plate (with the service buffer), packs to buy, and whether it would
run short if the high count turns up. Buffers: plated or boxed 5%, family-style 10%, buffet 15%,
grazing 18%. Supplies follow: drink servings (2 in the first hour, 1 per hour after, more in
heat), ice, plates, cups and napkins.

If dishes run short at the high count and the menu has no `reserve` item, the command exits 1:
add one, or accept the risk in writing.

### Step 6 - Money

```bash
python3 scripts/roomcalc.py budget party.json --split 3
```

Total, cost per expected guest, and a verdict against the cap: `UNDER`, `TIGHT` (over 90%),
`OVER` (exit 1). The three biggest lines are listed because that is where savings are.

When over budget, trim in this order and show the new numbers after each step:

1. drop a fourth or fifth dish in the same course (the others absorb its share);
2. swap the most expensive line for a cheaper dish in the same course;
3. change pack sizes or sellers;
4. move from buffet to plated or boxed (smaller buffer);
5. shorten the event or move it off a mealtime.

Never trim a guest's only safe dish, the ice, the cooler, or the thermometer.

`--split N` divides the total into N shares that add back to the cent. If the group shares
costs some other way (by family, by what each ordered), say so and do it by hand.

### Step 7 - Table clock

```bash
python3 scripts/roomcalc.py clock party.json
```

Perishable dishes (`hold`: `hot`, `cold` or `ambient`) may sit at room temperature for 2 hours,
or 1 hour when it is above 32 C / 90 F. For a longer party the helper splits each dish into
small platters and gives swap times; each platter comes off the table by its time. Mark a dish
`"held": true` only if it really stays hot (60 C / 140 F or more) or cold (4 C / 40 F or less)
on equipment, and check it with a thermometer. Use `out_at` for things served later (cake).

Also back-schedule the run-up: when each order must be placed (ask the seller; cakes and
platters often need one to three days), pick-up or delivery times, and fridge space the night
before.

### Step 8 - Feast sheet

Hand the host one page (see `examples/feast-sheet.md`):

1. headline: expected people (range), eaters, budget verdict, per head;
2. order and shopping list grouped by seller, with packs and the order-by time;
3. safe-plate map and the set-aside list, with names;
4. dish labels: name, contains, may contain, suitable for;
5. table clock with who swaps platters;
6. who brings what (for potlucks, assign by course so `must_cover` still holds);
7. leftovers: containers ready, what goes home with whom, the off-by times.

### Step 9 - After the party

Within a day, write `result.json`: how many people came, and for each dish the share left
(0, 0.25, 0.5 ...) and, if it ran out, roughly when. Then:

```bash
python3 scripts/roomcalc.py tally party.json --result result.json
```

You get turnout against the prediction, a status per dish (`RAN OUT`, `ABOUT RIGHT`,
`TOO MUCH`), a note when leftovers were only pack rounding, and `crowd_appetite`: how much this
crowd ate compared with the table defaults. Save the numbers with the plan; next time put the
real show-up rate in `show_rate` and scale `per_person` by the appetite for dishes that ran out.

`lint` checks a plan file for missing fields, unknown flags, duplicates and broken `instead_of`
links. Run it whenever the file changes.

## Example

> "Mia turns 8. Picnic in the park, Saturday 15:00 to 18:00, forecast 34 C. 21 names on the
> list, budget 1,100 yuan. One boy has a peanut allergy, a mum and daughter eat halal, one girl
> is gluten-free, one dad is vegan, one is vegetarian. Grandma is making samosas."

- `heads`: 19 yes, 3 maybe, 1 no reply, 1 no -> about 21 people (range 16.5 to 22.8),
  16 adult-equivalent eaters.
- `cover` on the draft fails: grandma's samosas have no ingredient list, so six restricted
  guests "cannot verify" them. After asking her (wheat pastry, mustard seeds, no nuts) it
  passes, and lists Leo (peanut allergy) and Sam (vegan, fruit is his only dessert) for
  set-aside plates. The rice-paper rolls are off Leo's list because the sauce may contain peanut.
- `qty`: 20 skewers, 24 sausage rolls, 2 x 12 wraps, 3 x 10 rice-paper rolls, 20 samosas,
  24 corn cups, 4 kg of watermelon and grapes (60% usable), one 24-slice cake, one box of 6
  gluten-free cupcakes for Nina, one bag of crisps as reserve; 105 drink servings, 16 kg ice.
- `budget`: 787 yuan, 37.78 per head, `UNDER` the cap.
- `clock`: it is above 32 C, so every perishable dish goes out in three small platters at
  15:00, 16:00 and 17:00; cake and cupcakes come out at 16:30 and are off by 18:30.
- After: skewers ran out at 16:20 and samosas at 16:45; wraps and fruit were 30-35% left;
  crowd appetite 1.13. Next year: more skewers, smaller fruit order, one fewer pack of wraps.

The full files are in `examples/`.

Smaller asks get a smaller answer. "Boxed lunch for a 12-person team meeting, two vegetarians,
one no-pork": `kind: work`, `service: boxed`, one box each (`each: true`) with a vegetarian
`instead_of` box; quantities in one table and an order-by time.

## Tips

- Say which numbers are defaults and which are the host's own. Defaults are starting points.
- Count children separately; a "family of four" is not four adults.
- For free events, send a reminder a day or two before; it is the cheapest way to shrink no-shows.
- Labels on the table do more for allergy safety than anything said out loud. Put serving
  spoons per dish and set the allergy-safe dishes at the start of the line, before cross-contact.
- Do not top up a half-empty platter with fresh food; replace it.
- Leftovers: shallow containers into the fridge before the off-by time; anything past it goes in the bin.
- Potlucks: ask each cook for the ingredient list when they sign up, not at the door.
- Keep the plan file. The second party is far easier than the first.
