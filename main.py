

import asyncio
import edge_tts
import pygame
from openai import OpenAI
import os
import time
import requests
import json
import re  # 引入正则库，用来精准抓取号码
from colorama import Fore, Style, init

# ================= 配置区域 =================

API_KEY = "sk-32b438b35e8244268821df49c7f68257"
BASE_URL = "https://api.deepseek.com"

# 飞书配置
FEISHU_APP_ID = "cli_a9a6b4f6ee381bdd"
FEISHU_APP_SECRET = "ev8q6bCqqE5FScMr80z3Gbf4h5ABiLXN"
FEISHU_APP_TOKEN = "NmM0b7F3PaH4EAsmpFIc7BIinde" # 你的Token
FEISHU_TABLE_ID = "tbl8t9V1RuU2YoyH"            # 你的TableID

# ===========================================

init(autoreset=True)
client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

SYSTEM_PROMPT = """
你叫“小智”，是【通衡科技】的金牌销售。
你的目标：推销“AI电销机器人”。
逻辑控制：
1. 必须引导客户说出具体的微信号或手机号。
2. 如果客户说“加个微信吧”，你要问：“好的王总，那我加您，您的微信号是多少？”
3. 【绝对禁止】在没有拿到具体数字/账号的情况下挂断电话！
4. 只有当客户明确报出一串数字/账号，或者客户明确拒绝（说不要/再见）时，你才能在回复末尾加上“【挂断】”。
"""

messages = [{"role": "system", "content": SYSTEM_PROMPT}]

# --- 辅助功能：精准提取微信号/手机号 ---
def extract_contact_info(text):
    """
    使用正则表达式提取内容中的微信号或手机号
    规则：提取连续的6位以上数字或字母组合
    """
    # 这一行代码是核心：寻找 [a-z0-9] 连续出现6次以上的字符串
    pattern = r'[a-zA-Z0-9_-]{6,}'
    match = re.search(pattern, text)
    if match:
        return match.group() # 返回提取到的号码
    return None

# --- 飞书功能 ---
def get_feishu_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json; charset=utf-8"}
    payload = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    try:
        r = requests.post(url, json=payload, headers=headers)
        return r.json().get("tenant_access_token")
    except: return None

def save_to_feishu(raw_input, contact_number, ai_reply):
    """
    raw_input: 客户原话 (例如：微信号是wx123)
    contact_number: 提取出的号码 (例如：wx123)
    """
    print(Fore.YELLOW + f"🔄 捕获到号码 [{contact_number}]，正在写入飞书...")
    
    token = get_feishu_token()
    if not token: return

    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"}
    
    data = {
        "fields": {
            "客户意向": "高意向(已留号)", 
            "客户回复": contact_number,  # 这里只存纯净的号码，方便你看
            "跟进状态": "待加V",
            "对话摘要": f"客户原话: {raw_input}" # 把原话存在摘要里以防万一
        }
    }
    
    try:
        resp = requests.post(url, json=data, headers=headers)
        if resp.status_code == 200 and resp.json().get("code") == 0:
            print(Fore.GREEN + f"✅ 成功！号码 [{contact_number}] 已同步到飞书！")
        else:
            print(Fore.RED + f"❌ 写入失败: {resp.json()}")
    except Exception as e:
        print(Fore.RED + f"❌ 报错: {e}")

# --- 核心功能 ---
async def speak(text):
    clean_text = text.replace("【挂断】", "")
    if not clean_text.strip(): return
    print(Fore.GREEN + f"通衡机器人: {clean_text}")
    filename = f"voice_{int(time.time())}.mp3"
    try:
        communicate = edge_tts.Communicate(clean_text, "zh-CN-YunxiNeural")
        await communicate.save(filename)
        pygame.mixer.init()
        pygame.mixer.music.load(filename)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            await asyncio.sleep(0.1)
        pygame.mixer.quit()
    except: pass
    finally:
        try: os.remove(filename)
        except: pass

def think(user_text):
    print(Fore.CYAN + "......")
    messages.append({"role": "user", "content": user_text})
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=0.7
        )
        ai_text = response.choices[0].message.content
        messages.append({"role": "assistant", "content": ai_text})
        return ai_text
    except: return "信号断了。"

# --- 主程序 ---
async def main():
    print(Fore.YELLOW + "=== 通衡科技 AI电销系统 (精准抓取版) ===")
    
    opening = "喂？你好，是王总吗？我是通衡科技的小智。"
    await speak(opening)
    messages.append({"role": "assistant", "content": opening})

    while True:
        try:
            user_input = input(Fore.WHITE + "客户(你): ")
            if not user_input: continue
            
            # 1. 先判断有没有号码
            extracted_num = extract_contact_info(user_input)
            
            # 2. 思考回复
            ai_reply = think(user_input)
            
            # 3. 逻辑分流
            if extracted_num:
                # 只有提取到了号码，才存飞书
                save_to_feishu(user_input, extracted_num, ai_reply)
            elif "微信" in user_input and "【挂断】" in ai_reply:
                # 补救措施：如果AI都要挂电话了，但还没抓到号，可能是AI判断失误
                # 这里可以选择强制存，或者不管它
                pass
            
            # 4. 说话
            await speak(ai_reply)
            
            if "【挂断】" in ai_reply:
                print(Fore.RED + "\n--- 通话结束 ---")
                break
                
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    asyncio.run(main())