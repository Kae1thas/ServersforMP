import socket
import sys
import threading
import queue

# Очередь для передачи данных между потоками
data_queue = queue.Queue()
scroll_event = threading.Event()
program_running = threading.Event()

def http_get(url):
    # Парсим URL для получения хоста и пути
    if not url.startswith("http://"):
        print("URL должен начинаться с http://")
        return
    url = url[7:]  # Убираем "http://"
    if '/' in url:
        host, path = url.split("/", 1)
        path = "/" + path
    else:
        host = url
        path = "/"

    # Создаем сокет и подключаемся к серверу
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, 80))
        request = f"GET {path} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n"
        s.send(request.encode())

        # Читаем данные из сокета и помещаем их в очередь
        while True:
            data = s.recv(4096)
            if not data:
                break
            data_queue.put(data)
        data_queue.put(None)  # Сигнализируем о завершении данных


def user_interaction():
    while program_running.is_set():
        scroll_event.wait()  # Ждем пока основной поток попросит нас о вводе
        scroll_event.clear()  # Сбрасываем событие после его обработки
        while program_running.is_set():
            command = input("Type 'next' to scroll down: ").strip().lower()
            if command == 'next':
                print("Ввод успешен.")
                continue_output.set()
                break
            else:
                print("Ошибка: Неверная команда. Пожалуйста, введите 'next' для продолжения.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python server.py <URL>")
        sys.exit(1)

    program_running.set()

    # Запускаем потоки для HTTP-запроса и взаимодействия с пользователем
    http_thread = threading.Thread(target=http_get, args=(sys.argv[1],))
    input_thread = threading.Thread(target=user_interaction)
    http_thread.start()
    input_thread.start()

    # Основной поток будет обрабатывать вывод данных
    lines_printed = 0
    buffer = b""
    continue_output = threading.Event()

    while True:
        data = data_queue.get()
        if data is None:
            break
        buffer += data
        lines = buffer.split(b"\n")
        buffer = lines.pop()

        for line in lines:
            print(line.decode(errors='ignore'))
            lines_printed += 1
            if lines_printed >= 25:
                scroll_event.set()  # Уведомляем поток ввода пользователя о необходимости продолжения
                continue_output.wait()  # Ждем команды от пользователя
                continue_output.clear()
                lines_printed = 0

    # Завершаем работу программы
    program_running.clear()
    scroll_event.set()  # Уведомляем поток ввода пользователя о завершении

    # Ждем завершения потоков
    http_thread.join()
    input_thread.join()

    print("Все данные были успешно выведены. Программа завершена.")
    sys.exit(0)
