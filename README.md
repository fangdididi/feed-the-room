# feed-the-room

**English** | [简体中文](README.zh-CN.md)

> How much food does a gathering really need, and does every guest have something safe to eat? An agent skill that turns an RSVP list into a realistic head count, checks each guest's diet and allergies against the menu, sizes every dish to real pack sizes, checks the budget, schedules the table, and learns from the leftovers.

## What it is

`feed-the-room` is an agent skill for anyone feeding a group: a birthday party, a team lunch,
a family dinner, a potluck, a picnic, a meetup. Ask "how much should I order for 25 people?" and
the agent does not guess a number. It asks a few questions that actually change the answer,
writes one plan file, and runs a small standard-library helper that does the arithmetic the
same way every time.

### The problem

Group food goes wrong in the same few ways:

- ordering for the invite list, then throwing a third away;
- ordering for the "yes" replies, then running short when the plus-ones arrive;
- one vegan guest, one bowl of fruit;
- a "may contain nuts" sauce on the table next to a child with a peanut allergy;
- a cake left in the sun for three hours;
- next year, starting from zero again because nobody wrote down what was left.

feed-the-room turns each of those into a check.

## Features

- **Party card.** At most ten questions, all of them ones that move the numbers: who, how long,
  mealtime or not, service style, heat, budget, equipment, how people replied.
- **Head count with a range.** Show-up rates by kind of gathering (family, work, paid, free,
  small free), maybes and silent invitees, plus-ones, children and teens weighted, walk-ins.
  Low / expected / high, and your own history overrides every default.
- **Safe-plate map.** Diets rule out what a dish contains; allergies also rule out what it may
  contain. A dish without an ingredient list is UNKNOWN, never assumed safe. Every guest must
  have a safe main (and any other course you require); guests with an allergy or a single
  choice get a labelled plate set aside before service.
- **Quantities that match reality.** Per-person amounts scale down when people have several
  choices, "one each" items (cake, boxed lunches) are counted per person, alternatives
  (`instead_of`) are sized only for those who need them, yields cover bone and rind, buffers
  follow the service style, and everything rounds up to the seller's pack size.
- **Reserve, not waste.** Perishables are sized to the expected count; a cheap shelf-stable
  reserve covers the gap to the high count.
- **Budget check.** Total, per head, UNDER / TIGHT / OVER, the three biggest lines, an even split
  that adds up to the cent, and a trimming order that never touches safety.
- **Table clock.** 2 hours at room temperature, 1 hour above 32 C / 90 F. Longer parties get
  small platters with swap times and off-the-table times.
- **Feast sheet.** One printable page: orders by seller, safe plates, labels, clock, who does what.
- **After-party tally.** Turnout against prediction, ran-out / about-right / too-much per dish,
  a note when leftovers were only pack rounding, and a crowd-appetite factor for next time.
- **Helper with tests.** `scripts/roomcalc.py`, Python 3 standard library only, 38 unit tests.

## Install

The skill is a folder with `SKILL.md`. Clone it where your agent looks for skills:

```bash
git clone https://github.com/fangdididi/feed-the-room.git
```

| Agent | Where to put it |
|---|---|
| **Claude Code** | `~/.claude/skills/feed-the-room/` (personal) or `.claude/skills/feed-the-room/` (per project) |
| **Codex CLI** | `~/.codex/skills/feed-the-room/` or `.agents/skills/feed-the-room/` in the repo; or reference `SKILL.md` from `AGENTS.md` |
| **Cursor** | `.cursor/skills/feed-the-room/`, or add `SKILL.md` as a project rule / `@`-mention it in chat |
| **Gemini CLI, Copilot, Kiro, Windsurf, others** | Put the folder in the repo and point the agent's instruction file (`GEMINI.md`, `.github/copilot-instructions.md`, etc.) at `feed-the-room/SKILL.md` |
| **Chat apps with Projects** | Upload `SKILL.md` (and the `references/` files) as project knowledge |

Example:

```bash
mkdir -p ~/.claude/skills && git clone https://github.com/fangdididi/feed-the-room.git ~/.claude/skills/feed-the-room
```

Requirements: Python 3.8+ for the helper (standard library only). No accounts, no API keys,
nothing is ordered or paid.

## Usage

Ask your agent things like:

- "How much food for a team lunch of 30? Buffet, two vegetarians, one coeliac."
- "My son's birthday picnic: 15 kids and their parents, 3 hours, it'll be hot. What do I buy?"
- "We're doing a potluck for 20. Who should bring what so everyone has a main they can eat?"
- "Free meetup, 80 people registered. How many pizzas?"
- "Here's what was left after Saturday. What should we change next time?"
- "下周部门聚餐 30 人自助，有两位素食、一位清真，预算 2000，帮我算算订多少。"

Helper commands:

```bash
python3 scripts/roomcalc.py lint   party.json            # exit 1 on problems
python3 scripts/roomcalc.py heads  party.json            # people and eaters, low/expected/high
python3 scripts/roomcalc.py cover  party.json            # exit 1 if someone has no safe plate
python3 scripts/roomcalc.py qty    party.json            # exit 1 if short at high with no reserve
python3 scripts/roomcalc.py budget party.json --split 3  # exit 1 if over the cap
python3 scripts/roomcalc.py clock  party.json
python3 scripts/roomcalc.py tally  party.json --result result.json
python3 scripts/roomcalc.py --help                       # heads, cover, qty, budget, clock also take --json
python3 -m unittest discover -s tests                    # 38 tests
```

## Example

A child's birthday picnic, 15:00-18:00 at 34 C, 21 names on the list, budget 1,100 yuan, one
peanut allergy, two halal, one gluten-free, one vegan, one vegetarian, and grandma's samosas.

```text
$ python3 scripts/roomcalc.py heads examples/party.json
kind: close  rates: yes 0.92 maybe 0.35 silent 0.30
replies: maybe 3, no 1, silent 1, yes 19
people  low 16.5  expected 20.8  high 22.8
eaters  low 12.2  expected 15.9  high 17.3  (adult = 1)
plan perishables for 16 eaters; reserve covers up to 18

$ python3 scripts/roomcalc.py cover examples/party.draft.json
...
PROBLEMS:
  - Leo: cannot verify Grandma's potato samosas
  ...
```

After grandma confirms the ingredients:

```text
$ python3 scripts/roomcalc.py cover examples/party.json
Leo [ALLERGY] main: Chicken skewers, Mini sausage rolls, Cheese & veg wraps, Grandma's potato samosas; ...
    x Rice-paper rolls (allergy: may contain peanut)
Sam [diet] main: Rice-paper rolls, Grandma's potato samosas; side: Corn cups; dessert: Watermelon & grapes
    ! only one safe choice in 'dessert'
SET ASIDE a labelled plate before service for: Leo, Sam
OK: every guest has a safe plate

$ python3 scripts/roomcalc.py qty examples/party.json
service buffet, buffer 15%, plan for 16 eaters (high 18)
main     Chicken skewers              need     17.4 pcs  buy 1 packs = 20.0
main     Rice-paper rolls             need     20.2 pcs  buy 3 packs = 30.0
dessert  Watermelon & grapes          need   2194.9 g    buy 4 packs = 4000.0 (usable share 60%)
dessert  Birthday cake                need     20.8 slices buy 1 packs = 24.0
dessert  Gluten-free cupcakes         need      1.1 pcs  buy 1 packs = 6.0
reserve  Plain crisps                 need     42.3 g    buy 1 packs = 150.0
...

$ python3 scripts/roomcalc.py budget examples/party.json --split 3
total ¥787.00  per head ¥37.78  cap 1100  verdict UNDER
even split: ¥262.34 / ¥262.33 / ¥262.33

$ python3 scripts/roomcalc.py clock examples/party.json
party 15:00-18:00, room-temperature limit 60 min
Chicken skewers   hot   out 15:00 swap 16:00, 17:00 off by 18:00 ...
Birthday cake     cold  out 16:30 swap 17:30 off by 18:30 ...
```

The finished one-page plan is in [`examples/feast-sheet.md`](examples/feast-sheet.md), and what
the family learned afterwards is in [`examples/after-party.md`](examples/after-party.md).

## How it works

1. **Party card** -> the `event` block of `party.json`.
2. **Heads** -> expected attendance with a range; perishables for expected, reserve for high.
3. **Cover** -> every restricted guest checked against every dish; gaps fixed by changing the menu.
4. **Menu shape** -> variety, one safe main per restriction group, `each` and `instead_of` items.
5. **Qty** -> split rule, yields, service buffer, pack rounding, supplies.
6. **Budget** -> verdict, biggest lines, trimming order that never cuts safety, even split.
7. **Clock** -> platters, swap times, off-by times, run-up order deadlines.
8. **Feast sheet** -> one page for the host.
9. **Tally** -> calibration saved for next time.

## File structure

```
feed-the-room/
├── SKILL.md                    # the skill (English)
├── SKILL.zh-CN.md              # the skill (Chinese)
├── README.md / README.zh-CN.md
├── LICENSE
├── scripts/
│   └── roomcalc.py             # heads / cover / qty / budget / clock / tally / lint
├── references/
│   ├── portions.md             # per-person amounts, split rule, yields, supplies
│   ├── headcount.md            # show-up rates and calibration
│   └── safe-plates.md          # diets, allergen flags, labels, holding times
├── examples/
│   ├── party.draft.json        # first draft: one unlabelled dish
│   ├── party.json              # fixed plan
│   ├── result.json             # what happened
│   ├── tally.output.json       # helper output
│   ├── feast-sheet.md          # the one-page plan
│   └── after-party.md          # lessons for next time
└── tests/
    └── test_roomcalc.py        # 38 unit tests
```

## Limits

- Portion and show-up numbers are planning defaults, not predictions. Replace them with your own.
- Allergy safety depends on true ingredient lists. The skill refuses to guess; it cannot check
  a kitchen for cross-contact.
- The food-safety rules are the home and small-group version. Licensed caterers follow their
  local food code.
- It plans and calculates. It never places orders or makes payments.

## License

MIT, see [LICENSE](LICENSE).
