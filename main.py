import requests
import sys
import ast

def get_access_token(app_id, app_secret):
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={app_id}&secret={app_secret}"
    return requests.get(url).json().get('access_token')

def send_minimal_message(to_user, access_token, template_id):
    url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={access_token}"
    
    data = {
        "touser": to_user,
        "template_id": template_id,
        "data": {
            "word": {
                "value": "如果你能看到这句话，说明大括号和变量名完全没问题！",
                "color": "#FF0000"
            }
        }
    }
    
    res = requests.post(url, headers={'Content-Type': 'application/json'}, json=data).json()
    print(f"微信返回结果: {res}")

if __name__ == "__main__":
    try:
        with open("config.txt", encoding="utf-8") as f:
            config = ast.literal_eval(f.read())
    except Exception as e:
        print(f"配置错误: {e}")
        sys.exit(1)

    token = get_access_token(config["app_id"], config["app_secret"])
    
    for user in config["user"]:
        send_minimal_message(user, token, config["template_id"])
