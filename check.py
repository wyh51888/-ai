import requests
import json
from colorama import Fore, init

init(autoreset=True)

# 1. 填入配置 (直接从 main.py 复制过来)
APP_ID = "cli_a9a6b4f6ee381bdd"
APP_SECRET = "ev8q6bCqqE5FScMr80z3Gbf4h5ABiLXN"
APP_TOKEN = "NmM0b7F3PaH4EAsmpFIc7BIinde" # 你的新Token
TABLE_ID = "tbl8t9V1RuU2YoyH"            # 你的新TableID

def get_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json"}
    payload = {"app_id": APP_ID, "app_secret": APP_SECRET}
    try:
        r = requests.post(url, json=payload, headers=headers)
        return r.json().get("tenant_access_token")
    except:
        return None

def check_columns():
    print(Fore.YELLOW + "正在读取表格列名...")
    token = get_token()
    if not token:
        print(Fore.RED + "无法连接飞书，请检查App ID和Secret")
        return

    # 获取列名的API
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/fields"
    headers = {"Authorization": f"Bearer {token}"}
    
    r = requests.get(url, headers=headers)
    data = r.json()
    
    if data.get("code") == 0:
        print(Fore.GREEN + "✅ 连接成功！你表格里目前的列名如下：")
        print("-" * 30)
        items = data["data"]["items"]
        for item in items:
            print(f"列名: {Fore.CYAN}{item['field_name']}{Fore.RESET}  (类型: {item['ui_type']})")
        print("-" * 30)
        print(Fore.WHITE + "👉 请确保代码里的 '客户回复' 和上面打印出来的完全一样！")
        print("常见错误：多了空格、繁体字、或者根本还没改名（叫'多选'或'文本'）。")
    else:
        print(Fore.RED + f"读取失败: {data}")

if __name__ == "__main__":
    check_columns()