# -*- coding: utf-8 -*-
import json


def package_msg(key, msg):
    packed_msg = {}
    packed_msg[key] = msg
    return json.dumps(packed_msg)


def package_sys_msg(key, msg):
    packed_msg = {}
    packed_msg['SysMsg'] = {key: msg}
    return json.dumps(packed_msg)


def package_public_chat_msg(sender, msg):
    packed_msg = {}
    packed_msg['ChatMsg'] = {'toAll': [sender, msg]}
    return json.dumps(packed_msg)


def package_private_chat_msg(sender, receiver, msg):
    packed_msg = {}
    packed_msg['ChatMsg'] = {'toClient': [sender, receiver, msg]}
    return json.dumps(packed_msg)


def convert_seconds_to_hms_fmt(seconds):
    '''
    convert seconds to day, hour, seconds format
    :return: day, hour, seconds format in str
    '''
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)

    # time_str = str("%02dh-%02dm-%02ds" % (h, m, s))
    time_str = str("%02dh-%02dm" % (h, m))
    return time_str
