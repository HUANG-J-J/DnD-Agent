from engine.character import BACKGROUND_STATS, CLASS_HIT_DICE, Character

TOOL_SCHEMAS = [
    {   
        "type":"function",
        "function":{
            "name":"roll_dice",
            "description":"掷骰子。当需要检定时使用，例如：攻击命中、技能使用、伤害数值、特殊行动",
            "parameters":{
                "type":"object",
                "properties":{
                    "sides":{
                        "type":"integer",
                        "description":"骰子的面数。例如：d20填20，d8填8"
                    }
                },
                "required":["sides"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_character",
            "description": "当玩家提供了角色名字、种族和职业后，调用此工具创建角色并开始游戏。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "玩家的角色名"},
                    "species": {"type": "string", "description": "物种，如精灵、矮人"},
                    "job": {"type": "string", "description": "职业，如战士、法师","enum":list(CLASS_HIT_DICE)},
                    "background": {"type": "string", "description": "背景，如士兵、贤者","enum":list(BACKGROUND_STATS)},
                    "base_stats": {
                        "type": "object",
                        "description": "标准数组(15,14,13,12,10,8)的分配结果",
                        "additionalProperties": False,
                        "properties": {
                            "STR": {"type": "integer"}, "DEX": {"type": "integer"},
                            "CON": {"type": "integer"}, "INT": {"type": "integer"},
                            "WIS": {"type": "integer"}, "CHA": {"type": "integer"}
                        },
                        "required": ["STR", "DEX", "CON", "INT", "WIS", "CHA"]
                    },
                    "bonus_distribution": {"type": "string", "enum": ["A", "B"], "description": "方案A(+2/+1)或方案B(+1/+1/+1)"},
                    "bonus_stat1": {"type": "string", "description": "方案A加值的第一个属性"},
                    "bonus_stat2": {"type": "string", "description": "方案A加值的第二个属性"}
                },
                "required": ["name", "species", "job", "background", "base_stats", "bonus_distribution", "bonus_stat1"]
            }
        }
    }
]

def tool_roll_dice(args,state):

    sides = args.get("sides", 20)



    dice_result = state.dice.roll(sides) 
    print(f"  [系统底层] 掷出了 d{sides}，结果是 {dice_result}")

    return f" [系统底层] 掷出了 d{sides}，结果是 {dice_result}"

def tool_create_character(args,state):
    
    hero = Character(
                        name=args["name"],
                        species=args["species"],
                        job=args["job"],
                        background=args["background"],
                        base_stats=args["base_stats"]
                    )

    bonus_msg = hero.apply_background_bonus(
                        distribution=args["bonus_distribution"],
                        stat1=args["bonus_stat1"],
                        stat2=args.get("bonus_stat2")
                    )
    hero.hp = hero.max_hp
    state.hero=hero
    print(f"     [系统底层] 成功创建角色：{state.hero.name} ({bonus_msg})")
    print(state.hero.get_status_text()) 

    return f"角色 {state.hero.name} 创建成功，最终属性：{state.hero.stats}。请DM开始剧情。"

TOOL_FUNCS={"roll_dice":tool_roll_dice,"create_character":tool_create_character}
