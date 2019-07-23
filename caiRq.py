import sapcai
import numpy as np

REQUEST_TOKEN = "c5f00ce71c740878c0ac4abc7fe17812"

build = sapcai.Build(REQUEST_TOKEN, 'en')

CON_ID = np.random.randint(1, 100)


def talk(text_in):
    response = build.dialog({'type': 'text', 'content': text_in}, CON_ID)
    return response.messages


class FakeResponse:
    def __init__(self, p_type, p_content):
        self.type = p_type
        self.content = p_content
