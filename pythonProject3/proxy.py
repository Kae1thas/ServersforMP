import socket
import selectors
import types
import concurrent.futures
from urllib.parse import urlparse
import logging
import colorlog


# Настройки логгирования
handler = colorlog.StreamHandler()
handler.setFormatter(colorlog.ColoredFormatter(
    '%(log_color)s%(levelname)s:%(name)s:%(message)s',
    log_colors={
        'INFO': 'green',
    }
))
logger = colorlog.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Настройки
HOST = '127.0.0.1'
PORT = 25565
CACHE = {}

# Инициализация селектора
sel = selectors.DefaultSelector()

def accept(sock, mask):
    conn, addr = sock.accept()  # Принять новое соединение
    logger.info(f'Accepted connection from {addr}')
    conn.setblocking(False)
    data = types.SimpleNamespace(addr=addr, inb=b'', outb=b'')
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    sel.register(conn, events, data=data)

def service_connection(key, mask):
    sock = key.fileobj
    data = key.data
    if mask & selectors.EVENT_READ:
        recv_data = sock.recv(1024)  # Чтение данных от клиента
        if recv_data:
            data.inb += recv_data
            if b'\r\n\r\n' in data.inb:
                request_line = data.inb.split(b'\r\n')[0].decode()
                method, url, _ = request_line.split(' ')
                if method == 'GET':
                    parsed_url = urlparse(url)
                    cache_key = (method, url)
                    if cache_key in CACHE:
                        logger.info(f'Cache hit for {url}')
                        data.outb += CACHE[cache_key]
                    else:
                        logger.info(f'Cache miss for {url}')
                        target_host = parsed_url.hostname
                        target_port = parsed_url.port or 80
                        path = parsed_url.path
                        if parsed_url.query:
                            path += '?' + parsed_url.query
                        # Создание и отправка запроса к целевому серверу
                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as target_socket:
                            target_socket.connect((target_host, target_port))
                            target_socket.sendall(f'GET {path} HTTP/1.0\r\nHost: {target_host}\r\n\r\n'.encode())
                            response = b''
                            while True:
                                chunk = target_socket.recv(4096)
                                if not chunk:
                                    break
                                response += chunk
                            CACHE[cache_key] = response
                            data.outb += response
        else:
            logger.info('Closing connection to %s', data.addr)
            sel.unregister(sock)
            sock.close()
    if mask & selectors.EVENT_WRITE:
        if data.outb:
            sent = sock.send(data.outb)  # Отправка данных клиенту
            data.outb = data.outb[sent:]

def print_cache():
    logger.info("\nCurrent Cache Content:")
    for key, value in CACHE.items():
        logger.info(f'URL: {key[1]}')
        logger.info(f'Content: {value[:100]}...')  # Ограничим вывод 100 символами для читаемости
        logger.info('----------------------------')

def start_proxy(num_threads):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((HOST, PORT))
    sock.listen()
    sock.setblocking(False)
    sel.register(sock, selectors.EVENT_READ, data=None)

    logger.info(f'Serving on {(HOST, PORT)}')
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            while True:
                events = sel.select(timeout=None)
                for key, mask in events:
                    if key.data is None:
                        accept(key.fileobj, mask)
                    else:
                        executor.submit(service_connection, key, mask)
    except KeyboardInterrupt:
        logger.info('Caught keyboard interrupt, exiting')
    finally:
        print_cache()
        sel.close()

start_proxy(2)  # Задайте желаемое количество потоков здесь
