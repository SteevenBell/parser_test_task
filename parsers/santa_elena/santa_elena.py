import json
import os

import requests
from bs4 import BeautifulSoup
from translate import Translator

translator = Translator(from_lang="ES", to_lang="EN")
translator_available = True

current_dir = os.getcwd()
path_file = current_dir.replace(r"parsers\santa_elena", r"files\santa_elena\\")

result = []


def run():
    check_available_translator()
    shops_links_d = get_all_shops()

    for shop, link in shops_links_d.items():
        get_info_by_url(shop=shop, url=link)

    result_path_file = path_file + r"result.txt"
    with open(result_path_file, "w", encoding="utf-8") as file:
        file.writelines(
            json.dumps(
                result,
                sort_keys=False,
                indent=4,
                ensure_ascii=False,
                separators=(',', ': ')
            )
        )


def check_available_translator():
    res = translator.translate("Dirección")
    if res.find("YOU USED ALL AVAILABLE FREE TRANSLATIONS FOR TODAY") != -1:
        global translator_available
        translator_available = False


def translate_str(text: str) -> str:
    if translator_available:
        return translator.translate(text)
    return text


def get_info_by_url(shop: str, url: str):
    shop = shop.strip()
    url = url.strip()

    response = requests.get(url)

    soup = BeautifulSoup(response.text, "lxml")
    divs = soup.find_all("div", class_="elementor-column-wrap elementor-element-populated")
    for div in divs:
        item = div.find("div", class_="elementor-widget-wrap")
        text_editor = item.find("div", attrs={"data-widget_type": "text-editor.default"})
        heading = item.find("div", attrs={"data-widget_type": "heading.default"})
        image = item.find("div", attrs={"data-widget_type": "image.default"})
        if text_editor and heading and image:
            info = {
                "name": None,
                "address": None,
                "latlon": None,
                "phones": None,
                "working_hours": None
            }

            heading = heading.find("div", class_="elementor-widget-container")
            heading = heading.find("h3")
            heading_text = heading.text
            info["name"] = heading_text

            text_editor = text_editor.find("div", class_="elementor-text-editor elementor-clearfix")
            ps = text_editor.find_all("p")
            h4s = text_editor.find_all("h4")

            phones_res = []
            div_h_default = soup.find("div", attrs={"data-widget_type": "html.default"})
            div_section = div_h_default.find("div", attrs={"id": "sectionA"})
            if div_section:
                phone_str = div_section.text.strip()
                phones_res.append(phone_str)

            w_hs = []
            for p in ps:
                w_hs.append(translate_str(p.text))
            for h4 in h4s:
                w_hs.append(translate_str(h4.text))
            w_hs_row = " ".join(w_hs)

            # need refactor
            if translator_available:
                address_index = w_hs_row.index("Address:")
                phone_index = w_hs_row.index("Phone:")

                if w_hs_row.find("Opening hours:") != -1:
                    w_h_index = w_hs_row.index("Opening hours:")
                else:
                    w_h_index = w_hs_row.index("Hours of operation:")

                address_str = w_hs_row[address_index + len("Address:"):phone_index]
                phone_str = w_hs_row[phone_index + len("Phone:"):w_h_index]

                w_h_str = w_hs_row[w_h_index + len("Opening hours:"):]
            else:
                address_index = w_hs_row.index("Dirección:")
                phone_index = w_hs_row.index("Teléfono:")

                if w_hs_row.find("Horario de atención:") != -1:
                    w_h_index = w_hs_row.index("Horario de atención:")
                else:
                    w_h_index = w_hs_row.index("Horas de operación:")

                address_str = w_hs_row[address_index + len("Dirección:"):phone_index]
                phone_str = w_hs_row[phone_index + len("Teléfono:"):w_h_index]

                w_h_str = w_hs_row[w_h_index + len("Horario de atención:"):]

            address_str = translate_str(address_str)
            info["address"] = f'{shop.split("en")[1]}, {address_str}'

            phone_str = translate_str(phone_str)
            phones_res.append(phone_str)
            info["phones"] = phones_res

            w_h_res = []
            for x in w_h_str.split("p.m"):
                if len(x) < 2:
                    continue
                w_hs_row = x.strip()
                w_hs_row = w_hs_row.replace(". ", "")

                w_h_res.append(w_hs_row)

            info["working_hours"] = w_h_res

            result.append(info)


def get_all_shops() -> dict:
    url = 'https://www.santaelena.com.co/'
    response = requests.get(url)

    soup = BeautifulSoup(response.text, "lxml")

    result_data = []
    result_dict = {}
    li_tags = soup.find("ul", attrs={"id": "menu-1-d0aa52e"})
    li_tags = li_tags.find("li", class_="menu-item menu-item-type-post_type menu-item-object-page "
                                        "menu-item-has-children menu-item-512").find("ul")
    li_tags = li_tags.find_all("li")
    for li in li_tags:
        li_el = li.next
        link = li_el.attrs.get("href")
        shop_name = li_el.text

        res_str = f"{shop_name}>{link}\n"
        result_data.append(res_str)
        result_dict.update({shop_name: link})

    shops_links_path_file = path_file + r"shops_links.txt"

    with open(shops_links_path_file, "w", encoding="utf-8") as file:
        file.writelines(result_data)

    return result_dict


run()
