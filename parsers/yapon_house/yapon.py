import requests
import os
import json
import time
from parsers.yapon_house.headers_config import HEADERS_ADDRESS
from typing import List
from bs4 import BeautifulSoup


def get_info_for_site(
        url: str,
        address: str,
        city: str
) -> dict:
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'Connection': 'keep-alive',
        'Referer': '',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Chromium";v="116", "Not)A;Brand";v="24", "Google Chrome";v="116"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
    }

    headers["Referer"] = url

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html5lib")

    info = {
        "name": "Японский Домик",
        "address": None,
        "latlon": None,
        "phones": None,
        "working_hours": None
    }

    # найдем скрипт и добавим в словарь
    js_data = {}
    for script in soup.find_all("script"):
        script_next = script.next
        if script_next:
            script_str = str(script_next)
            if script_str.find("window.initialState") != -1:
                script_str = script_str.replace("window.initialState = ", "")
                js_data = json.loads(script_str)

    if js_data:
        city_js = js_data.get("city")
        city_name_js = city_js.get("name").lower() if city_js.get("name") else ""
        if city.lower() == city_name_js:
            phone_param = city_js.get("callCenterPhoneParameters")
            phone = phone_param.get("number") if phone_param.get("number") else ""
            info["phones"] = [phone]

        shops = js_data.get("shops")
        for shop_item in shops:
            s_address = shop_item.get("address")
            if address == s_address:
                info["address"] = f"{city}, {s_address}"

                coord = shop_item.get("coord")
                lat = float(coord.get("latitude")) if coord.get("latitude") else 0.0
                lon = float(coord.get("longitude")) if coord.get("latitude") else 0.0
                info["latlon"] = [lat, lon]

                w_hours = shop_item.get("workingHours")
                info["working_hours"] = convert_working_house(w_hours)

    return info


def convert_working_house(working_hours: list) -> List[str]:
    days_dict = {
        1: "Пн",
        2: "Вт",
        3: "Ср",
        4: "Чт",
        5: "Пт",
        6: "Сб",
        7: "Вс",
    }
    result_d = {}

    for item in working_hours:
        item_type = item.get("type")
        if item_type == "default":
            start = item.get("from") if item.get("from") else "0"
            finish = item.get("to") if item.get("to") else "0"

            time_str = f"{start}:{finish}"
            day_num = item.get("day")

            if time_str in result_d.keys():
                result_d.get(time_str).append(day_num)
            else:
                result_d.update({time_str: [day_num]})

    for time_str, days_list in list(result_d.items()):
        if len(days_list) > 1:
            start_day_num = min(days_list)
            finish_day_num = max(days_list)

            result_str = f"{days_dict.get(start_day_num)} - {days_dict.get(finish_day_num)}"
            result_d[time_str] = result_str
        else:
            try:
                result_str = days_dict.get(days_list[0])
                result_d[time_str] = result_str
            except ValueError as e:
                result_d[time_str] = ""

    general_res = []
    for time_str, days_row in list(result_d.items()):
        start_time_row = time_str.split(":")[0]
        finish_time_row = time_str.split(":")[1]

        start_time_secs = int(start_time_row) * 60
        start_result = time.strftime("%H:%M", time.gmtime(start_time_secs))
        finish_time_secs = int(finish_time_row) * 60
        finish_result = time.strftime("%H:%M", time.gmtime(finish_time_secs))

        time_result_row = f'{start_result} - {finish_result}'
        result = f'{days_row} {time_result_row}'
        general_res.append(result)

    return general_res


def run():
    # с этого запроса нужно забрать города и ссылки на них
    # стартовая Омск
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
    }

    url = 'https://omsk.yapdomik.ru/'
    response = requests.get(url, headers=headers)

    soup = BeautifulSoup(response.text, "html5lib")

    cities_data_write: List[str] = ["Омск>https://omsk.yapdomik.ru\n"]
    cities_list_soup = soup.find("div", class_="city-select__list")
    cities_elements = cities_list_soup.find_all("a", class_="city-select__item")

    for city_el in cities_elements:
        city_str = city_el.text.strip()
        city_link = city_el.attrs.get("href")

        result_row = f"{city_str}>{city_link}\n"
        cities_data_write.append(result_row)

    current_dir = os.getcwd()
    path_file = current_dir.replace(r"parsers\yapon_house", r"files\yapon_house\\")
    cities_with_urls_path = path_file + r"cities_with_urls.txt"

    # запишем все наши города и урлы на них в файл
    with open(cities_with_urls_path, "w", encoding="utf-8") as file:
        file.writelines(cities_data_write)

    # сейчас нужно перейти на все страницы городов
    # и записать их адреса в файл
    address_result = []
    with open(cities_with_urls_path, "r", encoding="utf-8") as file:
        for row in file.readlines():
            city_str, url_str = row.split(">")
            url_str = url_str.strip()

            response = requests.get(url_str, **HEADERS_ADDRESS)
            soup = BeautifulSoup(response.text, "html5lib")

            address_list_el = soup.find("div", class_="site-footer__address-list")
            for li_el in address_list_el.find_all("li"):
                result_row = f"{city_str}>{li_el.text}\n"
                address_result.append(result_row)

    address_file_path = path_file + r"address_all_cities.txt"
    with open(address_file_path, "w", encoding="utf-8") as f:
        f.writelines(address_result)

    # сгенерим словарь с урлами чтобы не доставать из файла
    city_urls_d = {}
    for row in cities_data_write:
        c, c_url = row.split(">")
        city_urls_d.update({c: c_url})

    results = []
    # собираем информацию по каждому адресу
    for x in address_result:
        city, address = x.split(">")
        city_url = city_urls_d.get(city)
        city_url = city_url.strip()
        address = address.strip()
        city = city.strip()

        info = get_info_for_site(url=city_url, address=address, city=city)
        results.append(info)

    res_path = path_file + r"results.txt"
    with open(res_path, "w", encoding="utf-8") as file:
        res_json = json.dumps(
            results,
            sort_keys=False,
            indent=4,
            ensure_ascii=False,
            separators=(',', ': ')
        )
        file.writelines(res_json)


run()
