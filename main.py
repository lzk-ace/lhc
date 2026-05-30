import random
import sys
import ast
import requests
from time import localtime
from datetime import datetime, date
from zhdate import ZhDate

def get_color():
    get_colors = lambda n: list(map(lambda i: "#" + "%06x" % random.randint(0, 0xFFFFFF), range(n)))
    return random.choice(get_colors(100))

def get_access_token():
    app_id = config.get("app_id")
    app_secret = config.get("app_secret")
    post_url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={app_id}&secret={app_secret}"
    try:
        res = requests.get(post_url).json()
        if "access_token" in res:
            return res['access_token']
        else:
            print(f"❌ 微信拒绝访问！(大概率是 app_secret 错误或失效)\n微信返回: {res}")
            sys.exit(1)
    except Exception as e:
        print(f"请求微信接口异常: {e}")
        sys.exit(1)

def get_weather(region):
    """专门为高德开放平台编写的天气获取逻辑"""
    key = config.get("weather_key")
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    # 第一步：高德地理编码接口（将地名转换为高德专属 adcode）
    geo_url = f"https://restapi.amap.com/v3/geocode/geo?address={region}&key={key}"
    try:
        geo_res = requests.get(geo_url, headers=headers).json()
        if geo_res.get("status") == "1" and geo_res.get("geocodes"):
            adcode = geo_res["geocodes"][0]["adcode"]
        else:
            print(f"⚠️ 高德无法识别地区 '{region}' 或 Key 无效。返回: {geo_res}")
            return "获取失败", "未知", "未知"
            
        # 第二步：高德实时天气接口
        weather_url = f"https://restapi.amap.com/v3/weather/weatherInfo?city={adcode}&key={key}"
        weather_res = requests.get(weather_url, headers=headers).json()
        if weather_res.get("status") == "1" and weather_res.get("lives"):
            live = weather_res["lives"][0]
            weather = live.get("weather")
            temp = live.get("temperature") + "°C"
            wind_dir = live.get("winddirection") + "风"
            return weather, temp, wind_dir
        else:
            print(f"⚠️ 高德天气获取失败: {weather_res}")
            return "获取失败", "未知", "未知"
            
    except Exception as e:
        print(f"⚠️ 高德接口请求异常: {e}")
        return "获取失败", "未知", "未知"

def get_birthday(birthday, year, today):
    birthday_year = birthday.split("-")[0]
    if birthday_year[0] == "r":
        r_mouth = int(birthday.split("-")[1])
        r_day = int(birthday.split("-")[2])
        try:
            birthday_date = ZhDate(year, r_mouth, r_day).to_datetime().date()
        except TypeError:
            print("农历生日日期错误")
            sys.exit(1)
        year_date = date(year, birthday_date.month, birthday_date.day)
    else:
        year_date = date(year, int(birthday.split("-")[1]), int(birthday.split("-")[2]))
        
    if today > year_date:
        if birthday_year[0] == "r":
            r_last = ZhDate((year + 1), r_mouth, r_day).to_datetime().date()
            birth_date = date((year + 1), r_last.month, r_last.day)
        else:
            birth_date = date((year + 1), int(birthday.split("-")[1]), int(birthday.split("-")[2]))
        return (birth_date - today).days
    elif today == year_date:
        return 0
    else:
        return (year_date - today).days

def get_ciba():
    url = "https://open.iciba.com/dsapi/"
    headers = {'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(url, headers=headers, timeout=5)
        data = r.json()
        return data.get("note", "愿你每一天都充满阳光。"), data.get("content", "May your every day be full of sunshine.")
    except Exception:
        return "愿你每一天都充满阳光。", "May your every day be full of sunshine."

def send_message(to_user, access_token, region_name, weather, temp, wind_dir, note_ch, note_en):
    url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={access_token}"
    today = datetime.date(datetime(year=localtime().tm_year, month=localtime().tm_mon, day=localtime().tm_mday))
    week = ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"][today.isoweekday() % 7]
    
    love_date = date(int(config["love_date"].split("-")[0]), int(config["love_date"].split("-")[1]), int(config["love_date"].split("-")[2]))
    love_days = str((today - love_date).days)
    
    birthdays = {k: v for k, v in config.items() if "birth" in k}
            
    data = {
        "touser": to_user,
        "template_id": config["template_id"],
        "data": {
            "date": {"value": f"{today} {week}", "color": get_color()},
            "region": {"value": region_name, "color": get_color()},
            "weather": {"value": weather, "color": get_color()},
            "temp": {"value": temp, "color": get_color()},
            "wind_dir": {"value": wind_dir, "color": get_color()},
            "love_day": {"value": love_days, "color": get_color()},
            "cn": {"value": note_ch, "color": get_color()},
            "en": {"value": note_en, "color": get_color()}
        }
    }
    
    for key, value in birthdays.items():
        birth_day = get_birthday(value["birthday"], localtime().tm_year, today)
        birthday_data = f"今天{value['name']}生日哦，生日快乐！🎂" if birth_day == 0 else f"距离{value['name']}的生日还有 {birth_day} 天"
        data["data"][key] = {"value": birthday_data, "color": get_color()}

    try:
        response = requests.post(url, headers={'Content-Type': 'application/json'}, json=data)
        if response.json().get("errcode") == 0:
            print(f"[{to_user}] 推送成功 🎉")
        else:
            print(f"[{to_user}] 推送失败: {response.json()}")
    except Exception as e:
        print(f"请求微信接口异常: {e}")

if __name__ == "__main__":
    try:
        with open("config.txt", encoding="utf-8") as f:
            config = ast.literal_eval(f.read())
    except Exception as e:
        print(f"读取 config.txt 失败: {e}")
        sys.exit(1)

    accessToken = get_access_token()
    users = config.get("user", [])
    
    region = config.get("region", "怀化")
    weather, temp, wind_dir = get_weather(region)
    
    note_ch = config.get("note_ch", "").strip()
    note_en = config.get("note_en", "").strip()
    if not note_ch and not note_en:
        note_ch, note_en = get_ciba()
        
    for user in users:
        send_message(user, accessToken, region, weather, temp, wind_dir, note_ch, note_en)
