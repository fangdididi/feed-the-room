# Head count: who actually comes

A reply is a promise; attendance is what you feed. Plan against expected attendance with a range.

## Default show-up rates for "yes"

| Kind (`event.kind`) | Typical gathering | Share of yes who come |
|---|---|---|
| `close` | family, close friends, a party at home | 0.92 |
| `work` | team lunch in working hours | 0.90 |
| `paid` | tickets, deposits, prepaid meals | 0.85 |
| `free` | free community event, 50+ invited | 0.70 |
| `free` (fewer than 50 invited) | small free meetup, workshop | 0.63 |

"Maybe" counts 0.35. No reply counts 0.30 for `close`, 0.20 for `work`, 0.10 otherwise.
Declines count 0. Plus-ones take their host guest's rate.

Low and high are the same rates 10 points down and up. Walk-ins (`event.walk_ins`) are added to
expected and high, and treated as having no restrictions.

## Why free events drop so much

Without money down, a reply costs nothing to break. Small free events lose the most. Two things
help: a reminder one or two days before, and asking people to reply "can't come" if plans
change. A small deposit helps most of all where that is appropriate.

## Calibrating with your own history

After each event, `tally` reports `turnout_vs_prediction`. Over two or three similar events:

- divide the people who came by the yes replies -> your own `show_rate.yes`;
- keep it per kind of event (a birthday is not a team lunch);
- write it into the plan file under `show_rate` and note where it came from.

Your own numbers beat any published average. Defaults are only for the first time.

## Eaters versus people

- Food is sized on **eaters** (adult = 1, teen 1.2, child 0.5, toddler 0, times `appetite`).
- Drinks, plates, cups and cost per head use **people**.
- "One each" items use people (a child gets a full slice of cake).
