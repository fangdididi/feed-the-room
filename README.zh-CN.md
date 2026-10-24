# feed-the-room（喂饱一屋子人）

[English](README.md) | **简体中文**

> 一场聚会到底需要多少吃的？每位客人是不是都有能放心吃的东西？这个智能体技能把报名名单换算成真实人数，逐一核对每位客人的饮食习惯和过敏原，把每道菜的量算到真实包装规格，核对预算，排好上桌时间，并从剩菜里学习。

## 这是什么

`feed-the-room` 是一个给“要喂饱一群人”的人用的智能体技能：生日会、团队午餐、家庭聚餐、百家宴、野餐、线下聚会。你问“25 个人该订多少？”，智能体不会随口报一个数。它只问几个真正会改变答案的问题，写一个计划文件，再用一个只依赖标准库的小脚本做计算，每次算法都一样、结果可复算。

### 解决什么问题

给一群人准备吃的，总是在同样几个地方出错：

- 按邀请名单订餐，最后倒掉三分之一；
- 按“确认参加”订餐，家属一来就不够；
- 唯一的纯素客人，只有一碗水果；
- “可能含坚果”的蘸酱，摆在花生过敏的孩子旁边；
- 蛋糕在太阳下放了三个小时；
- 到了明年又从零开始，因为没人记下当时剩了多少。

feed-the-room 把这些都变成可以检查的一步。

## 功能

- **聚会卡**：最多十个问题，每一个都会影响数字——谁来、待多久、是不是饭点、上菜方式、天气、预算、设备、大家怎么回复的。
- **带区间的人数**：按聚会类型（亲友、工作、付费、免费、小型免费）给出到场率，算上“可能”和没回复的人、家属、儿童与青少年的食量权重、临时来的人。给出低 / 预期 / 高三档，任何默认值都可以用你自己的历史数据覆盖。
- **安全餐盘图**：饮食习惯排除菜里“含有”的成分；过敏还要排除“可能含有”的成分。没有配料表的菜标为 UNKNOWN，绝不默认安全。每位客人都必须有一道安全的主菜（以及你要求的其他餐段）；过敏的客人和只有一个选项的客人，开席前就预留一盘贴好名字的。
- **贴近现实的分量**：选择多时每道菜的人均量自动打折；“每人一份”的东西（蛋糕、盒饭）按人头算；替代菜（`instead_of`）只按需要它的人来算；可食比例覆盖骨头和瓜皮；余量按上菜方式定；全部向上取整到卖家的包装规格。
- **兜底而不浪费**：易腐食物按预期人数准备，便宜耐放的兜底食物覆盖到高人数。
- **预算核对**：总价、人均、UNDER / TIGHT / OVER 结论、花钱最多的三项、精确到分的平摊，以及永不触碰安全项的削减顺序。
- **餐桌时钟**：室温最多 2 小时，超过 32°C（90°F）只有 1 小时。时间长的聚会拆成小盘，给出换盘和撤下时间。
- **宴席单**：可打印的一页纸——按卖家分组的订单、安全餐盘、标签、时钟、分工。
- **聚会复盘**：实际人数与预测之比、每道菜“提前吃完 / 刚好 / 太多”、剩菜只是包装取整时的提示，以及下次用的“食量系数”。
- **带测试的辅助脚本**：`scripts/roomcalc.py`，只用 Python 3 标准库，38 个单元测试。

## 安装

技能就是一个包含 `SKILL.md` 的文件夹。克隆到你的智能体读取技能的位置：

```bash
git clone https://github.com/fangdididi/feed-the-room.git
```

| 智能体 | 放在哪里 |
|---|---|
| **Claude Code** | `~/.claude/skills/feed-the-room/`（个人）或 `.claude/skills/feed-the-room/`（项目内） |
| **Codex CLI** | `~/.codex/skills/feed-the-room/` 或仓库内 `.agents/skills/feed-the-room/`；也可以在 `AGENTS.md` 里引用 `SKILL.md` |
| **Cursor** | `.cursor/skills/feed-the-room/`，或把 `SKILL.md` 设为项目规则 / 在对话中 `@` 引用 |
| **Gemini CLI、Copilot、Kiro、Windsurf 等** | 把文件夹放进仓库，在对应的指令文件（`GEMINI.md`、`.github/copilot-instructions.md` 等）里指向 `feed-the-room/SKILL.md` |
| **支持“项目”的聊天应用** | 把 `SKILL.zh-CN.md`（或 `SKILL.md`）和 `references/` 上传为项目知识 |

示例：

```bash
mkdir -p ~/.claude/skills && git clone https://github.com/fangdididi/feed-the-room.git ~/.claude/skills/feed-the-room
```

环境要求：辅助脚本需要 Python 3.8+（只用标准库）。不需要账号、不需要 API 密钥，不会下单、不会付款。

## 使用

可以这样问你的智能体：

- “下周部门聚餐 30 人自助，有两位素食、一位清真，预算 2000，帮我算算订多少。”
- “儿子生日野餐：15 个孩子加家长，3 个小时，天会很热。要买些什么？”
- “我们办 20 人的百家宴，谁带什么才能保证每个人都有能吃的主菜？”
- “免费线下活动报名了 80 人，要订多少个披萨？”
- “这是周六聚会剩下的东西，下次该怎么调整？”
- "How much food for a team lunch of 30? Buffet, two vegetarians, one coeliac."

辅助脚本命令：

```bash
python3 scripts/roomcalc.py lint   party.json            # 有问题时退出码 1
python3 scripts/roomcalc.py heads  party.json            # 人数与食量当量，低/预期/高
python3 scripts/roomcalc.py cover  party.json            # 有人没有安全餐盘时退出码 1
python3 scripts/roomcalc.py qty    party.json            # 高人数会不够且无兜底时退出码 1
python3 scripts/roomcalc.py budget party.json --split 3  # 超预算时退出码 1
python3 scripts/roomcalc.py clock  party.json
python3 scripts/roomcalc.py tally  party.json --result result.json
python3 scripts/roomcalc.py --help                       # heads、cover、qty、budget、clock 支持 --json
python3 -m unittest discover -s tests                    # 38 个测试
```

## 示例

一场孩子的生日野餐：15:00–18:00，34°C，名单上 21 个名字，预算 1100 元；一人花生过敏、两人清真、一人无麸质、一人纯素、一人素食，外婆还会做咖喱角。

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

外婆确认配料之后：

```text
$ python3 scripts/roomcalc.py cover examples/party.json
Leo [ALLERGY] main: Chicken skewers, Mini sausage rolls, Cheese & veg wraps, Grandma's potato samosas; ...
    x Rice-paper rolls (allergy: may contain peanut)
Sam [diet] main: Rice-paper rolls, Grandma's potato samosas; side: Corn cups; dessert: Watermelon & grapes
    ! only one safe choice in 'dessert'
SET ASIDE a labelled plate before service for: Leo, Sam
OK: every guest has a safe plate

$ python3 scripts/roomcalc.py budget examples/party.json --split 3
total ¥787.00  per head ¥37.78  cap 1100  verdict UNDER
even split: ¥262.34 / ¥262.33 / ¥262.33
```

结论：花生过敏的 Leo 不能吃越南春卷（蘸酱可能含花生），纯素的 Sam 甜点只有水果，两人都要提前预留餐盘；34°C 下所有易腐菜分三小盘，15:00、16:00、17:00 各上一盘；总价 787 元，人均 37.78 元，在预算内。完整的一页计划见 [`examples/feast-sheet.md`](examples/feast-sheet.md)，聚会后的复盘见 [`examples/after-party.md`](examples/after-party.md)。

## 工作流程

1. **聚会卡** → `party.json` 的 `event` 部分。
2. **人数** → 带区间的预期到场；易腐食物按预期，兜底按高人数。
3. **安全餐盘** → 每位有限制的客人对照每道菜；通过改菜单补缺口。
4. **定菜单** → 品种、每个限制群体一道安全主菜、`each` 与 `instead_of`。
5. **分量** → 分摊规则、可食比例、余量、包装取整、耗材。
6. **预算** → 结论、最大开销项、不碰安全的削减顺序、平摊。
7. **时钟** → 小盘、换盘时间、撤下时间、倒排下单截止时间。
8. **宴席单** → 给主人的一页纸。
9. **复盘** → 校准数据留给下一次。

## 文件结构

```
feed-the-room/
├── SKILL.md                    # 技能（英文）
├── SKILL.zh-CN.md              # 技能（中文）
├── README.md / README.zh-CN.md
├── LICENSE
├── scripts/
│   └── roomcalc.py             # heads / cover / qty / budget / clock / tally / lint
├── references/
│   ├── portions.md             # 人均分量、分摊规则、可食比例、耗材
│   ├── headcount.md            # 到场率与校准
│   └── safe-plates.md          # 饮食习惯、过敏原标记、标签、摆放时限
├── examples/
│   ├── party.draft.json        # 初稿：一道菜没有配料表
│   ├── party.json              # 修正后的计划
│   ├── result.json             # 实际情况
│   ├── tally.output.json       # 脚本输出
│   ├── feast-sheet.md          # 一页宴席单
│   └── after-party.md          # 下次的改进
└── tests/
    └── test_roomcalc.py        # 38 个单元测试
```

## 局限

- 分量和到场率是规划用的默认值，不是预测。请用你自己的数据替换。
- 过敏安全取决于真实的配料表。技能拒绝猜测，也无法检查厨房里的交叉污染。
- 食品安全规则是家庭和小团体版本。持证餐饮请遵守当地食品法规。
- 它只做规划和计算，从不下单、不付款。

## 许可证

MIT，见 [LICENSE](LICENSE)。
