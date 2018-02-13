# -*- coding: utf-8 -*-

import json
import threading
import time
import socket_config

from socket_wrapper import *

heat_beat_interval = 20


class Client:
    clientSock = None
    port = 12354
    host = None

    recv_buffer_size = 4096

    __is_socket_alive = False

    heart_beat_thread = None
    send_msg_thread = None
    recv_msg_thread = None
    process_msg_thread = None

    __msg_to_send = []
    __chat_msg_received = []
    __sys_msg_received = []

    __data_buffer = ''
    __data_buf_Lock = None

    __msg_header_size = 13

    def __init__(self):
        self.host = socket_config.host_name
        self.port = socket_config.port
        self.clientSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__data_buf_Lock = threading.Lock()

    def connect_to_server(self):
        self.__is_socket_alive = socket_connection(self.clientSock, self.host, self.port)

        self.heart_beat_thread = threading.Thread(target=self.send_heart_beat_package)
        self.heart_beat_thread.setDaemon(True)
        self.heart_beat_thread.start()

        self.recv_msg_thread = threading.Thread(target=self.recv_msg)
        self.recv_msg_thread.setDaemon(True)
        self.recv_msg_thread.start()

        self.send_msg_thread = threading.Thread(target=self.send_msg)
        self.send_msg_thread.setDaemon(True)
        self.send_msg_thread.start()

        self.process_msg_thread = threading.Thread(target=self.read_msg_from_buffer)
        self.process_msg_thread.setDaemon(True)
        self.process_msg_thread.start()

        return self.__is_socket_alive

    def is_socket_alive(self):
        return self.__is_socket_alive

    def append_to_msg_sending_queue(self, msg):
        self.__msg_to_send.append(msg)

    def pop_chat_msg_from_queue(self):
        if len(self.__chat_msg_received) > 0:
            return self.__chat_msg_received.pop(0)
        else:
            return None

    def append_sys_msg(self, msg):
        # append sys msg to sys msg list
        self.__sys_msg_received.append(msg)

    def pop_sys_msg_from_queue(self):
        if len(self.__sys_msg_received) > 0:
            return self.__sys_msg_received.pop(0)
        else:
            return None

    def send_msg(self):
        while self.__is_socket_alive:
            if len(self.__msg_to_send) > 0:
                msg = self.__msg_to_send.pop(0)
                self.__safe_socket_send(msg)
            time.sleep(0.1)

    def recv_msg(self):
        # append received data to data buffer
        while self.__is_socket_alive:
            try:
                recved_data = self.clientSock.recv(self.recv_buffer_size)
            except socket.error as err:
                print "failed to receive data", err
                self.close_client()
                return
            else:
                if (not recved_data):
                    print "receive empty string, program terminated"
                    break

                while 1:
                    if self.__data_buf_Lock.acquire():
                        self.__data_buffer += recved_data
                        self.__data_buf_Lock.release()
                        break

    def read_msg_from_buffer(self):
        # process msg in data buffer
        # and distribute msg to chat msg list or sys msg list
        while self.__is_socket_alive:
            if len(self.__data_buffer) > 0:

                msg_start_index = self.__data_buffer.find('msgHeader')

                if msg_start_index == -1:
                    continue

                msg_header_end_index = msg_start_index + self.__msg_header_size
                msg_header = self.__data_buffer[msg_start_index:msg_header_end_index]
                head_pack = struct.unpack('!9sI', msg_header)
                msg_body_size = head_pack[1]
                msg_body_end_index = msg_header_end_index + msg_body_size
                msg_body = self.__data_buffer[msg_header_end_index: msg_body_end_index]

                print "recv msg:  ", msg_body

                self.__parse_received_data(msg_body)

                if self.__data_buf_Lock.acquire():
                    self.__data_buffer = self.__data_buffer[msg_start_index + self.__msg_header_size + msg_body_size:]
                    self.__data_buf_Lock.release()

    def __parse_received_data(self, msg):
        '''
        the protocol of msg we used here are as following:
        all the message are packed in a dict structure:

        message can be attributed as system message or chat message, which leads to the dict structure:
        1. {'SysMsg': {a:b}}:
            a field are used to identify the types of system msg, for instance: "SysLoginRequest"
            b field are usually the real msg that we want to send, it could be a str or dict, according to the type of a field
        2. {'ChatMsg': {a:b}}:
            a field here is to identify to whom the chat msg is to send:
                i.'toAll' means: we want to broadcast the msg
                ii.'toClient' means, it is a private msg
                iii.'toRoom' means: it is a room msg
            b field is the msg we want to send:
                for ii and iii case, b field has three sub fields, [x,y,z]
                    x is the sender, y is receiver, z is the message
                for i case, b field has two sub fields, [x,y]
                    x is the sender, y is the message
        '''
        try:
            data = json.loads(msg)
        except ValueError as e:
            print 'exception in loading json data', e
            print msg
        else:
            # print data
            for msg_type, msg_text in data.items():
                if msg_type == 'ChatMsg':
                    # msg_text will be a dict {'toAll': msg} or {'XXX': msg}
                    self.__chat_msg_received.append(msg_text)
                elif msg_type == 'SysMsg':
                    # msg_text will be a dict, like {'SysLoginRequestAck': 'xxx'} or {'allUsernames': {}}
                    self.__sys_msg_received.append(msg_text)

    def close_client(self):
        if self.__is_socket_alive:
            print 'close socket'
            self.__safe_socket_send("CLIENT_SHUTDOWN")
            self.clientSock.close()
            self.__is_socket_alive = False
        else:
            print 'socket has been closed already'

    def send_heart_beat_package(self):
        '''
        There are two benefits of sending heart beat package:
        1. the heart beat package will allow the server to be aware of whether the client is ALIVE or not
        2. the heart beat package also serve as PASSWORD to maintain a connection with the server,
            so that the connection which is NOT raised from our client program will be rejected(closed by the server)
        '''
        while self.__is_socket_alive:
            self.__safe_socket_send("-^-^-pyHB-^-^-")
            time.sleep(heat_beat_interval)

    def __safe_socket_send(self, msg):
        if not socket_send(self.clientSock, msg):
            self.__is_socket_alive = False
            self.close_client()


if __name__ == "__main__":
    client = Client()
