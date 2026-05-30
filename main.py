import random
import sys
import ast
import requests
import json
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
        return requests.get(post_url).json()['access_token']
    except Exception as e:
        print(f"获取 access_token 失败: {e}")
        sys.exit(1)

def get_weather(region):
    headers = {'User-Agent': 'Mozilla/5.0'}
    key = config.get("weather_key")
    region_url = f"https://geoapi.qweather.com/v2/city/lookup?location={region}&key={key}"
    try:
        res_region = requests.get(region_url, headers=headers)
        if res_region.status_code != 200: return "获取失败", "未知", "未知"
        region_data = res_region.json()
        if str(region_data.get("code")) != "200": return "获取失败", "未知", "未知"
        location_id = region_data["location"][0]["id"]
        weather_url = f"https://devapi.qweather.com/v7/weather/now?location={location_id}&key={key}"
        res_weather = requests.get(weather_url, headers=headers)
        if res_weather.status_code != 200: return "获取失败", "未知", "未知"
        weather_data = res_weather.json()
        return weather_data["now"]["text"], weather_data["now"]["temp"] + "°C", weather_data["now"]["windDir"]
    except Exception:
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
        return data.get("note", "减轻他人负担的人绝非无用。"), data.get("content", "No one is useless who lightens another’s burden.")
    except Exception:
        return "减轻他人负担的人绝非无用。", "No one is useless who lightens another’s burden."

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
        "url": "http://weixin.qq.com/download",
        "topcolor": "#FF0000",
        "data": {
            "date": {"value": f"{today} {week}", "color": get_color()},
            "region": {"value": region_name, "color": get_color()},
            "weather": {"value": weather, "color": get_color()},
            "temp": {"value": temp, "color": get_color()},
            "wind_dir": {"value": wind_dir, "color": get_color()},
            "love_day": {"value": love_days, "color": get_color()},
            "jinju_en": {"value": note_en if note_en else "Test English Quote", "color": "#000000"},
            "jinju_cn": {"value": note_ch if note_ch else "测试中文金句", "color": "#000000"}
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
        print(f"请求异常: {e}")

if __name__ == "__main__":
    try:
        with open("config.txt", encoding="utf-8") as f:
            config = ast.literal_eval(f.read())
    except Exception as e:
        print(f"读取 config.txt 失败: {e}")
        sys.exit(1)

    accessToken = get_access_token()
    users = config.get("user", [])
    region = config.get("region", "未知")
    weather, temp, wind_dir = get_weather(region)
    
    note_ch = config.get("note_ch", "").strip()
    note_en = config.get("note_en", "").strip()
    if not note_ch and not note_en:
        note_ch, note_en = get_ciba()
        
    for user in users:
        send_message(user, accessToken, region, weather, temp, wind_dir, note_ch, note_en)
