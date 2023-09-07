import json
import os
import re
from parsers.dentalia.headers_config import HEADERS_PAGE, HEADERS_LATLON
from typing import List

import requests
from bs4 import BeautifulSoup
from translate import Translator

result_data: List[dict] = []
translator = Translator(from_lang="ES", to_lang="EN")


def run():
    print("Parser for DENTALIA started")

    url = "https://dentalia.com/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "lxml")

    section_items = soup.find_all("section", class_="elementor-section elementor-inner-section elementor-element "
                                                    "elementor-element-01a0b47 LinkToClinic elementor-section-boxed "
                                                    "elementor-section-height-default elementor-section-height-default")

    current_dir = os.getcwd()
    path_file = current_dir.replace(r"parsers\dentalia", r"files\dentalia\\")
    url_for_parsing_file_path = path_file + r"urls_for_parsing.txt"

    # создаем файл всех URL для поиска информации обо всех клиниках
    with open(
            url_for_parsing_file_path, "w", encoding="utf-8"
    ) as file:
        for section in section_items:
            name_clinic = section.find("div", class_="jet-listing-dynamic-field__content").text
            url_for_parse = section.attrs.get("id")
            result_str = f"{name_clinic}>{url_for_parse}\n"

            file.write(result_str)

    print(f"Added {len(section_items)} lines to the urls_for_parsing.txt file")

    print("We're starting to gather information on each clinic.")
    with open(url_for_parsing_file_path, "r", encoding="utf-8") as file:
        for row in file.readlines():
            clinic, url = row.split(">")
            print(f"The script started working for {clinic}...")
            clinic_id = url[url.index("estados:") + len("estados:"):]
            clinic_id = clinic_id.strip()

            print(f"Clinic ID is [{clinic_id}]")
            clinic_info = parse_info(clinic_id)

            for item_dict in clinic_info:
                result_data.append(item_dict)

    print(f"Found information on {len(result_data)} clinics.")

    result_data_path_file = path_file + r"dentalia_result.txt"
    print("We start writing to the final file....")
    with open(result_data_path_file, "w", encoding="utf-8") as file:
        res_json = json.dumps(result_data)
        file.write(res_json)


def update_param_headers(estados_id: str):
    refer_url = "https://dentalia.com/clinica/?jsf=jet-engine:clinicas-archive&tax=estados:"
    HEADERS_PAGE["headers"].update({"Referer": refer_url + estados_id})
    tax_param = "estados:"
    HEADERS_PAGE["params"].update({"tax": tax_param + estados_id})

    refer_url = "https://dentalia.com/clinica/?jsf=jet-engine:clinicas-archive&tax=estados:"
    HEADERS_LATLON["headers"].update({"Referer": refer_url + estados_id})
    HEADERS_LATLON["data"].update({"query[_tax_query_estados]": estados_id})

    return HEADERS_PAGE, HEADERS_LATLON


def parse_info(estados_id: str) -> List[dict]:
    headers_page, headers_latlon = update_param_headers(estados_id)

    response = requests.post('https://dentalia.com/clinica/', **headers_page)

    html_content = json.loads(response.text).get('data')
    if html_content:
        html_content = html_content.get('html')

    soup = BeautifulSoup(html_content, "html5lib")

    # информация разбита по section, которых мб > 1
    section_elements = soup.find_all(attrs={"data-id": "1b2744e"})
    clinics_info = []

    for section_el in section_elements:
        info = {
            "name": None,
            "address": None,
            "latlon": None,
            "phones": None,
            "working_hours": None
        }

        clinic_name = section_el.find("h3", class_="elementor-heading-title elementor-size-default").text
        info["name"] = clinic_name

        address = section_el.find("div", attrs={"data-id": "b843495"})
        address = address.find("div", class_="jet-listing-dynamic-field__content").text
        info["address"] = address

        phone_str = section_el.find("div", attrs={"data-id": "cb84d19"})
        phone_str = phone_str.find("div", class_="jet-listing-dynamic-field__content").text
        phones = convert_phone_str_to_list(phone_str)
        info["phones"] = phones

        working_hours_str = section_el.find("div", attrs={"data-id": "9e2c33b"})
        working_hours_str = working_hours_str.find("div", class_="jet-listing-dynamic-field__content").text
        working_hours = convert_w_hours_to_list(working_hours_str)
        info["working_hours"] = working_hours

        latlon_id_elem = section_el.find_parent("div", class_="jet-engine-listing-overlay-wrap").attrs.get("data-url")
        latlon_id_elem = latlon_id_elem[latlon_id_elem.index("id") + 3:]
        latlon_id = int(latlon_id_elem)

        # получаем данные координат
        response = requests.post('https://dentalia.com/wp-admin/admin-ajax.php', **headers_latlon)
        res_json = response.json()
        markers = res_json.get("markers")
        latlon_res: List = []
        for mark in markers:
            mark_id = mark.get("id")
            if latlon_id == mark_id:
                latLang_dict = mark.get("latLang")

                lat_str = latLang_dict.get("lat")
                lat_num = float(lat_str) if lat_str else 0.0

                lng_str = latLang_dict.get("lng")
                lng_num = float(lng_str) if lng_str else 0.0

                latlon_res.append(lat_num)
                latlon_res.append(lng_num)
        info["latlon"] = latlon_res

        clinics_info.append(info)
    return clinics_info


def convert_w_hours_to_list(w_hours_str: str) -> List[str]:
    r1 = r"\w.+?[0-9]{1,2}am\s*[a]{1}\s*[0-9]{1,2}pm"
    r2 = r"\w.+?[0-9]{1}[0-9:]{2}[0-9]{1,2}\s*[a-z]{1}\s*[0-9]{2}[:]{1}[0-9]{2}"

    hours_result = []
    w_hours_str = w_hours_str[w_hours_str.index(":") + 1:]

    data = re.findall(r1, w_hours_str) if re.search(r1, w_hours_str) else re.findall(r2, w_hours_str)
    if data:
        for row in data:
            row_result = translator.translate(row)
            hours_result.append(row_result.strip())

    return hours_result


def convert_phone_str_to_list(phone_str: str) -> List[str]:
    # TODO: эту функицю можно переделать с помощью regex
    phone_str = phone_str[phone_str.find(":") + 1:]
    phone_list = []

    if phone_str != -1:
        count = phone_str.count(")")

        while count != 0:
            telephone = ""
            find_tel_code = False

            iter_num = 0
            for char in phone_str:
                iter_num += 1
                if char == "(" and len(telephone) < 2:
                    telephone += char
                    continue
                if char == ")" and not find_tel_code:
                    find_tel_code = True
                    telephone += char
                    continue

                last_symb = iter_num == len(phone_str)
                if find_tel_code and (char == "(" or last_symb):
                    if last_symb:
                        telephone += char
                    count -= 1
                    break
                telephone += char

            phone_list.append(telephone.strip())
            phone_str = phone_str.replace(telephone, "")

    return phone_list


run()
