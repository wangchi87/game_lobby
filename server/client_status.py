# -*- coding: utf-8 -*-

import time

heart_beat_threshold = 30


class ClientStatus:
    '''
    This class is mainly used to maintain the status of each client.
    The client will send 'heart beat' package ("-^-^-pyHB-^-^-") to the server

    There are two benefits of doing this:
    1. the heart beat package will allow the server to be aware of whether the client is ALIVE or not
    2. the heart beat package also serve as PASSWORD to maintain a connection with the server,
       so that the connection which is NOT raised from our client program will be rejected(closed by the server)
    '''

    __client_has_logged_in = False
    # record how long the user keeps online this time
    __online_duration = None
    __last_online_time_stamp = None

    __login_time_stamp = None

    # record the time stamp that a heart beat signal came in
    __last_check_in_time_stamp = None

    def __init__(self):
        self.update_client_online_status()

    def client_login(self):
        self.__client_has_logged_in = True
        self.__login_time_stamp = time.time()

    def client_logout(self):
        self.__client_has_logged_in = False

    def client_has_login_or_not(self):
        return self.__client_has_logged_in

    def update_client_online_status(self):
        self.__last_check_in_time_stamp = time.time()

    def is_client_offline(self):

        delta = time.time() - self.__last_check_in_time_stamp

        if delta <= heart_beat_threshold:
            return False
        else:
            return True

    def get_last_checked_in_time(self):
        return self.__last_check_in_time_stamp

    def get_client_online_duration(self):
        self.__online_duration = time.time() - self.__login_time_stamp
        return self.__online_duration

    def get_client_login_time_stamp(self):
        return self.__login_time_stamp


if __name__ == '__main__':
    pass
