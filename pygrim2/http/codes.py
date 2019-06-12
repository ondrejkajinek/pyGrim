# std
import http.client
import sys

if sys.version_info[1] >= 5:
    http_responses = {
        code.value: description
        for code, description
        in http.client.responses.items()
    }
else:
    http_responses = {
        code: description
        for code, description
        in http.client.responses.items()
    }

# in order of http://en.wikipedia.org/wiki/List_of_HTTP_status_codes
http_responses.setdefault(418, "I'm a teapot")  # LOL
http_responses.setdefault(423, "Locked")
http_responses.setdefault(426, "Updgrade Required")
http_responses.setdefault(428, "Precondition Required")
