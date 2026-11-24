import pytest

from engine.character import Character

# 标准数组：力15 敏14 体13 智12 感10 魅8 → 调整值 +2 +2 +1 +1 +0 -1
STATS = {"STR": 15, "DEX": 14, "CON": 13, "INT": 12, "WIS": 10, "CHA": 8}


def make(job="战士", background="士兵"):
    return Character("测试", "人类", job, background, STATS)


# ---- 1. 出过 bug 的地方 ----

def test_unknown_job_rejected():
    # bad case 3：以前会静默降级成 d8
    with pytest.raises(ValueError, match="血猎手"):
        make(job="血猎手")


def test_unknown_background_rejected():
    with pytest.raises(ValueError, match="海盗"):
        make(background="海盗")


def test_valid_character_builds():
    # 11-22 写成 BACKGROUND_STATS.background 时，正常建卡就会崩
    hero = make()
    assert hero.allowed_stats == ["STR", "DEX", "CON"]
    assert hero.hp == hero.max_hp


@pytest.mark.xfail(strict=True, reason="bad case 1：加值失败只 return 错误字符串，不抛异常")
def test_illegal_background_bonus_raises():
    # 士兵只能加 STR/DEX/CON，CHA 不合法
    with pytest.raises(ValueError):
        make().apply_background_bonus("A", "CHA", "STR")


# ---- 2. 规则计算 ----

@pytest.mark.parametrize(
    "value, expected",
    [(10, 0), (11, 0), (15, 2), (20, 5), (8, -1), (9, -1), (1, -5)],
)
def test_modifier(value, expected):
    # 调整值 = (属性 - 10) / 2 向下取整；9 → -1 是边界（截断取整会错算成 0）
    assert make().get_modifier(value) == expected


@pytest.mark.parametrize("job, expected", [("野蛮人", 13), ("战士", 11), ("法师", 7)])
def test_max_hp(job, expected):
    # 1 级 HP = 生命骰最大值 + 体质调整值(+1)
    assert make(job=job).max_hp == expected


def test_background_bonus_plan_a():
    hero = make()
    hero.apply_background_bonus("A", "STR", "DEX")
    assert hero.stats["STR"] == 17
    assert hero.stats["DEX"] == 15


# ---- 3. 走另一条代码路径的特殊情况 ----

def test_caster_spell_numbers():
    # 法师用智力(12 → +1)，熟练 +2：DC = 8 + 2 + 1，攻击 = 2 + 1
    hero = make(job="法师")
    assert hero.spell_save_dc == 11
    assert hero.spell_attack_bonus == 3


def test_non_caster_has_no_spell_numbers():
    # 战士不在 SPELLCASTING_ABILITY 里，.get 返回 None → 0
    hero = make(job="战士")
    assert hero.spell_save_dc == 0
    assert hero.spell_attack_bonus == 0
