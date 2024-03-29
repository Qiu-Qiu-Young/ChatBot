from flask import Flask, redirect, url_for, request, Response
import flask
import WXBizMsgCrypt as crypt_msg
import xml.etree.cElementTree as ET
import requests
import caiRq
from webCache import Cache
import json
import numpy as np

app = Flask(__name__)

split_sym = '-'
corpId = "wwccd856b6ce4cef38"
corpSecret = "Hba4i3Cq9Xpy_A9Br0PmBfXkT9mEDmBPHi8H0CS_Nxs"
token = "xyuuT7mi0eVDQqJHjC"
encodingAesKey = "cTYhQlOB8OvKgBHWRKilQxj0GcBhBWEB3AIBo5J5LyE"

card_num = 0

crypto = crypt_msg.WXBizMsgCrypt(token, encodingAesKey, corpId)
task_dict = {}
request_dict = {}
# web_url_dict = {}
# phone_dict = {}
web_url_cache = Cache("web_url", 100, split_sym)
phone_cache = Cache("phone", 100, split_sym)


def generate_task_id():
    global card_num
    card_num += 1
    return str(np.random.randint(100000, 999999)) + str(card_num)


def display_msg(rep):
    url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid=" + corpId + "&corpsecret=" + corpSecret
    token = json.loads(requests.get(url).content)['access_token']
    # req = handle_response(touser, agentid, task_id, response)
    url_post = "https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token=" + token
    ret = requests.post(url_post, data=json.dumps(rep))

    return ret.content


def handle_response(touser, agentid, task_id, response):
    global web_url_cache
    global phone_cache

    if response.type == 'text':
        return [{'touser': touser, 'msgtype': 'text', 'agentid': agentid, 'text': {'content': response.content},
                 'safe': 0}]
    elif response.type == 'quickReplies':
        btns = []
        for btn in response.content['buttons']:
            print btn['value']
            btns.append({"key": btn['value'], "name": btn['title']})

        return [{'touser': touser, 'msgtype': 'taskcard', 'agentid': agentid, 'taskcard': {
            "title": response.content['title'],
            "description": " ",
            "task_id": task_id,
            "btn": btns
        }}]
    elif response.type == 'card':
        btns = []
        url = ""
        bt_num = 0
        # for btn in response.content['buttons']:
        #     btn_key = btn['type'] + split_sym + str(bt_num)
        #     dict_key = task_id + split_sym + btn_key
        #     if btn['type'] == 'web_url':
        #         web_url_dict[dict_key] = btn['value']
        #         url = btn['value']
        #     elif btn['type'] == 'phone_number':
        #         phone_dict[dict_key] = btn['value']
        #     btns.append({"key": btn_key, "name": btn['title']})
        #     bt_num += 1

        return [{'touser': touser, 'msgtype': 'news', 'agentid': agentid, 'news': {
            # "title": response.content['title'],
            # "description": response.content['subtitle'] if 'subtitle' in response.content else " ",
            # "task_id": task_id,
            # "btn": btns
            "articles": [
                {
                    "title": response.content['title'],
                    "description": response.content['subtitle'] if 'subtitle' in response.content else " ",
                    "url": url,
                    "picurl": response.content['imageUrl'] if 'imageUrl' in response.content else None
                }
            ]
        }}]
    elif response.type == 'buttons':
        btns = []
        bt_num = 0
        for btn in response.content['buttons']:
            btn_key = btn['type'] + split_sym + str(bt_num)
            dict_key = task_id + split_sym + btn_key
            if btn['type'] == 'web_url':
                web_url_cache.add(dict_key, btn['value'])
                # web_url_dict[dict_key] = btn['value']
            elif btn['type'] == 'phone_number':
                phone_cache.add(dict_key, btn['value'])
                # phone_dict[dict_key] = btn['value']
            btns.append({"key": btn_key, "name": btn['title']})
            bt_num += 1

        return [{'touser': touser, 'msgtype': 'taskcard', 'agentid': agentid, 'taskcard': {
            "title": response.content['title'],
            "description": " ",
            "task_id": task_id,
            "btn": btns
        }}]
    elif response.type == 'carousel':
        reps = []
        for card_content in response.content:
            print json.dumps(card_content)
            card = caiRq.FakeResponse("card", card_content)
            reps.extend(handle_response(touser, agentid, generate_task_id(), card))
        return reps

    elif response.type == 'list':
        return [{'touser': touser, 'msgtype': 'text', 'agentid': agentid,
                 'text': {'content': "Sorry, we don't support list"},
                 'safe': 0}]
    elif response.type == 'picture':
        return [{'touser': touser, 'msgtype': 'text', 'agentid': agentid,
                 'text': {'content': response.content},
                 'safe': 0}]
    elif response.type == 'video':
        return [{'touser': touser, 'msgtype': 'text', 'agentid': agentid,
                 'text': {'content': response.content},
                 'safe': 0}]


@app.route('/chat_bot', methods=['POST', 'GET'])
def chat_bot():
    global task_dict
    global request_dict
    signature = request.args.get('msg_signature')
    timestamps = request.args.get('timestamp')
    nonce = request.args.get('nonce')
    msg_encrypt = request.args.get('echostr')
    if request.method == 'GET':
        signature = request.args.get('msg_signature')
        timestamps = request.args.get('timestamp')
        nonce = request.args.get('nonce')
        msg_encrypt = request.args.get('echostr')

        ret, sReplyEchoStr = crypto.VerifyURL(signature, timestamps, nonce, msg_encrypt)
        if ret == 0:
            return sReplyEchoStr
        else:
            return "error"
    elif request.method == 'POST':
        ret, content = crypto.DecryptMsg(request.data, signature, timestamps, nonce)
        if ret == 0:
            content_tree = ET.fromstring(content)
            if content_tree.find('Event') is None:
                print content
                text_in = content_tree.find('Content').text
                username = content_tree.find('FromUserName').text
                # msg_type = content_tree.find('MsgType').text
                agent_id = content_tree.find('AgentID').text
            else:
                text_in = content_tree.find('EventKey').text
                username = content_tree.find('FromUserName').text
                # msg_type = content_tree.find('MsgType').text
                agent_id = content_tree.find('AgentId').text
                if text_in.split(split_sym)[0] == 'web_url':
                    task_id = content_tree.find('TaskId').text
                    url = web_url_cache.find(task_id + split_sym + text_in)
                    rep = {'touser': username, 'msgtype': 'text', 'agentid': agent_id,
                           'text': {'content': url},
                           'safe': 0}
                    print display_msg(rep)
                    return rep

            responses = caiRq.talk(text_in)
            if request.url in request_dict:
                return "replicated"

            for response in responses:
                print response.type
                task_id = generate_task_id()
                reps = handle_response(username, agent_id, task_id, response)
                for rep in reps:
                    print display_msg(rep)
                task_dict[task_id] = response

            request_dict[request.url] = request.data
            # print display_msg(username, agent_id, responses[0])
            return responses[0].content
        else:
            return "error"


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
