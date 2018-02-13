
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
        sock.bind((host,port))
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
    we add a header for each msg, which contains the length of each data

    :return: we return a boolean type of data to indicate whether there is
        an expection when sending the data
    '''
    head = ['msgHeader', len(data)]
    head_pack = struct.pack('!9sI', *head)

    data = head_pack + data.encode('utf-8')

    try:
        sock.sendall(data)
    except socket.error as err:
        print "failed to send data: ", err
        return False
    else:
        return True


dataBuffer = ''
headerSize = 13


def socket_recv(sock, recv_buffer_size):
    ''' socket recv except of this method is caught outside '''
    # in client, we actually did not use this to receive data
    global dataBuffer

    while 1:
        data = sock.recv(recv_buffer_size)

        # client never send ''!
        # this will happen only when the client is terminated unexpectedly
        if not data:
            # print 'receive empty string!'
            return data

        dataBuffer = dataBuffer + data

        while 1:
            if len(dataBuffer) < headerSize:
                print "data less is than header"
                break

            head_pack = struct.unpack('!9sI', dataBuffer[:headerSize])
            msg_body_size = head_pack[1]

            if len(dataBuffer) < headerSize + msg_body_size:
                print "data less is than whole msg"
                break

            msg = dataBuffer[headerSize:headerSize + msg_body_size]
            dataBuffer = dataBuffer[headerSize + msg_body_size:]
            return msg

