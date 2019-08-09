import requests, time

from requests.exceptions import RequestException

from typing import Optional


# N.B. this script requires Tor to be running on the server
def send_request() -> Optional[requests.Response]:
    # TODO: handle any ConnectionRefusedError and ConnectTimeoutError
    headers = {
        'User-agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0',
        'referer': 'https://www.google.com'
    }
    proxies = {
        'http': 'socks5h://127.0.0.1:9050',
        'https': 'socks5h://127.0.0.1:9050'
    }
    try:
        return requests.get('http://33y6fjyhs3phzfjj.onion', headers=headers, proxies=proxies, timeout=10)
    except RequestException as err:
        print(err)


def passes_healthcheck(response: Optional[requests.Response]) -> bool:
    expected_text = 'SecureDrop | Protecting Journalists and Sources'
    if response:
        print(f'response status code: {response.status_code}')
        if response.status_code == 200 and expected_text in response.text:
            return True
    return False


def main():
    attempts = 0
    while attempts < 5:
        attempts += 1
        response = send_request()
        if passes_healthcheck(response):
            break
        print(f'unable to reach site on attempt {attempts}')
        time.sleep(60)
    else:
        # TODO: Send an email via SNS
        pass


if __name__ == '__main__':
    main()
