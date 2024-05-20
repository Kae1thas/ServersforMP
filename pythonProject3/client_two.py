import socket
import selectors
import types

sel = selectors.DefaultSelector()

def start_connections(host, port, num_conns):
    server_addr = (host, port)
    for i in range(num_conns):
        conn_id = i + 1
        print(f'Запуск соединения от второго клиента {conn_id} к {server_addr}')
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(False)
        sock.connect_ex(server_addr)
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        data = types.SimpleNamespace(connid=conn_id, msg_total=0, recv_total=0, messages=[], outb=b'')
        sel.register(sock, events, data=data)

def service_connection(key, mask):
    sock = key.fileobj
    data = key.data
    if mask & selectors.EVENT_READ:
        recv_data = sock.recv(1024)
        if recv_data:
            print(f'Получено {recv_data} от соединения {data.connid}')
            data.recv_total += len(recv_data)
        if not recv_data or data.recv_total == data.msg_total:
            print(f'Закрытие соединения {data.connid}')
            sel.unregister(sock)
            sock.close()
    if mask & selectors.EVENT_WRITE:
        if not data.outb and data.messages:
            data.outb = data.messages.pop(0)
        if data.outb:
            print(f'Отправка {data.outb} к соединению {data.connid}')
            sent = sock.send(data.outb)
            data.outb = data.outb[sent:]

if __name__ == '__main__':
    host = 'localhost'
    port = 9090
    num_conns = 10  # Количество соединений, которые вы хотите установить

    start_connections(host, port, num_conns)

    try:
        while True:
            events = sel.select(timeout=1)
            if events:
                for key, mask in events:
                    service_connection(key, mask)
            if not sel.get_map():
                break
    except KeyboardInterrupt:
        print('Клиент остановлен')
    finally:
        sel.close()
