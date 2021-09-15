import urllib

import requests


def qingyunke(msg):
    url = 'http://api.qingyunke.com/api.php?key=free&appid=0&msg={}'.format(urllib.parse.quote(msg))
    html = requests.get(url)
    return html.json()["content"].replace("{br}",'\n')
msg = '歌词后来'
print("原话>>", msg)
res = qingyunke(msg)
print("青云客>>", res)
