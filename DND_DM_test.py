import os
import openai
import json


from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from engine.dice import Dice
from engine.character import Character



client = OpenAI(
    api_key=os.environ["LLM_API_KEY"],
    base_url=os.environ["LLM_BASE_URL"],
    max_retries=0, 
    timeout=30
)

#tools json
tools = [
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
                    "job": {"type": "string", "description": "职业，如战士、法师"},
                    "background": {"type": "string", "description": "背景，如士兵、贤者"},
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



@retry( retry=retry_if_exception_type((
        openai.APITimeoutError,
        openai.APIConnectionError,
        openai.RateLimitError,
        openai.InternalServerError,
    )),
        stop=stop_after_attempt(3), 
        wait=wait_exponential(multiplier=1, max=10),
        reraise=True )
def call_llm(client, model, messages, tools):
    return client.chat.completions.create(model=model, messages=messages, tools=tools)


def build_request(messages, my_hero):
    request_messages = messages.copy()
    if my_hero is None:
        return request_messages

    # 从后往前找最后一条 user 消息，把状态插在它前面
    for i in reversed(range(len(request_messages))):
        if request_messages[i]["role"] == "user":
            status_text = f"【当前真实状态】\n{my_hero.get_status_text()}"
            request_messages.insert(i, {"role": "system", "content": status_text})
            break
    return request_messages

def tool_roll_dice(args):

    sides = args.get("sides", 20)

    dice_result = Dice.roll(sides) 
    print(f"  [系统底层] 掷出了 d{sides}，结果是 {dice_result}")

    return f" [系统底层] 掷出了 d{sides}，结果是 {dice_result}"

def tool_create_character(args):
    global my_hero
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
    my_hero=hero
    print(f"     [系统底层] 成功创建角色：{my_hero.name} ({bonus_msg})")
    print(my_hero.get_status_text()) 

    return f"角色 {my_hero.name} 创建成功，最终属性：{my_hero.stats}。请DM开始剧情。"

TOOLS={"roll_dice":tool_roll_dice,"create_character":tool_create_character}

messages=[
    {
        "role":"system",
        "content":("""你是一名 DND 5e (2024版) 的 DM。
在游戏开始前，你要引导玩家创建角色。你需要确认他们的：

- 名字

- 物种 (Species)

- 职业 (Class)

- 背景 (Background)

将标准数组 [15, 14, 13, 12, 10, 8] 分配给六项属性。

选择背景加值方案（方案A：+2/+1；方案B：+1/+1/+1），注意背景有特定的属性限制。

只有当玩家完全确认以上信息后，你才能调用 create_character 工具。绝对不要帮玩家做决定，要一步步询问。""")
    }
]

my_hero = None

while True:
    print("--------------------------------------------------------\n")
    user_input = input("你:")

    if user_input == "退出":                  
        print("已退出游戏，再见")
        break

    turn_start = len(messages)               
    hero_before = my_hero      

     # 1. 玩家的话正常存进历史
    messages.append({"role": "user", "content": user_input})
    
    # 2. 构造发请求的临时消息列表（复制一份副本）
    request_messages = build_request(messages, my_hero)

    try:
        # 1. 请求模型
        resp = call_llm(client, "deepseek-flash", request_messages, tools)
        reply_msg = resp.choices[0].message
        
        # 2. 核心判断：AI 是想说话，还是想调工具？
        tools_rounds:int = 0
        while reply_msg.tool_calls and tools_rounds <10 :
            tools_rounds+=1
            print("--------------------------------------------------------\n")
            print(f"  [系统提示] [第{tools_rounds}轮]AI 决定调用 {len(reply_msg.tool_calls)} 个工具！")

            # 必须把 AI 的意图存进历史，否则下一轮它会断片
            messages.append(reply_msg.model_dump(exclude_none=True))

            for tool_call in reply_msg.tool_calls:

                tool_name = tool_call.function.name
                print(f"  -> 正在执行工具: {tool_name}")
                try:
                    args = json.loads(tool_call.function.arguments)

                    if tool_name in TOOLS: 
                        result= TOOLS[tool_name](args)
                    else:   
                        result=f"调用的工具{tool_name}不存在，可用的工具有{", ".join(TOOLS.keys())}"
                except Exception as e:
                    print(f"工具执行出错：{type(e).__name__}: {e}")
                    result = f"工具执行出错：{type(e).__name__}: {e}"
                    
                messages.append({"role":"tool","tool_call_id": tool_call.id,"content":result})

            request_messages = build_request(messages, my_hero)

            # 拿着调用工具的结果和最新状态，再次请求 AI
            resp = call_llm(client, "deepseek-flash", request_messages, tools)
            reply_msg = resp.choices[0].message

        # 7. 打印最终给玩家看的文字
        reply = reply_msg.content or "（DM 陷入了沉思……工具调用超过 10 轮，请换个说法）"

        print("--------------------------------------------------------\n")
        print("DM:", reply)
        messages.append({"role": "assistant", "content": reply})
        

    except openai.APIError as e:
        print(f"调用失败：{e}")
        del messages[turn_start:]     # 这一轮加进去的全删
        my_hero = hero_before         # 角色也回滚
        continue
