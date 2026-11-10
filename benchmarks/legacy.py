"""旧版（v1.0.0, api.py）的解析实现，仅用于性能/正确性对比。

保持与原始代码相同的正则、相同的下标取值；出错时按原样抛出异常，
这样基准测试可以如实报告"旧实现在今天的豆瓣页面上是否还能解析"。
"""

from __future__ import annotations

import re


def parse_latest(html: str) -> dict:
    data: dict = {"books": []}
    result = re.findall(re.compile(r'<li class="media clearfix">(.*?)</li>', re.S), html)
    for item in result:
        book = {}
        item = item.replace("\n", "").replace("\t", "").replace("\r", "")
        item = re.sub(" +", " ", item)
        img_result = re.findall(
            re.compile(
                r'<a href="https://book.douban.com/subject/(.*?)/"><img class="subject-cover"'
                r' align="left" src="(.*?)"/></a>',
                re.S,
            ),
            item,
        )
        book["id"] = img_result[0][0]
        book["cover"] = img_result[0][1]
        name_result = re.findall(re.compile(r'<a class="(.*?)" href="(.*?)">(.*?)</a>', re.S), item)
        book["name"] = name_result[0][2]
        data_result = re.findall(
            re.compile(r'<p class="(.*?)">(.*?)/(.*?)/(.*?)/(.*?)/(.*?)</p>', re.S), item
        )
        book["auther"] = data_result[0][1]
        book["publish"] = data_result[0][3]
        book["price"] = data_result[0][4].replace("元", "")
        comment_result = re.findall(re.compile(r'<span class="(.*?)">(.*?)</span>', re.S), item)
        book["comment"] = comment_result[1][1]
        data["books"].append(book)
    data["code"] = 200
    return data


def parse_tag(html: str) -> dict:
    data: dict = {"books": []}
    result = re.findall(re.compile(r'<li class="subject-item">(.*?)</li>', re.S), html)
    for item in result:
        book = {}
        item = item.replace("\n", "").replace("\t", "").replace("\r", "")
        item = re.sub(" +", " ", item)
        img_result = re.findall(re.compile(r'<img class="" src="(.*?)" width="90">', re.S), item)
        book["cover"] = img_result[0]
        name_result = re.findall(
            re.compile(
                r'<a href="https://book.douban.com/subject/(.*?)/" title="(.*?)"'
                r' onclick="(.*?)">(.*?)</a>',
                re.S,
            ),
            item,
        )
        book["id"] = name_result[0][0]
        book["name"] = name_result[0][1]
        data_result = re.findall(re.compile(r'<div class="pub">(.*?)</div>', re.S), item)
        book["info"] = data_result[0]
        comment_result = re.findall(re.compile(r'<span class="(.*?)">(.*?)</span>', re.S), item)
        book["comment"] = comment_result[1][1]
        data["books"].append(book)
        data["code"] = 200
    return data


def parse_detail(html: str) -> dict:
    data: dict = {}
    book: dict = {}
    html = re.sub(" +", " ", html).replace("\n", "").replace("\t", "")
    result = re.findall(re.compile(r'<div id="content">(.*?)</div>', re.S), html)
    name_result = re.findall(
        re.compile(
            r'<img src="(.*?)" title="点击看大图" alt="(.*?)" rel="v:photo"'
            r' style="max-width: 135px;max-height: 200px;">',
            re.S,
        ),
        result[0],
    )
    book["cover"] = name_result[0][0]
    book["name"] = name_result[0][1]
    data_result = re.findall(re.compile(r'<div id="info" class="">(.*?)</div>', re.S), html)
    auther_result = re.findall(
        re.compile(r'<span class="pl"> (.*?)</span>:(.*?)<br>', re.S), data_result[0]
    )
    auther_result_url = auther_result[0][1]
    result2 = re.findall(re.compile(r'<a class="" href="(.*?)">(.*?)</a>', re.S), auther_result_url)
    book["auther"] = result2[0][1]
    result3 = re.findall(re.compile(r'<a href="(.*?)">(.*?)</a>', re.S), auther_result_url)
    book["publisher"] = result3[0][1]
    result4 = re.findall(
        re.compile(r'<span class="pl">(.*?)</span> (.*?)<br/>', re.S), data_result[0]
    )
    for item in result4:
        if item[0] == "定价:":
            book["price"] = item[1].replace("元", "")
        if item[0] == "ISBN:":
            book["ISBN"] = item[1]
    book["ISBN"] = result4[len(result4) - 1][1]
    pingjia_result = re.findall(
        re.compile(r'<strong class="ll rating_num " property="v:average"> (.*?) </strong>', re.S),
        html,
    )
    if not pingjia_result:
        book["score"] = "0"
        book["score_num"] = "0"
    else:
        book["score"] = pingjia_result[0]
        votes = re.findall(re.compile(r'<span property="v:votes">(.*?)</span>', re.S), html)
        book["score_num"] = votes[0]
    jianjie = re.findall(re.compile(r'<div class="intro">(.*?)</div>', re.S), html)
    book["introduction"] = jianjie[0]
    book["auther_introduction"] = jianjie[1]
    data["code"] = 200
    data["book"] = book
    return data


def legacy_scan(html: str) -> int:
    """只做正则扫描（不做下标取值），用于测量"整页正则"的原始吞吐。

    注意：这里刻意没有把 ``<p class="...">a/b/c/d/e</p>`` 那条正则放到整页上跑——
    它包含 5 个惰性分组，在无匹配的整页上会发生灾难性回溯（实测 >20s）。
    旧版只在单个 ``<li>`` 片段上使用它，所以没暴露出来。
    """
    count = 0
    count += len(re.findall(re.compile(r'<li class="(.*?)">(.*?)</li>', re.S), html))
    count += len(re.findall(re.compile(r'<a class="(.*?)" href="(.*?)">(.*?)</a>', re.S), html))
    count += len(re.findall(re.compile(r"<div class=\"(.*?)\">(.*?)</div>", re.S), html))
    count += len(re.findall(re.compile(r'<span class="(.*?)">(.*?)</span>', re.S), html))
    normalized = html.replace("\n", "").replace("\t", "").replace("\r", "")
    count += len(re.sub(" +", " ", normalized))
    return count
