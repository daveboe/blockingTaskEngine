import requests
import logging


def retry(func, max_tries=1, logging=False, hook=None):
    def retried_func(*args, **kwargs):
        tries = 0
        while True:
            if hook is not None:
                hook(logging)
            resp = func(*args, **kwargs)
            if resp.status_code == 500 and tries < max_tries:
                tries += 1
                continue
            break
        return resp
    return retried_func
