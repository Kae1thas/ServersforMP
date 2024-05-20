import requests
import concurrent.futures

def send_request(url):
    response = requests.get(url)
    print(response.text)

urls = ['http://127.0.0.1:25565'] * 1  # список URL для запросов
with concurrent.futures.ThreadPoolExecutor() as executor:
    executor.map(send_request, urls)
