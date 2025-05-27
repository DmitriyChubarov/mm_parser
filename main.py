import requests
import json
import os
from urllib.parse import urlencode, quote
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import threading
import http.client

api_key = 'apikey'
host = '127.0.0.1'
chrome_driver_path = '/Users/dmitrij/Documents/Python/chromedriver_mac64/chromedriver'
output_path = os.path.expanduser('~/Desktop/results.txt')
lock = threading.Lock()


def get_debugger_port(profile_id, config):
    query = urlencode({
        'x-api-key': api_key,
        'config': quote(json.dumps(config))
    })
    url = f'http://{host}:8848/devtool/launch/{profile_id}?{query}'
    response = requests.get(url)
    data = response.json()
    if 'data' not in data or data['data'] is None:
        raise Exception(f"Failed to get debugger port: {data.get('msg', 'No message')}")
    port = data['data']['port']
    return port

def stop_browser(port):
    conn = http.client.HTTPConnection(host, 8848)
    payload = ''
    headers = {
        'User-Agent': 'Apidog/1.0.0 (https://apidog.com)',
        'x-api-key': api_key
    }
    conn.request("GET", f"/api/agent/browser/stop/{port}", payload, headers)
    res = conn.getresponse()
    data = res.read()

def exec_selenium(debugger_address, profile_name):
    options = Options()
    options.add_experimental_option("debuggerAddress", debugger_address)
    options.add_argument('--headless')
    service = ChromeService(executable_path=chrome_driver_path)
    driver = webdriver.Chrome(service=service, options=options)
    result = ""
    try:
        driver.get("https://megamarket.ru/personal/promo-codes")
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        empty_account_title = soup.find('h2', class_='personal-empty-promo-codes__title')
        bonus_amount = soup.find('div', class_='header-profile-actions-balance__bonus money-bonus xl money-bonus_loyalty header-profile-actions-balance__bonus_xl')
        bonus_text = bonus_amount.text.strip() if bonus_amount else "нет данных"

        if empty_account_title and "пустой акк" in empty_account_title.text.lower():
            result = f"{profile_name} - пустой акк\n"
        else:
            promo_blocks = soup.find_all('div', class_='personal-promo-code-new')
            if promo_blocks:
                for promo_block in promo_blocks:
                    title = promo_block.find('h2', class_='personal-promo-code-new__title')
                    date = promo_block.find('p', class_='personal-promo-code-new__date')
                    button_content = promo_block.find('div', class_='c-button__content')

                    title_text = title.text.strip() if title else "нет данных"
                    date_text = date.text.strip() if date else "нет данных"
                    button_text = button_content.text.strip() if button_content else "нет данных"

                    result += f"{profile_name} - | {title_text} | {date_text} | {button_text} | {bonus_text} |\n"
            else:
                result = f"{profile_name} - Промокодов нет | {bonus_text} |\n"
    finally:
        driver.quit()
        result += "\n"  # добавляем пробел после каждого аккаунта

    return result



def process_profile(profile):
    profile_id = profile['profileId']
    profile_name = profile['name']
    config = {"headless": True, "autoClose": True}
    result = ""
    try:
        port = get_debugger_port(profile_id, config)
        debugger_address = f"{host}:{port}"
        result = exec_selenium(debugger_address, profile_name)
        print(result)  # Вывод результата
    except Exception as e:
        result = f"Error processing profile {profile_id}: {str(e)}\n"
        print(result)  # Вывод ошибки
    finally:
        stop_browser(port)
        with lock:
            with open(output_path, 'a') as file:
                file.write(result)

def main():
        url = "http://localhost:8848/api/agent/browser/profiles/status"
        response = requests.get(url, headers={'x-api-key': api_key})
        data = response.json()

        if 'data' in data:
            with ThreadPoolExecutor(max_workers=5) as executor:
                executor.map(process_profile, data['data'])
        else:
            with open(output_path, 'a') as file:
                file.write("No profiles found or incorrect key\n")

if __name__ == "__main__":

        open(output_path, 'w').close()
        main()
