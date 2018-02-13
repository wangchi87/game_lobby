# -*- coding: UTF-8 -*-

import time
import tkMessageBox
from ScrolledText import ScrolledText
from Tkinter import *

from utils import *


class CreateRoomGUI(Toplevel):
    __client_sock = None
    __user_name = None
    __main_frame = None

    __room = None

    def __init__(self, client, username, mfm):
        Toplevel.__init__(self)
        self.protocol('WM_DELETE_WINDOW', self.close_room)
        self.__user_name = username
        self.__client_sock = client
        self.__main_frame = mfm
        self.configure_GUI()

    def close_room(self):
        self.withdraw()

    def configure_GUI(self):
        self.title(u'创建房价')
        frm_pos = '%dx%d+%d+%d' % (325, 230, (1500 - 400) / 2, (900 - 300) / 2)
        self.geometry(frm_pos)
        self.resizable(width=True, height=True)

        self.label_room_name = Label(self, text=u'房间名称')
        self.label_creation_Info = Label(self)
        self.text_room_name = Entry(self, text=u'room')

        self.button_room_creation = Button(self, text=u'创建', command=self.create_room_btn_cmd)
        self.button_cancel = Button(self, text=u'取消', command=self.cancel_btn_cmd)

        self.label_room_name.pack(pady=15)
        self.label_creation_Info.pack(pady=5)
        self.text_room_name.pack(pady=5)
        self.button_room_creation.pack(pady=5)
        self.button_cancel.pack(pady=5)

    def cancel_btn_cmd(self):
        self.withdraw()

    def create_room_btn_cmd(self):
        room_name = self.text_room_name.get()
        key = 'SysCreateRoomRequest'
        value = {'admin': self.__user_name, 'roomName': room_name}
        msg = package_sys_msg(key, value)
        self.__client_sock.append_to_msg_sending_queue(msg)

        # get sys ack meg, add new room to main_frame.room_list
        self.__room = Room(self.__client_sock, room_name, self.__main_frame, self)


class EnterRoomGUI(Toplevel):
    __client_sock = None
    __user_name = None
    __main_frame = None
    __room_list = []

    __room_name = None
    __room = None

    def __init__(self, client, username, mfm):
        Toplevel.__init__(self)
        self.protocol('WM_DELETE_WINDOW', self.closeRoom)
        self.__user_name = username
        self.__client_sock = client
        self.__main_frame = mfm

        # query all existing room
        self.query_all_rooms()
        self.configureUI()

    def closeRoom(self):
        self.withdraw()

    def configureUI(self):
        self.title(u'进入房间')
        frame_pos = '%dx%d+%d+%d' % (250, 400, (1500 - 400) / 2, (900 - 300) / 2)
        self.geometry(frame_pos)
        self.resizable(width=True, height=True)

        self.label_caption = Label(self, text=u'所有房间')

        self.listbox_room = Listbox(self, bg='#fffff0')
        self.listbox_room.grid_propagate(0)

        self.button_enter_room = Button(self, text=u'进入', command=self.enter_room_btn_cmd)
        self.button_cancel = Button(self, text=u'取消', command=self.cancel_btn_cmd)

        self.label_caption.place(x=75, y=20, width=100, height=30)
        self.listbox_room.place(x=25, y=80, width=200, height=200)
        self.button_enter_room.place(x=50, y=350, width=50, height=30)
        self.button_cancel.place(x=150, y=350, width=50, height=30)

    def cancel_btn_cmd(self):
        self.withdraw()

    def enter_room_btn_cmd(self):
        if self.listbox_room.size() == 0:
            tkMessageBox.showinfo("Note", "There is no room available")
            return

        sel = self.listbox_room.curselection()
        if sel.__len__() > 0:
            self.__room_name = self.listbox_room.get(sel)
            key = 'SysEnterRoomRequest'
            value = {'roomName': self.__room_name}
            msg = package_sys_msg(key, value)
            self.__client_sock.append_to_msg_sending_queue(msg)
            self.__room = Room(self.__client_sock, self.__room_name, self.__main_frame, self)
        else:
            tkMessageBox.showinfo("Note", "Please select a room")

    def query_all_rooms(self):
        key = 'SysRoomListRequest'
        value = ''
        msg = package_sys_msg(key, value)
        self.__client_sock.append_to_msg_sending_queue(msg)

    def update_room_list(self, room_list):
        self.listbox_room.delete(0, END)
        for r in room_list:
            self.listbox_room.insert(END, r)


class Room(Toplevel):
    __client_sock = None
    __user_name = None
    __room_name = None
    __main_frame = None
    __top_frame = None

    __exit_room = False

    def __init__(self, client, room_name, main_frame, top_frame):
        Toplevel.__init__(self)

        self['background'] = 'grey'

        self.protocol('WM_DELETE_WINDOW', self.close_room)
        self.__user_name = main_frame.get_user_name()

        self.title("Room Name:" + room_name)
        self.__room_name = room_name

        self.configure_GUI()
        self.__client_sock = client

        self.__top_frame = top_frame
        self.__main_frame = main_frame
        self.__main_frame.add_new_room(self.__room_name, self)

        self.withdraw()
        self.mainloop()

    def show_room(self):
        self.__top_frame.withdraw()
        self.deiconify()

    def close_room(self):
        self.withdraw()

    def configure_GUI(self):
        # main window
        bg_color = '#208090'
        self['bg'] = bg_color
        self.geometry("400x500+520+500")
        self.resizable(width=True, height=True)

        self.frm_top = Frame(self, width=380, height=250)
        self.frm_mid = Frame(self, width=380, height=150)
        self.frm_btm = Frame(self, width=380, height=30)
        self.frm_btm['bg'] = bg_color

        self.label_msg_list = Label(self, justify=LEFT, text=u"""消息列表""")
        self.label_user_name = Label(self, justify=LEFT, text=self.__user_name)

        self.text_msg_List = ScrolledText(self.frm_top, borderwidth=1, highlightthickness=0, relief='flat',
                                          bg='#fffff0')
        self.text_msg_List.tag_config('userColor', foreground='red')
        self.text_msg_List.place(x=0, y=0, width=380, height=250)

        self.text_client_msg = ScrolledText(self.frm_mid)
        self.text_client_msg.grid(row=0, column=0)

        self.button_send_msg = Button(self.frm_btm, text='发送消息', command=self.__send_msg_btn_cmd)
        self.button_send_msg.place(x=0, y=0, width=100, height=30)

        self.button_exit_room = Button(self.frm_btm, text='退出房间', command=self.__exit_room_btn_cmd)
        self.button_exit_room.place(x=280, y=0, width=100, height=30)

        self.label_msg_list.grid(row=0, column=0, padx=2, pady=2, sticky=W)
        self.frm_top.grid(row=1, column=0, padx=2, pady=2)
        self.label_user_name.grid(row=2, column=0, padx=2, pady=2, sticky=W)
        self.frm_mid.grid(row=3, column=0, padx=2, pady=2, )
        self.frm_btm.grid(row=4, column=0, padx=2, pady=2, )

        self.frm_top.grid_propagate(0)
        self.frm_mid.grid_propagate(0)
        self.frm_btm.grid_propagate(0)

    def destroy_room(self):
        self.destroy()

    def query_room_user_name(self):
        msg = {'roomName': self.__room_name}
        data = package_sys_msg("SysRoomUserNameRequest", msg)
        self.__client_sock.append_to_msg_sending_queue(data)

    def __exit_room_btn_cmd(self):
        self.__exit_room = True
        msg = {'roomName': self.__room_name}
        data = package_sys_msg("SysExitRoomRequest", msg)
        self.__client_sock.append_to_msg_sending_queue(data)

    def __send_msg_btn_cmd(self):
        if self.__exit_room:
            return

        usr_msg = self.text_client_msg.get('0.0', END)
        self.display_new_msg(self.__user_name, usr_msg, 'userColor')
        self.text_client_msg.delete('0.0', END)
        data = package_room_chat_msg(self.__user_name, self.__room_name, usr_msg)
        self.__client_sock.append_to_msg_sending_queue(data)

    def display_new_msg(self, user_name, msg, config=''):
        self.text_msg_List['state'] = 'normal'
        msg_time = time.strftime(" %Y-%m-%d %H:%M:%S", time.localtime()) + '\n'
        self.text_msg_List.insert(END, user_name + ': ' + msg_time + msg, config)
        self.text_msg_List['state'] = 'disabled'

