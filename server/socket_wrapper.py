
import socket
import struct


def socket_creation():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except socket.error as err:
        print "failed to create socket: ", err
    else:
        return sock


def socket_bind(sock, host, port):
    try:
        sock.bind((host, port))
    except socket.error as err:
        print "failed to bind address: ", err


def socket_listen(sock):
    try:
        sock.listen(5)
    except socket.error as err:
        print "failed to listen socket: ", err


def socket_accept(sock):
    try:
        s, a = sock.accept()
    except socket.error as err:
        print "failed to accept client: ", err
    else:
        return s, a


def socket_connection(sock, host, port):
    try:
        sock.connect((host, port))
    except socket.error as err:
        print "failed to connect to server: ", err
        return False
    else:
        return True


def socket_send(sock, data):
    '''
    :return: we return a boolean type of data to indicate whether there is
    an expection when sending the data
    '''
    # we add a header for each msg, which contains the length of each data
    head = ['msgHeader', len(data)]
    header_pack = struct.pack('!9sI', *head)

    data = header_pack + data.encode('utf-8')
    # print data
    try:
        sock.sendall(data)
    except socket.error as err:
        print sock, "failed to send data: ", err
        return False
    else:
        return True


data_buffer = ''
header_size = 13


def socket_recv(sock, recv_buff_size):
    ''' socket recv except of this method is caught outside '''
    global data_buffer

    while 1:

        data = sock.recv(recv_buff_size)

        # client never send ''!
        # this will happen only when the client is terminated unexpectedly
        if not data:
            # print 'receive empty string!'
            return data

        data_buffer = data_buffer + data

        while 1:
            if len(data_buffer) < header_size:
                break

            header_pack = struct.unpack('!9sI', data_buffer[:header_size])
            msg_body_size = header_pack[1]

            if len(data_buffer) < header_size + msg_body_size:
                break

            msg = data_buffer[header_size:header_size + msg_body_size]

            data_buffer = data_buffer[header_size + msg_body_size:]

            return msg

