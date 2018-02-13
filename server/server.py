# -*- coding: utf-8 -*-

import datetime
import select
import sys
import threading
import traceback
import socket_config

from client_status import *
from socket_wrapper import *
from utils import *


class ServerEnd:
    server_socket = None
    port = 12354
    host = None

    recv_buffer_size = 4096

    # collection of all client sockets
    __client_sockets = []
    __sock_lock = None

    # store all user names and passwords
    # the KEY is username, the VALUE is a dict which has three fields:
    # 1. "PWD"      : password
    # 2. "lastLogin": last login time
    # 3. "totalTime": total online time
    __usr_database = {}

    # record whether user has logged in or not
    # this is NOT the same with the status of socket
    # the KEY is username, the VALUE is True or False
    __usr_login_or_logout = {}

    # associate username and socket
    # the KEY is a socket, the VALUE is corresponding username
    __socket_username_dict = {}

    # we apply a dict to manage the status of client sock
    # detecting the status of connected sock
    # the KEY is a socket, the VALUE is an object of ClientStatus
    # ClientStatus is created since the client is connected, not when logging
    __usr_status = {}

    # we have two sub thread:
    # 1. heart beat thread
    # 2. updating usr online time thread
    __sub_thread_alive = True

    # heart beat loop status and thread
    __hear_beat_thread = None

    # update usr online time thread
    __updating_user_online_time_thread = None

    # a dict for all available rooms
    # KEY is room name, VALUE is like {"admin": user_name, "sockets":[sock1, sock2, ...] }
    __room_list = {}

    def __init__(self):
        self.__client_sockets = []
        self.__sock_lock = threading.Lock()
        self.host = socket_config.host_name
        self.port = socket_config.port

        self.__load_user_data()

        self.__hear_beat_thread = threading.Thread(target=self.__detect_client_status)
        self.__hear_beat_thread.setDaemon(True)
        self.__hear_beat_thread.start()

        self.__updating_user_online_time_thread = threading.Thread(target=self.__update_clients_online_duration)
        self.__updating_user_online_time_thread.setDaemon(True)
        self.__updating_user_online_time_thread.start()

        self.__main_loop()

    # ******************** socket management method ********************
    def assign_host_address(self, host):
        self.host = host

    def assign_port(self, port):
        self.port = port

    def __init_socket(self):
        self.server_socket = socket_creation()
        socket_bind(self.server_socket, self.host, self.port)
        self.server_socket.setblocking(False)
        socket_listen(self.server_socket)

    def __close_server(self):
        print "close server !!"
        self.__sub_thread_alive = False
        self.__broadcast_server_sys_msg(self.__client_sockets, "SERVER_SHUTDOWN", '')
        self.server_socket.close()

    def __accept_new_client(self, sock):
        self.__usr_status[sock] = ClientStatus()
        self.__client_sockets.append(sock)
        print "new client connected ", self.__get_user_name(sock)
        # print "current sockets", self.__client_sockets

    def __close_dead_socket(self, sock):
        self.__sock_lock.acquire()

        user_name = self.__get_user_name(sock)
        print "client ", user_name, " disconnected"

        if user_name in self.__usr_login_or_logout:
            self.__usr_login_or_logout[user_name] = False

        self.__del_sock_from_room_list(sock)
        self.__update_user_online_time(sock)

        if sock in self.__usr_status:
            self.__usr_status[sock].client_logout()
            self.__usr_status.__delitem__(sock)

        if sock in self.__socket_username_dict:
            self.__socket_username_dict.__delitem__(sock)

        if sock in self.__client_sockets:
            self.__client_sockets.remove(sock)

        sock.close()
        self.__dump_user_data()
        self.__sock_lock.release()

    def __del_sock_from_room_list(self, sock):
        '''delete socket in room sockets lists'''

        # __roomList = {
        #            'room1':
        #                   {'admin':xx, 'sockets':[s1,s2,s3]},
        #            'room2':
        #                   {'admin':xx, 'sockets':[s1,s2,s3]}
        #           }

        for room_name in self.__room_list.keys():
            if sock in self.__room_list[room_name]['sockets']:
                self.__room_list[room_name]['sockets'].remove(sock)

    def __safe_socket_send(self, sock, msg):
        if self.__check_socket_is_alive(sock):
            if not socket_send(sock, msg):
                traceback.print_exc()
                self.__close_dead_socket(sock)

    def __check_socket_is_alive(self, sock):
        try:
            sock.sendall('*')
        except socket.error as e:
            print sock, 'is down', e
            self.__close_dead_socket(sock)
            return False
        else:
            return True

    # ************************* broadcast usr or system msg methods **************************

    def __broadcast_server_sys_msg(self, group, key, msg):
        '''
        send server system msg to all clients in group
        :param group: all the sockets
        :param key: key is the type of system msg, for example "SysLoginRequestAck"
        :param msg: msg we want to send
        :return:
        '''
        for sock in group:
            if sock != self.server_socket and type(sock) == socket._socketobject:
                self.__safe_socket_send(sock, package_sys_msg(key, msg))

    def __broadcast_client_chat_msg(self, group, msg_sock, msg):
        '''
        send chat msg from msgSock to other clients
        '''
        for sock in group:
            if sock != msg_sock and sock != self.server_socket and type(sock) == socket._socketobject:
                self.__safe_socket_send(sock, package_public_chat_msg(self.__get_user_name(msg_sock), msg))

    def __broadcast_server_chat_msg(self, group, msg):
        # send server msg to all clients
        for sock in group:
            if sock != self.server_socket and type(sock) == socket._socketobject:
                self.__safe_socket_send(sock, package_public_chat_msg('Server msg', msg))

    def __broadcast_client_sys_msg(self, group, msg_sock, key, msg):
        '''
        send msg from msgSock to other clients, if client want to broadcast a SYSTEM LEVEL msg
        for example, one client declaims that he is logging out
        '''
        for sock in group:
            if sock != msg_sock and sock != self.server_socket and type(sock) == socket._socketobject:
                self.__safe_socket_send(sock, package_sys_msg(key, msg))

    # ************************* two sub-thread methods **************************
    def __detect_client_status(self):
        '''
        detect heart beat signal from client
        '''
        while self.__sub_thread_alive:
            time.sleep(20)
            for sock, client in self.__usr_status.items():
                if client.is_client_offline():
                    print sock, "is OFFLINE"
                    self.__close_dead_socket(sock)

    def __update_clients_online_duration(self):
        '''
        update the online duration information of each client every 60 seconds
        '''
        while self.__sub_thread_alive:
            for sock in self.__usr_status.keys():
                # send client online information
                self.__send_client_online_duration_msg(sock)
            time.sleep(60)

    def __send_client_online_duration_msg(self, sock):
        if self.__usr_status[sock].client_has_login_or_not() and sock in self.__client_sockets:
            user_name = self.__get_user_name(sock)
            usr_data = self.__usr_database[user_name]

            last_online_time_str = datetime.datetime.fromtimestamp(usr_data['lastLogin']).strftime(
                "%Y-%m-%d-%H-%M")

            # historical online time + current online time
            total_time = usr_data['totalTime'] + self.__usr_status[sock].get_client_online_duration()
            total_time_str = convert_seconds_to_hms_fmt(total_time)
            time_msg = package_sys_msg("SysUsrOnlineDurationMsg", last_online_time_str + ";" + total_time_str)

            self.__safe_socket_send(sock, time_msg.encode('utf-8'))

    def __update_user_online_time(self, sock):
        user_name = self.__get_user_name(sock)
        if sock in self.__usr_status and self.__usr_status[sock].client_has_login_or_not():
            self.__usr_database[user_name]['lastLogin'] = self.__usr_status[sock].get_client_login_time_stamp()
            self.__usr_database[user_name]['totalTime'] += self.__usr_status[sock].get_client_online_duration()

    # ********************** process client request *************************

    def __analyse_received_data(self, sock, received_data):
        '''
        This method process the received data from socket

        There are four types of received data:
        1. received_data == '':
            when the client is closed unexpectedly, server will receive lots of empty string ''
            we take advantage of it, use it as a sign that client is closed.
        2. received_data == "CLIENT_SHUTDOWN"
            this message means the client is closed manually
        3. received_data == "-^-^-pyHB-^-^-"
            this is the heart beat message
        4. other message needs to be parsed with self.__parse_received_data() method

        :param sock: the socket from which we get the received data
        :param received_data: received data

        '''
        # print "Received raw data", received_data
        if (not received_data) or received_data == "CLIENT_SHUTDOWN":
            try:
                self.__broadcast_client_sys_msg(self.__client_sockets, sock, 'SysUsrLogOut',
                                                self.__get_user_name(sock))
                self.__broadcast_client_chat_msg(self.__client_sockets, sock, "client disconnected\n")
                self.__close_dead_socket(sock)
            except Exception as e:
                print e
        elif received_data == "-^-^-pyHB-^-^-":
            self.__usr_status[sock].update_client_online_status()
        else:
            # parse received_data
            self.__parse_received_data(sock, received_data)

    def __parse_received_data(self, sock, msg):
        '''
        This method parse the received message.
        We will firstly parse the received json data, and return
        the corresponding message

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
            b field contains the following things:
                for ii and iii case, b field has three sub fields, [x,y,z]
                    x is the sender, y is receiver, z is the message
                for i case, b field has two sub fields, [x,y]
                    x is the sender, y is the message

        :param sock: the socket from which we get msg
        :param msg: received raw message
        '''

        print "client msg: ", msg

        data = ''
        try:
            data = json.loads(msg)
        except Exception as e:
            print 'exception in loading json data: ', e
        finally:
            if type(data) == dict:
                for msg_type, msg_text in data.items():
                    if msg_type == 'ChatMsg':
                        # msg_text will be a dict {'toAll': [sender,msg]} or {'XXX': msg}
                        self.__process_chat_msg(sock, msg_text, msg)

                    elif msg_type == 'SysMsg':
                        self.__process_sys_msg(sock, msg_text)

    def __process_chat_msg(self, sock, msg, received_data):
        '''
        process chat msg:
        msg will be like
        1. {'toAll'     :[sender, 'abc']}
        2. {'toClient'  :[sender, receiver,'abc']}
        3. {'toRoom'    :[sender, room_name,'abc']}
        '''

        # k is msg type, v is msg text
        for msg_id, msg_text in msg.items():
            if msg_id == "toAll":
                sender = msg_text[0]
                recv_msg = msg_text[1]
                # process lobby chat msg
                # print 'msg to all from :', sender, recv_msg
                self.__broadcast_client_chat_msg(self.__client_sockets, sock, recv_msg)
            elif msg_id == 'toClient':
                # process PRIVATE chat msg
                # forward the raw received data to corresponding socket
                receiver = msg_text[1]
                receiver_sock = self.__get_sock_with_username(receiver)
                # send private chat msg
                if receiver_sock is not None:
                    # print receiver_sock, received_data
                    self.__safe_socket_send(receiver_sock, received_data)
            elif msg_id == 'toRoom':
                # process ROOM chat msg
                # msg_text will be like [sender, room_name,'abc']
                room_name = msg_text[1]
                room_sockets = self.__room_list[room_name]['sockets']

                # print 'to room msg, sockets: ', room_sockets
                if sock in room_sockets:
                    for receiver_sock in room_sockets:
                        if receiver_sock != sock:
                            # print receiver_sock, received_data
                            self.__safe_socket_send(receiver_sock, received_data)

    def __process_sys_msg(self, sock, msg):
        # msg will be a dict, like {'SysLoginRequest': {}} or {'SysRegisterRequest': {}}
        for msg_id, msg_text in msg.items():

            reply = ''

            if msg_id == 'SysLoginRequest':
                # case: {'SysLoginRequest': {user_name:user_pwd}}
                user_name = msg_text.keys()[0]
                user_pwd = msg_text.values()[0]
                reply = self.__usr_login(sock, user_name, user_pwd)

            # confirm a login like what TCP does
            if msg_id == 'SysLoginConfirmed':
                user_name = msg_text
                self.__confirm_login(sock, user_name)
                self.__send_client_online_duration_msg(sock)
                continue

            if msg_id == 'SysRegisterRequest':
                # case: {'SysRegisterRequest': {user_name:user_pwd}}
                user_name = msg_text.keys()[0]
                user_pwd = msg_text.values()[0]
                reply = self.__register_new_user(user_name, user_pwd)

            if msg_id == 'SysAllOnlineClientsRequest':
                # case : {'SysAllOnlineClientsRequest': ''}
                reply = self.__reply_all_online_username()

            if msg_id == 'SysCreateRoomRequest':
                # case : {'SysCreateRoomRequest': {"admin": "1", "roomName": "aaa"}}
                reply = self.__create_room(sock, msg_text)

            if msg_id == 'SysEnterRoomRequest':
                # case : {'SysEnterRoomRequest': {"roomName": "aaa"}}
                reply = self.__enter_room(sock, msg_text)

            if msg_id == 'SysRoomListRequest':
                # case : {'SysEnterRoomRequest': {"roomName": "aaa"}}
                reply = self.__query_room_list()

            if msg_id == 'SysExitRoomRequest':
                reply = self.__client_exit_room(sock, msg_text)

            if msg_id == 'SysRoomUserNameRequest':
                pass

            if reply:
                self.__safe_socket_send(sock, reply)
                print "sys reply : ", reply

    def __get_sock_with_username(self, user_name):
        sock = None
        for so, user in self.__socket_username_dict.items():
            if user == user_name:
                sock = so
                break
        return sock

    def __reply_all_online_username(self):
        try:
            user_name = []
            reply = {"allOnlineUsernames": user_name}

            for user, status in self.__usr_login_or_logout.items():
                if status:
                    reply['allOnlineUsernames'].append(user)

            return package_sys_msg("SysAllOnlineClientsAck", reply)
        except Exception as e:
            print "exception in replying all online username", e

    # *********************** process room request ********************

    def __create_room(self, sock, msg):
        # msg is like {"admin": "1", "roomName": "aaa"}
        reply = {}
        room_name = msg['roomName']

        if room_name in self.__room_list:
            reply[room_name] = "Room already exists"
            return package_sys_msg('SysCreateRoomAck', reply)

        self.__room_list[room_name] = {'admin': msg['admin'], 'sockets': [sock]}

        reply[room_name] = "Successful Room Creation"
        return package_sys_msg('SysCreateRoomAck', reply)

    def __enter_room(self, sock, msg):
        # msg is like {"roomName": "aaa"}
        reply = {}
        room_name = msg['roomName']

        if room_name in self.__room_list:
            if sock not in self.__room_list[room_name]['sockets']:
                self.__room_list[room_name]['sockets'].append(sock)
                reply[room_name] = "Successfully Enter The Room"
            else:
                reply[room_name] = "Already In The Room"
            return package_sys_msg('SysEnterRoomAck', reply)

        reply[room_name] = "Room Not Exists"
        return package_sys_msg('SysEnterRoomAck', reply)

    def __client_exit_room(self, sock, msg):

        key = "SysExitRoomAck"
        room_name = msg['roomName']

        if sock in self.__room_list[room_name]['sockets']:
            self.__room_list[room_name]['sockets'].remove(sock)
            value = {room_name: "Exit Room"}
        else:
            value = {room_name: "Failed To Exit Room"}

        return package_sys_msg(key, value)

    def __query_room_list(self):
        key = "SysRoomListAck"
        value = self.__room_list.keys()
        return package_sys_msg(key, value)

    # *********************** user login and registration ********************
    def __usr_login(self, sock, user_name, user_pwd):
        '''
        process user login request
        and make a reply
        '''
        if user_name not in self.__usr_database:
            # print "account not exists"
            return package_sys_msg('SysLoginAck', "Account Not exists")

        if user_name in self.__usr_login_or_logout and self.__usr_login_or_logout[user_name]:
            # print "usr is already online"
            return package_sys_msg('SysLoginAck', "This User is already online")

        if self.__usr_database[user_name]['pwd'] == user_pwd:
            return package_sys_msg('SysLoginAck', "Successful login")
        else:
            return package_sys_msg('SysLoginAck', "Invalid login")

    def __confirm_login(self, sock, user_name):
        self.__socket_username_dict[sock] = user_name
        self.__usr_login_or_logout[user_name] = True
        self.__usr_status[sock].client_login()
        self.__broadcast_client_sys_msg(self.__client_sockets, sock, "SysUsrLogin", user_name)

    def __register_new_user(self, user_name, user_pwd):
        '''
        process user register request
        and make a reply
        '''
        if self.__usr_database.has_key(user_name):
            # print "Account Already Registered"
            return package_sys_msg('SysRegisterAck', "Account has already been registered")

        self.__usr_database[user_name] = {'pwd': user_pwd, 'lastLogin': time.time(), 'totalTime': 0.0}
        self.__dump_user_data()
        return package_sys_msg('SysRegisterAck', "Successful registration")

    def __get_user_name(self, sock):
        if self.__socket_username_dict.has_key(sock):
            return self.__socket_username_dict[sock]
        else:
            try:
                name = str(sock.getpeername())
            except BaseException:
                return ''
            else:
                return name

    def __dump_user_data(self):
        data = json.dumps(self.__usr_database)
        try:
            f = open('usrdata.dat', 'w')
            f.write(data.encode('utf-8'))
            f.close()
        except IOError as e:
            print "Could not dump data"

    def __load_user_data(self):
        try:
            f = open('usrdata.dat', 'r')
            data = f.read().decode('utf-8')
            if data:
                self.__usr_database = json.loads(data)
            else:
                print "invalid usrdata.dat"
            f.close()
        except IOError as e:
            print "Could not open or find 'usrdata.dat' file"
        else:
            for k in self.__usr_database.keys():
                self.__usr_login_or_logout[k] = False

    # ***************************** main loop of server program *********************
    def __main_loop(self):

        self.__init_socket()
        quit_program = False
        try:
            while not quit_program:

                sock_list = self.__client_sockets + [self.server_socket]

                try:
                    read_list, write_list, error_list = select.select(sock_list, [], sock_list)
                except select.error as err:
                    print 'socket select error, some clients might be offline', err

                try:
                    for sock in error_list:
                        print "socket error", sock
                        self.__close_dead_socket(sock)

                    for sock in read_list:
                        if sock == self.server_socket:
                            # new client
                            new_client, new_addr = socket_accept(sock)
                            self.__accept_new_client(new_client)
                        else:
                            if type(sock) == socket._socketobject:
                                # msg received from client
                                try:
                                    received_data = socket_recv(sock, self.recv_buffer_size)
                                except socket.error as err:
                                    print "failed to receive data, close invalid socket, then"
                                    self.__close_dead_socket(sock)
                                else:
                                    self.__analyse_received_data(sock, received_data)

                except Exception as e:
                    print 'Find Exception', e

                finally:
                    if quit_program:
                        self.__close_server()
                        break

        except KeyboardInterrupt as e:
            print 'Find KeyboardInterrupt', e

        finally:
            self.__close_server()
            print "end of server program"


if __name__ == "__main__":

    server = ServerEnd()
