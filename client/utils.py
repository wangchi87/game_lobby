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


def package_room_chat_msg(sender, room_name, msg):
    packed_msg = {}
    packed_msg['ChatMsg'] = {'toRoom': [sender, room_name, msg]}
    return json.dumps(packed_msg)
