import json
import os
import random
from pathlib import Path

import openai
from openai import OpenAI
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from engine.state import GameState
from tools.dnd_tools import TOOL_FUNCS, TOOL_SCHEMAS

PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"
SYSTEM_PROMPT = (PROMPT_DIR / "dm_system.md").read_text(encoding="utf-8")


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


def build_request(messages, hero):
    request_messages = messages.copy()
    if hero is None:
        return request_messages

    # 从后往前找最后一条 user 消息，把状态插在它前面
    for i in reversed(range(len(request_messages))):
        if request_messages[i]["role"] == "user":
            status_text = f"【当前真实状态】\n{hero.get_status_text()}"
            request_messages.insert(i, {"role": "system", "content": status_text})
            break
    return request_messages

def main():

    client = OpenAI(
    api_key=os.environ["LLM_API_KEY"],
    base_url=os.environ["LLM_BASE_URL"],
    max_retries=0, 
    timeout=30
    )

    seed = random.randrange(1_000_000)
    print(f"本局种子：{seed}")
    state = GameState(seed)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    while True:
        print("--------------------------------------------------------\n")
        user_input = input("你:")

        if user_input == "退出":                  
            print("已退出游戏，再见")
            break

        turn_start = len(messages)               
        hero_before = state.hero      

        # 1. 玩家的话正常存进历史
        messages.append({"role": "user", "content": user_input})
        
        # 2. 构造发请求的临时消息列表（复制一份副本）
        request_messages = build_request(messages, state.hero)

        try:
            # 1. 请求模型
            resp = call_llm(client, "deepseek-flash", request_messages, TOOL_SCHEMAS)
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

                        if tool_name in TOOL_FUNCS: 
                            result= TOOL_FUNCS[tool_name](args,state)
                        else:   
                            result=f"调用的工具{tool_name}不存在，可用的工具有{", ".join(TOOL_FUNCS.keys())}"
                    except Exception as e:
                        print(f"工具执行出错：{type(e).__name__}: {e}")
                        result = f"工具执行出错：{type(e).__name__}: {e}"
                        
                    messages.append({"role":"tool","tool_call_id": tool_call.id,"content":result})

                request_messages = build_request(messages, state.hero)

                # 拿着调用工具的结果和最新状态，再次请求 AI
                resp = call_llm(client, "deepseek-flash", request_messages, TOOL_SCHEMAS)
                reply_msg = resp.choices[0].message

            # 7. 打印最终给玩家看的文字
            reply = reply_msg.content or "（DM 陷入了沉思……工具调用超过 10 轮，请换个说法）"

            print("--------------------------------------------------------\n")
            print("DM:", reply)
            messages.append({"role": "assistant", "content": reply})
            

        except openai.APIError as e:
            print(f"调用失败：{e}")
            del messages[turn_start:]     # 这一轮加进去的全删
            state.hero = hero_before         # 角色也回滚
            continue

if __name__ == "__main__":
    main()

