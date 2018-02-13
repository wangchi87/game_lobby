# -*- coding: UTF-8 -*-

import signal

from client_socket import *
from chat_room import *


# login window
class LoginWindow(Toplevel):
    '''
    this class is used to create a login window
    '''

    __client_sock = None
    mainFrm = None
    __user_name = None

    def __init__(self, main_frm, client_sock):
        Toplevel.__init__(self)
        self.mainFrm = main_frm
        self.configure_GUI()

        self.__client_sock = client_sock
        self.protocol('WM_DELETE_WINDOW', self.close_dialog)

    def configure_GUI(self):
        self.title(u'登录窗口')
        logFrmPos = '%dx%d+%d+%d' % (325, 330, (1500 - 400) / 2, (900 - 300) / 2)
        self.geometry(logFrmPos)
        self.resizable(width=True, height=True)

        self.log_frame = Frame(self)
        self.log_frame_left = Frame(self, width=70, height=330)
        self.log_frame_right = Frame(self, width=70, height=330)
        self.log_frame_left.grid(row=0, column=0)
        self.log_frame.grid(row=0, column=1)
        self.log_frame_right.grid(row=0, column=2)
        # self.logFrm.place(x=0, y=0, width=250, height=330)

        self.log_label_caption = Label(self.log_frame, text=u'登录窗口')

        self.log_label_username = Label(self.log_frame, text=u'用户名')
        self.log_label_password = Label(self.log_frame, text=u'密码')
        self.log_label_info = Label(self.log_frame)

        self.log_entry_username = Entry(self.log_frame, text=u'netease1')
        self.log_entry_password = Entry(self.log_frame, text=u'1234', show='*')

        self.log_button_enter = Button(self.log_frame, text=u'登录', command=self.enter_button_cmd)
        self.log_button_register = Button(self.log_frame, text=u'注册', command=self.register_button_cmd)

        self.log_label_caption.pack(pady=15)
        self.log_label_username.pack(pady=5)
        self.log_entry_username.pack(pady=5)
        self.log_label_password.pack(pady=5)
        self.log_entry_password.pack(pady=5)
        self.log_label_info.pack(pady=5)
        self.log_button_enter.pack(pady=5)
        self.log_button_register.pack(pady=5)

    def try_login(self):

        self.log_button_enter['state'] = 'disabled'

        if self.mainFrm.has_already_logged_in():
            print "already logged in"
            return False

        self.__user_name = self.log_entry_username.get()
        password = self.log_entry_password.get()

        jstr = package_sys_msg('SysLoginRequest', {self.__user_name: password})
        self.__client_sock.append_to_msg_sending_queue(jstr)

        # wait for system login msg replied from server
        attempt = 0

        start_time = time.time()
        while 1:
            if time.time() - start_time > 10:
                self.log_label_info['text'] = "Failed to login, please try again"
                self.log_button_enter['state'] = 'normal'
                if attempt < 3:
                    attempt += 1
                    self.__client_sock.append_to_msg_sending_queue(jstr)
                else:
                    return False

            sys_msg = self.__client_sock.pop_sys_msg_from_queue()

            # sys_msg is something like {"SysLoginAck": "Successful login"}
            if sys_msg is None:
                time.sleep(0.002)
            elif sys_msg.keys()[0] == 'SysLoginAck':
                break
            else:
                self.__client_sock.append_sys_msg(sys_msg)

        if sys_msg is not None:
            if sys_msg.values()[0] == 'Successful login':
                jstr = package_sys_msg('SysLoginConfirmed', self.__user_name)
                self.__client_sock.append_to_msg_sending_queue(jstr)
                self.mainFrm.user_logged_in()
                return True
            else:
                self.log_label_info['text'] = sys_msg.values()[0]
            self.log_button_enter['state'] = 'normal'
            return False

    def enter_button_cmd(self):
        if self.try_login():
            self.destroy()
            self.mainFrm.deiconify()
            self.mainFrm.set_user_name(self.__user_name)

            self.mainFrm.query_all_online_clients()

    def register_button_cmd(self):
        self.log_button_register['state'] = 'disabled'

        if self.mainFrm.has_already_logged_in():
            self.log_button_register['state'] = 'normal'
            return False

        self.__user_name = self.log_entry_username.get()
        password = self.log_entry_password.get()

        jstr = package_sys_msg('SysRegisterRequest', {self.__user_name: password})
        self.__client_sock.append_to_msg_sending_queue(jstr)

        # wait for system registration reply msg from server
        start_time = time.time()
        while 1:
            if time.time() - start_time > 120:
                self.log_label_info['text'] = "Failed to register, please try again"
                self.log_button_register['state'] = 'normal'
                return

            sys_msg = self.__client_sock.pop_sys_msg_from_queue()

            # sys_msg is something like {"SysRegisterAck": "Successful registration"}
            if sys_msg == None:
                time.sleep(0.2)
            elif sys_msg.keys()[0] == 'SysRegisterAck':
                break
            else:
                self.__client_sock.append_sys_msg(sys_msg)
                time.sleep(0.2)

        if sys_msg is not None:
            if sys_msg.values()[0] == 'Successful registration':
                self.log_label_info['text'] = sys_msg.values()[0]
                self.log_button_register['state'] = 'normal'
                return True
            else:
                self.log_label_info['text'] = sys_msg.values()[0]
            self.log_button_register['state'] = 'normal'
            return False

    def close_dialog(self):
        self.__client_sock.close_client()
        self.mainFrm.destroy()


class Dialog(Tk):
    __user_name = 'username'
    __login_window = None
    __client_sock = None

    __logged_in = False

    # roomLists maintain the rooms the client are in or created
    # key is room name, value is the handle of room object
    __room_list = {}

    __create_room_window = None
    __enter_room_window = None

    def __init__(self):
        Tk.__init__(self)
        self.title(u"聊天大厅")
        self['background'] = 'grey'
        self.configure_GUI()
        self.withdraw()
        self.protocol('WM_DELETE_WINDOW', self.close_dialog)

        self.__connect()

        self.after(100, self.__process_received_msg)

        if self.__client_sock.is_socket_alive():
            self.__login_window = LoginWindow(self, self.__client_sock)
        else:
            print 'failed to connect server'
            sys.exit(1)

        self.mainloop()

    def has_already_logged_in(self):
        return self.__logged_in

    def user_logged_in(self):
        self.__logged_in = True

    def user_logged_out(self):
        self.__logged_in = False

    def get_user_name(self):
        return self.__user_name

    def __connect(self):
        self.__client_sock = Client()
        self.__client_sock.connect_to_server()

    def set_user_name(self, user_name):
        self.__user_name = user_name
        self.label_username['text'] = user_name

    def __send_msg_btn_cmd(self):
        usr_msg = self.text_user_msg.get('0.0', END)
        self.__display_new_msg(self.__user_name, usr_msg, 'userColor')
        self.text_user_msg.delete('0.0', END)
        data = package_public_chat_msg(self.__user_name, usr_msg)
        self.__client_sock.append_to_msg_sending_queue(data)

    def close_dialog(self):
        self.__client_sock.close_client()
        self.destroy()

    def __process_received_msg(self):
        self.__process_chat_msg()
        self.__process_sys_msg()
        self.after(100, self.__process_received_msg)

    def __process_chat_msg(self):
        if self.__client_sock.is_socket_alive() and self.has_already_logged_in():
            msg_dict = self.__client_sock.pop_chat_msg_from_queue()
            if msg_dict is not None:
                # print msg_dict
                for msg_id, msg_text in msg_dict.items():

                    # msg_id is the msg type: 'toAll', 'toClient' or 'toRoom'
                    if msg_id == 'toAll':
                        # msg_text is like [sender, msg]
                        usr = msg_text[0]
                        usr_msg = msg_text[1]
                        self.__display_new_msg(usr, usr_msg, 'userColor')

                    elif msg_id == 'toClient' and msg_text[1] == self.__user_name:
                        # msg_text is like [sender, receiver, msg]
                        sender = msg_text[0]
                        prvt_msg = msg_text[2]
                        self.__display_new_msg(sender + u" 发来的私信 ", prvt_msg, "privateChatColor")

                    elif msg_id == 'toRoom':
                        sender = msg_text[0]
                        room_name = msg_text[1]
                        room_msg = msg_text[2]

                        room_win = self.__room_list[room_name]
                        room_win.display_new_msg(sender, room_msg)

    def __display_new_msg(self, user_name, msg, config=''):
        # append msg to list component
        self.text_msg_list['state'] = 'normal'
        msg_time = time.strftime(" %Y-%m-%d %H:%M:%S", time.localtime()) + '\n'
        self.text_msg_list.insert(END, user_name + ': ' + msg_time + msg + '\n', config)
        self.text_msg_list['state'] = 'disabled'

    def query_all_online_clients(self):
        key = "SysAllOnlineClientsRequest"
        data = package_sys_msg(key, '')
        self.__client_sock.append_to_msg_sending_queue(data)

    def __process_sys_msg(self):
        if self.__client_sock.is_socket_alive() and self.has_already_logged_in():
            sys_msg = self.__client_sock.pop_sys_msg_from_queue()
            if sys_msg:
                self.__analyse_sys_msg(sys_msg)

    def __analyse_sys_msg(self, sys_msg):
        # print 'sysMsg: ', sysMsg
        for msg_id, msg_text in sys_msg.items():
            if msg_id == 'SysUsrOnlineDurationMsg':
                self.__set_usr_online_time(msg_text)

            if msg_id == 'SysAllOnlineClientsAck':
                # case: {'allOnlineUsernames': ['usr1', 'usr5', 'usr4']}
                if msg_text.keys()[0] == 'allOnlineUsernames':
                    all_current_users = self.listbox_user_list.get(0, self.listbox_user_list.size())
                    for e in msg_text.values()[0]:
                        if e != self.__user_name and e not in all_current_users:
                            self.listbox_user_list.insert(END, e)

            # other user login
            if msg_id == 'SysUsrLogin' and msg_text != self.__user_name:
                # print 'SysUsrLogin', self.userList.size(), msg_text
                all_current_users = self.listbox_user_list.get(0, self.listbox_user_list.size())
                if msg_text not in all_current_users:
                    self.listbox_user_list.insert(END, msg_text)

            # other user log out
            if msg_id == 'SysUsrLogOut' and msg_text != self.__user_name:
                for i in range(0, self.listbox_user_list.size()):
                    if msg_text == self.listbox_user_list.get(i):
                        self.listbox_user_list.delete(i)

            if msg_id == "SysCreateRoomAck":
                room_name = msg_text.keys()[0]
                msg = msg_text.values()[0]

                self.__create_room_window.withdraw()
                if msg == 'Successful Room Creation':
                    self.__room_list[room_name].show_room()
                elif msg == 'Room already exists':
                    self.__room_list[room_name].show_room()

            if msg_id == 'SysEnterRoomAck':
                room_name = msg_text.keys()[0]
                msg = msg_text.values()[0]
                # print 'room list', self.__roomLists
                self.__enter_room_window.withdraw()
                if msg == 'Successfully Enter The Room':
                    self.__room_list[room_name].show_room()
                elif msg == 'Already In The Room':
                    self.__room_list[room_name].show_room()
                elif msg == 'Room Not Exists':
                    pass

            if msg_id == 'SysExitRoomAck':
                room_name = msg_text.keys()[0]
                msg = msg_text.values()[0]
                if msg == "Exit Room":
                    self.__room_list[room_name].destroy_room()
                    self.__room_list.__delitem__(room_name)
                else:
                    print msg

            if msg_id == 'SysRoomListAck':
                self.__enter_room_window.update_room_list(msg_text)

            if msg_id == 'SERVER_SHUTDOWN':
                self.__client_sock.close_client()
                self.__display_new_msg('SysMsg', "Server is down, you can close the program, and come back later")

    def __set_usr_online_time(self, time_str):
        if time_str is not None:
            msg = time_str.split(';')
            self.label_last_online_time['text'] = '上次登录时间\n'.decode('utf-8') + msg[0]
            self.label_total_online_time['text'] = '总共在线时间\n'.decode('utf-8') + msg[1]

    def __private_chat_btn_cmd(self):
        sel = self.listbox_user_list.curselection()
        if sel.__len__() > 0:
            receiver_name = self.listbox_user_list.get(sel)

            usr_msg = self.text_user_msg.get('0.0', END)
            self.__display_new_msg(u'发给 '+ receiver_name + u' 的私信', usr_msg, 'privateChatColor')
            self.text_user_msg.delete('0.0', END)
            data = package_private_chat_msg(self.__user_name, receiver_name, usr_msg)
            self.__client_sock.append_to_msg_sending_queue(data)
        else:
            tkMessageBox.showinfo("Note", "Please select a user")

    def __create_room_btn_cmd(self):
        if not self.__create_room_window:
            self.__create_room_window = CreateRoomGUI(self.__client_sock, self.__user_name, self)
            self.__create_room_window.mainloop()
        else:
            self.__create_room_window.deiconify()

    def __enter_room_btn_cmd(self):
        self.query_all_rooms()

        if not self.__enter_room_window:
            self.__enter_room_window = EnterRoomGUI(self.__client_sock, self.__user_name, self)
            self.__enter_room_window.mainloop()
        else:
            self.__enter_room_window.deiconify()

    def query_all_rooms(self):
        key = 'SysRoomListRequest'
        value = ''
        msg = package_sys_msg(key, value)
        self.__client_sock.append_to_msg_sending_queue(msg)

    def add_new_room(self, room_name, room):
        if not self.__room_list.has_key(room_name):
            self.__room_list[room_name] = room

    def configure_GUI(self):
        # main window
        bg_color = '#208090'
        self['bg'] = bg_color
        self.geometry("550x600+600+300")
        self.resizable(width=True, height=True)

        self.frm_top = Frame(self, width=380, height=250)
        self.frm_mid = Frame(self, width=380, height=250)
        self.frm_btm = Frame(self, width=380, height=30)
        self.frm_right = Frame(self, width=200, height=580)
        self.frm_btm['bg'] = bg_color
        self.frm_right['bg'] = bg_color

        # message zone
        self.label_msg = Label(self, justify=LEFT, text=u"""消息列表""")
        self.label_username = Label(self, justify=LEFT, text=self.__user_name)

        self.text_msg_list = ScrolledText(self.frm_top, borderwidth=1,
                                          highlightthickness=0, relief='flat',
                                          bg='#fffff0', state=DISABLED)
        self.text_msg_list.tag_config('userColor', foreground='red')
        self.text_msg_list.tag_config('privateChatColor', foreground='blue')
        self.text_msg_list.place(x=0, y=0, width=380, height=250)

        self.text_user_msg = ScrolledText(self.frm_mid)
        self.text_user_msg.grid(row=0, column=0)

        # buttons
        self.button_send_msg = Button(self.frm_btm, text='发送群消息', background='grey', command=self.__send_msg_btn_cmd)
        self.button_private_chat = Button(self.frm_right, text='发送私聊消息', background='grey',
                                          command=self.__private_chat_btn_cmd)
        self.button_create_room = Button(self.frm_right, text='创建房间', background='grey', command=self.__create_room_btn_cmd)
        self.button_enter_room = Button(self.frm_right, text='进入房间', background='grey', command=self.__enter_room_btn_cmd)

        self.label_last_online_time = Label(self.frm_right, text='  上次登录时间  \n')
        self.label_total_online_time = Label(self.frm_right, text=' 总共在线时间  \n')

        self.label_other_users = Label(self.frm_right, justify=LEFT, text=u"""其他在线用户""")
        self.user_list_str = StringVar()
        self.listbox_user_list = Listbox(self.frm_right, borderwidth=1, highlightthickness=0, relief='flat', bg='#ededed',
                                         listvariable=self.user_list_str)

        # layout
        self.label_msg.grid(row=0, column=0, padx=2, pady=2, sticky=W)
        self.frm_top.grid(row=1, column=0, padx=2, pady=2)
        self.label_username.grid(row=2, column=0, padx=2, pady=2, sticky=W)
        self.frm_mid.grid(row=3, column=0, padx=2, pady=2, )
        self.frm_btm.grid(row=4, column=0, padx=2, pady=2, )
        self.frm_right.grid(row=0, column=1, rowspan=5, sticky=N + S)

        self.button_send_msg.grid()

        # right frame layout
        self.label_last_online_time.place(x=20, y=30, width=130, height=50)
        self.label_total_online_time.place(x=20, y=90, width=130, height=50)
        self.button_create_room.place(x=20, y=160, width=130, height=30)
        self.button_enter_room.place(x=20, y=200, width=130, height=30)
        self.label_other_users.place(x=20, y=260, width=130, height=30)
        self.listbox_user_list.place(x=7, y=311, width=150, height=250)
        self.button_private_chat.place(x=7, y=565, width=120, height=30)

        self.frm_top.grid_propagate(0)
        self.frm_mid.grid_propagate(0)
        self.frm_btm.grid_propagate(0)
        self.frm_right.grid_propagate(0)


def my_handler(signum, frame):
    print "exit program"


if __name__ == "__main__":
    signal.signal(signal.SIGINT, my_handler)

    d = Dialog()

