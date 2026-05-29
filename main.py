import random
import sys
import os
import ast
from time import localtime
from requests import get, post
from datetime import datetime, date
from zhdate import ZhDate

def get_color():
    # 获取随机颜色
    get_colors = lambda n: list(map(lambda i: "#" + "%06x" % random.randint(0, 0xFFFFFF), range(n)))
    color_list = get_colors(100)
    return random.choice(color_list)

def get_access_token():
    # appId 和 appSecret
    app_id = config.get("app_id")
    app_secret = config.get("app_secret")
    post_url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={app_id}&secret={app_secret}"
    
    try:
        response_json = get(post_url).json()
        access_token = response_json['access_token']
        return access_token
    except KeyError:
        print(f"❌ 获取access_token失败，请检查app_id和app_secret是否正确。微信返回信息: {response_json}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 请求微信Token接口发生异常: {e}")
        sys.exit(1)

def get_weather(region):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36'
    }
    key = config["weather_key"]
    region_url = f"https://geoapi.qweather.com/v2/city/lookup?location={region}&key={key}"
    
    # 1. 获取地区ID
    res = get(region_url, headers=headers)
    if res.status_code != 200:
        print(f"❌ 获取地区ID失败，HTTP状态码: {res.status_code}，返回内容: {res.text}")
        sys.exit(1)
        
    try:
        response = res.json()
    except Exception:
        print(f"❌ 地区接口返回非JSON数据 (可能被拦截): {res.text}")
        sys.exit(1)

    if response["code"] == "404":
        print("❌ 推送消息失败，请检查地区名是否有误！")
        sys.exit(1)
    elif response["code"] == "401":
        print("❌ 推送消息失败，请检查和风天气key是否正确！")
        sys.exit(1)
    
    location_id = response["location"][0]["id"]
    
    # 2. 获取天气详情
    weather_url = f"https://devapi.qweather.com/v7/weather/now?location={location_id}&key={key}"
    res_weather = get(weather_url, headers=headers)
    
    if res_weather.status_code != 200:
        print(f"❌ 获取天气失败，HTTP状态码: {res_weather.status_code}，返回内容: {res_weather.text}")
        sys.exit(1)

    response_weather = res_weather.json()
    # 天气
    weather = response_weather["now"]["text"]
    # 当前温度
    temp = response_weather["now"]["temp"] + u"\N{DEGREE SIGN}" + "C"
    # 风向
    wind_dir = response_weather["now"]["windDir"]
    return weather, temp, wind_dir

def get_birthday(birthday_str, year, today):
    birthday_year = birthday_str.split("-")[0]
    # 判断是否为农历生日
    if birthday_year[0] == "r":
        r_mouth = int(birthday_str.split("-")[1])
        r_day = int(birthday_str.split("-")[2])
        try:
            birthday_date = ZhDate(year, r_mouth, r_day).to_datetime().date()
        except TypeError:
            print(f"❌ 请检查生日 {birthday_str} 的日子是否在今年存在")
            sys.exit(1)
            
        birthday_month = birthday_date.month
        birthday_day = birthday_date.day
        year_date = date(year, birthday_month, birthday_day)
    else:
        # 国历生日
        birthday_month = int(birthday_str.split("-")[1])
        birthday_day = int(birthday_str.split("-")[2])
        year_date = date(year, birthday_month, birthday_day)
        
    # 计算生日年份
    if today > year_date:
        if birthday_year[0] == "r":
            r_last_birthday = ZhDate((year + 1), r_mouth, r_day).to_datetime().date()
            birth_date = date((year + 1), r_last_birthday.month, r_last_birthday.day)
        else:
            birth_date = date((year + 1), birthday_month, birthday_day)
        birth_day = str(birth_date.__sub__(today)).split(" ")[0]
    elif today == year_date:
        birth_day = 0
    else:
        birth_date = year_date
        birth_day = str(birth_date.__sub__(today)).split(" ")[0]
    return birth_day

def get_ciba():
    url = "http://open.iciba.com/dsapi/"
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36'
    }
    r = get(url, headers=headers)
    note_en = r.json()["content"]
    note_ch = r.json()["note"]
    return note_ch, note_en

def send_message(to_user, access_token, region_name, weather, temp, wind_dir, note_ch, note_en):
    url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={access_token}"
    week_list = ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"]
    year = localtime().tm_year
    month = localtime().tm_mon
    day = localtime().tm_mday
    today = date(year, month, day)
    week = week_list[today.isoweekday() % 7]
    
    # 获取在一起的日子的日期格式
    love_year = int(config["love_date"].split("-")[0])
    love_month = int(config["love_date"].split("-")[1])
    love_day = int(config["love_date"].split("-")[2])
    love_date = date(love_year, love_month, love_day)
    love_days = str(today.__sub__(love_date)).split(" ")[0]
    
    # 获取所有生日数据
    birthdays = {k: v for k, v in config.items() if k.startswith("birth")}
        
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
            "note_en": {"value": note_en, "color": get_color()},
            "note_ch": {"value": note_ch, "color": get_color()}
        }
    }
    
    for key, value in birthdays.items():
        birth_day = get_birthday(value["birthday"], year, today)
        if birth_day == 0:
            birthday_data = f"今天{value['name']}生日哦，祝{value['name']}生日快乐！"
        else:
            birthday_data = f"距离{value['name']}的生日还有{birth_day}天"
        data["data"][key] = {"value": birthday_data, "color": get_color()}
        
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36'
    }
    
    response = post(url, headers=headers, json=data).json()
    if response["errcode"] == 40037:
        print("❌ 推送消息失败，请检查模板id是否正确")
    elif response["errcode"] == 40036:
        print("❌ 推送消息失败，请检查模板id是否为空")
    elif response["errcode"] == 40003:
        print("❌ 推送消息失败，请检查微信号是否正确")
    elif response["errcode"] == 0:
        print(f"✅ 成功向用户 {to_user} 推送消息")
    else:
        print(f"⚠️ 推送结果未知: {response}")

if __name__ == "__main__":
    try:
        with open("config.txt", "r", encoding="utf-8") as f:
            # 使用 ast.literal_eval 替代 eval，更加安全且不易出错
            config = ast.literal_eval(f.read())
    except FileNotFoundError:
        print("❌ 推送消息失败，未找到 config.txt 文件，请检查路径。")
        sys.exit(1)
    except SyntaxError:
        print("❌ 推送消息失败，请检查 config.txt 配置文件格式是否为标准的Python字典格式。")
        sys.exit(1)

    # 获取accessToken
    print("⏳ 正在获取微信 Access Token...")
    accessToken = get_access_token()
    
    users = config["user"]
    region = config["region"]
    
    print(f"⏳ 正在获取 {region} 的天气信息...")
    weather, temp, wind_dir = get_weather(region)
    
    note_ch = config.get("note_ch", "")
    note_en = config.get("note_en", "")
    if not note_ch and not note_en:
        print("⏳ 正在获取词霸每日金句...")
        note_ch, note_en = get_ciba()
        
    print("⏳ 开始推送消息...")
    for user in users:
        send_message(user, accessToken, region, weather, temp, wind_dir, note_ch, note_en)
        
    print("🎉 脚本运行结束。")
