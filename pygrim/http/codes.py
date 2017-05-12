# coding: utf8

import sys
if sys.version_info.major == 3:
    import http.server
    http_responses = {
        code: code_desc[0]
        for code, code_desc
        in http.server.BaseHTTPRequestHandler.responses.items()
    }
else:
    from httplib import responses as http_responses

# in order of http://en.wikipedia.org/wiki/List_of_HTTP_status_codes
http_responses.setdefault(418, "I'm a teapot")  # LOL
http_responses.setdefault(423, "Locked")
http_responses.setdefault(426, "Updgrade Required")
http_responses.setdefault(428, "Precondition Required")
