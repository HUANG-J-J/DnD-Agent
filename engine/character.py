


BACKGROUND_STATS = {
    "侍僧": ["INT", "WIS", "CHA"],
    "工匠": ["STR", "DEX", "INT"],
    "骗子": ["DEX", "CON", "CHA"],
    "罪犯": ["DEX", "CON", "INT"],
    "艺人": ["STR", "DEX", "CHA"],
    "农民": ["STR", "CON", "WIS"],
    "警卫": ["STR", "INT", "WIS"],
    "向导": ["DEX", "CON", "WIS"],
    "隐士": ["CON", "WIS", "CHA"],
    "商人": ["CON", "INT", "CHA"],
    "贵族": ["STR", "INT", "CHA"],
    "贤者": ["CON", "INT", "WIS"],
    "水手": ["STR", "DEX", "WIS"],
    "抄写员": ["DEX", "INT", "WIS"], 
    "士兵": ["STR", "DEX", "CON"],
    "旅人": ["DEX", "CON", "WIS"] 
}

CLASS_HIT_DICE = {
    "野蛮人": 12, "战士": 10, "圣武士": 10, "游侠": 10,
    "吟游诗人": 8, "牧师": 8, "德鲁伊": 8, "武僧": 8, "盗贼": 8, "邪术师": 8,
    "法师": 6, "术士": 6
}

SPELLCASTING_ABILITY = {
    "法师": "INT", "奇械师": "INT",
    "牧师": "WIS", "德鲁伊": "WIS", "游侠": "WIS",
    "吟游诗人": "CHA", "圣武士": "CHA", "术士": "CHA", "邪术师": "CHA"
}



class Character:
    def __init__(self, name: str, species: str, job: str, background: str, base_stats: dict):
        
        if job not in CLASS_HIT_DICE:
            raise ValueError(f"{job}不在可选范围内，请从以下职业中选择：{list(CLASS_HIT_DICE)}") 
        if background not in BACKGROUND_STATS:
            raise ValueError(f"{background}不在可选范围内，请从以下背景中选择：{list(BACKGROUND_STATS)}")
        self.name = name
        self.species = species
        self.job = job
        self.background = background
        
        # 用字典管理 6 大基础属性（力量、敏捷、体质、智力、感知、魅力）
        # 先填入基础值
        self.stats = base_stats.copy()

        self.allowed_stats = BACKGROUND_STATS[background]
          
        self.inventory = []   
        
        self.hp = self.max_hp 

        self.level = 1   # 初始等级
        self.skills = [] # 如果里面有“察觉”，被动感知就有熟练加值
    
    # 1. 设置属性的方法
    def set_stats(self, str_val, dex_val, con_val, int_val, wis_val, cha_val):
        self.stats["STR"] = str_val
        self.stats["DEX"] = dex_val
        self.stats["CON"] = con_val
        self.stats["INT"] = int_val
        self.stats["WIS"] = wis_val
        self.stats["CHA"] = cha_val

    # 2. 规则书里的“调整值”公式：(属性-10) / 2 (向下取整)
    def get_modifier(self, stat_value: int) -> int:
        return (stat_value - 10) // 2

    # 3. 加技能
    def add_skill(self, skill_name: str):
        self.skills.append(skill_name)

    # 4. 按照背景加点
    # 规则：背景的三项属性中一项 +2、另一项 +1，或三项各 +1
    def apply_background_bonus(self, bonuses: dict) -> str:
        for stat in bonuses:
            if stat not in self.allowed_stats:
                raise ValueError(f"{stat} 不在背景「{self.background}」的可选属性内，可选：{self.allowed_stats}")

        if sorted(bonuses.values()) not in ([1, 2], [1, 1, 1]):
            raise ValueError(f"加值组合不合法：{bonuses}。只能是一项 +2 另一项 +1，或三项各 +1")

        for stat, value in bonuses.items():
            self.stats[stat] = min(20, self.stats[stat] + value)
        return "，".join(f"{stat} +{value}" for stat, value in bonuses.items())

    # 动态计算最大生命值
    @property
    def max_hp(self) -> int:
        con_mod = self.get_modifier(self.stats["CON"])
        hit_die = CLASS_HIT_DICE[self.job]
        return hit_die + con_mod

    # 动态计算护甲等级
    @property
    def ac(self) -> int:
        dex_mod = self.get_modifier(self.stats["DEX"])
        return 10 + dex_mod

    # 动态计算先攻
    @property
    def initiative(self) -> int:
        return self.get_modifier(self.stats["DEX"])

    # 动态计算熟练加值
    @property
    def proficiency_bonus(self) -> int:
        return 1 + (self.level + 3) // 4

    # 动态计算被动感知
    @property
    def passive_perception(self) -> int:
        wis_mod = self.get_modifier(self.stats["WIS"])
        prof = self.proficiency_bonus if "察觉" in self.skills else 0
        return 10 + wis_mod + prof

    # 动态计算法术加值
    @property
    def spell_attack_bonus(self) -> int:
        ability = SPELLCASTING_ABILITY.get(self.job)
        if not ability:
            return 0
        stat_mod = self.get_modifier(self.stats[ability])
        return self.proficiency_bonus + stat_mod

    # 动态计算法术豁免DC
    @property
    def spell_save_dc(self) -> int:
        ability = SPELLCASTING_ABILITY.get(self.job)
        if not ability:
            return 0  # 非施法职业返回 0
        stat_mod = self.get_modifier(self.stats[ability])
        return 8 + self.proficiency_bonus + stat_mod

    # 5. 给AI的提示词
    def get_status_text(self) -> str:
        # 1. 一次性算出所有属性的调整值
        mods = {stat_name:self.get_modifier(stat_value) for stat_name, stat_value in self.stats.items()}

        spell_text = ""
        if self.spell_save_dc > 0:
            spell_text = f"- 施法属性: {SPELLCASTING_ABILITY[self.job]} | 法术豁免DC: {self.spell_save_dc} | 法术攻击: {self.spell_attack_bonus:+}\n"
  
        return (
            f"【角色卡】{self.name}（{self.species}·{self.job}·{self.background}）\n"
            f"- 等级: {self.level} (熟练加值 {self.proficiency_bonus:+})\n"
            f"- 生命值: {self.hp}/{self.max_hp} | 护甲(AC): {self.ac} | 先攻: {self.initiative:+} | 被动感知: {self.passive_perception}\n"
            f"- 基础属性(值): 力量{self.stats['STR']} 敏捷{self.stats['DEX']} 体质{self.stats['CON']} 智力{self.stats['INT']} 感知{self.stats['WIS']} 魅力{self.stats['CHA']}\n"
            f"- 各项调整值: 力量{mods['STR']:+} 敏捷{mods['DEX']:+} 体质{mods['CON']:+} 智力{mods['INT']:+} 感知{mods['WIS']:+} 魅力{mods['CHA']:+}\n"
            f"{spell_text}"
            f"- 已掌握技能: {', '.join(self.skills) if self.skills else '无'}"
        )
