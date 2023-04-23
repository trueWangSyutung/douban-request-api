
from flask import request, jsonify
import requests
import re
from flask import Flask  # 导包
import execjs  # 这个库是PyExecJS

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36'
}
app = Flask(__name__)  # 创建app，__name__表示指向程序所在的包
# 函数,接收请求,返回响应，传入参数为图片数据的base64编码

@app.route("/", methods=[ 'GET'])
def index():
    html = '<html lang="zh-cn"><head><meta charset="UTF-8"><title>'+'基于爬虫的豆瓣图书查询系统'+'</title></head>'
    html += '<body>'
    html += '<h1>基于爬虫的豆瓣图书查询系统</h1>'
    html += '<h2>您已经成功部署了基于爬虫的豆瓣图书查询系统</h2>'
    html += '<h2>个人网站：<a href="http://syutung.sar.tw.cn/">http://syutung.sar.tw.cn/</a></h2>'
    html += '<h2>邮箱：wangxudong@sar.tw.cn</h2>'
    html += '</body></html>'
    return html


@app.route("/getNewBook", methods=[ 'GET'])
def face_recognition():
    # 获取参数,page为页数，type为类型
    page = request.args.get('page')
    type = request.args.get('type')
    # 请求地址
    url = 'https://book.douban.com/latest?subcat=' + type + '&p=' + page
    # 请求头
    # 发送请求
    response = requests.get(url, headers=headers)
    # 获取响应内容
    html = response.text
    
    data = {
    }
    data['books'] = []
        # 匹配数据
        # 匹配书名
    reg = '<li class="media clearfix">(.*?)</li>'
    reg = re.compile(reg, re.S)
    result = re.findall(reg, html)
    for i in result:
        book = {}
        # 去除回车
        i = i.replace('\n', '')
        # 去除制表符
        i = i.replace('\t', '')
        # 去除空格
        i = i.replace('\s', '')
        i = i.replace('\r', '')
        # 去除多余空格
        i = re.sub(' +', ' ', i)
        # 匹配书名
        img_reg = '<a href="https://book.douban.com/subject/(.*?)/"><img class="subject-cover" align="left" src="(.*?)"/></a>'
        img_reg = re.compile(img_reg, re.S)
        img_result = re.findall(img_reg, i)
        print(img_result)
        book['id'] = img_result[0][0]
        book['cover'] = img_result[0][1]

        name_reg = '<a class="(.*?)" href="(.*?)">(.*?)</a>'
        name_reg = re.compile(name_reg, re.S)
        name_result = re.findall(name_reg, i)
        book['name'] = name_result[0][2]

        data_reg = '<p class="(.*?)">(.*?)/(.*?)/(.*?)/(.*?)/(.*?)</p>'
        data_reg = re.compile(data_reg, re.S)
        data_result = re.findall(data_reg, i)

        book['auther'] = data_result[0][1]
        book['publish'] = data_result[0][3]
        book['price'] = data_result[0][4].replace('元', '')

        comment_reg = '<span class="(.*?)">(.*?)</span>'
        comment_reg = re.compile(comment_reg, re.S)
        comment_result = re.findall(comment_reg, i)
        book['comment'] = comment_result[1][1]
        data['code'] = 200
        data['books'].append(book)

    return jsonify(data)

@app.route("/getBookDetail", methods=[ 'GET'])
def getBookDetail():
    # 获取参数, id为书籍id
    id = request.args.get('id')
    # 请求地址
    url = 'https://book.douban.com/subject/' + id
    # 发送请求
    response = requests.get(url, headers=headers)
    # 获取响应内容
    html = response.text
    # 去除多余空格
    html = re.sub(' +', ' ', html)
    # 去除回车
    html = html.replace('\n', '')
    # 去除制表符
    html = html.replace('\t', '')
    data = {}
    book = {}

    # 匹配数据
    reg = '<div id="content">(.*?)</div>'
    reg = re.compile(reg, re.S)
    result = re.findall(reg, html)
    # 匹配书名
    name_reg = '<img src="(.*?)" title="点击看大图" alt="(.*?)" rel="v:photo" style="max-width: 135px;max-height: 200px;">'
    name_reg = re.compile(name_reg, re.S)
    name_result = re.findall(name_reg, result[0])
    book['cover'] = name_result[0][0]
    book['name'] = name_result[0][1]

    # 匹配信息
    data_reg = '<div id="info" class="">(.*?)</div>'
    data_reg = re.compile(data_reg, re.S)   
    data_result = re.findall(data_reg, html)
    auther_reg = '<span class="pl"> (.*?)</span>:(.*?)<br>'
    auther_reg = re.compile(auther_reg, re.S)
    auther_result = re.findall(auther_reg, data_result[0])
    auther_result_url = auther_result[0][1]

    reg2 = '<a class="" href="(.*?)">(.*?)</a>'
    reg2 = re.compile(reg2, re.S)
    result2 = re.findall(reg2, auther_result_url)
    book['auther'] = result2[0][1]

    reg3 = '<a href="(.*?)">(.*?)</a>'
    reg3 = re.compile(reg3, re.S)
    result3 = re.findall(reg3, auther_result_url)
    
    book['publisher'] = result3[0][1]


    reg4 = '<span class="pl">(.*?)</span> (.*?)<br/>'
    reg4 = re.compile(reg4, re.S)
    result4 = re.findall(reg4, data_result[0])
    for i in range(len(result4)):
        print(result4[i],result4[i][0])
        if result4[i][0] == '定价:':
            book['price'] = result4[i][1].replace('元', '')
        if result4[i][0] == 'ISBN:':
            book['ISBN'] = result4[i][1]
    reg5 = '<span class="pl">(.*?)</span>(.*?)<br>'
    reg5 = re.compile(reg5, re.S)
    result5 = re.findall(reg5, result4[len(result4)-1][1]+"<br>")
    print(result4[len(result4)-1][1])
    book['ISBN'] = result4[len(result4)-1][1]

    # 爬起评价
    pingjia_reg = '<strong class="ll rating_num " property="v:average"> (.*?) </strong>'
    pingjia_reg = re.compile(pingjia_reg, re.S)
    pingjia_result = re.findall(pingjia_reg, html)
    print(pingjia_result)
    if len(pingjia_result) == 0:
        book['score'] = '0'
        book['score_num'] = '0'
        comment = {}
        comment['star5'] = '0'
        comment['star4'] = '0'
        comment['star3'] = '0'
        comment['star2'] = '0'
        comment['star1'] = '0'
        book['comment'] = comment
        
    else:
        book['score'] = pingjia_result[0]
        # 爬起评价人数
        pingjia_renshu_reg = '<span property="v:votes">(.*?)</span>'
        pingjia_renshu_reg = re.compile(pingjia_renshu_reg, re.S)
        pingjia_renshu_result = re.findall(pingjia_renshu_reg, html)
        book['score_num'] = pingjia_renshu_result[0]
    
        # 爬取各星级评价人数
        xingji_pingjia_renshu_reg = '<span class="rating_per">(.*?)</span>'
        xingji_pingjia_renshu_reg = re.compile(xingji_pingjia_renshu_reg, re.S)
        xingji_pingjia_renshu_result = re.findall(xingji_pingjia_renshu_reg, html)
        comment = {}
        comment['star5'] = xingji_pingjia_renshu_result[0].replace('%', '')
        comment['star4'] = xingji_pingjia_renshu_result[1].replace('%', '')
        comment['star3'] = xingji_pingjia_renshu_result[2].replace('%', '')
        comment['star2'] = xingji_pingjia_renshu_result[3].replace('%', '')
        comment['star1'] = xingji_pingjia_renshu_result[4].replace('%', '')
        book['comment'] = comment

    # 爬取简介
    jianjie_reg = '<div class="intro">(.*?)</div>'
    jianjie_reg = re.compile(jianjie_reg, re.S)
    jianjie_result = re.findall(jianjie_reg, html)
    # 去除<p>标签\</p>\<a href="javascript:void(0)" class="j a_show_full">(展开全部)</a>
    jianjie_result = jianjie_result[0].replace('<p>', '').replace('</p>', '').replace('<a href="javascript:void(0)" class="j a_show_full">(展开全部)</a>', '')
    book['introduction'] = jianjie_result

    # 爬取作者简介
    auther_jianjie_reg = '<div class="intro">(.*?)</div>'
    auther_jianjie_reg = re.compile(auther_jianjie_reg, re.S)
    auther_jianjie_result = re.findall(auther_jianjie_reg, html)
    auther_jianjie_result = auther_jianjie_result[1].replace('<p>', '').replace('</p>', '').replace('<a href="javascript:void(0)" class="j a_show_full">(展开全部)</a>', '')
    book['auther_introduction'] = auther_jianjie_result
    data['code'] = 200
    data['book'] = book
    return jsonify(data)

@app.route("/getType", methods=[ 'GET'])
def getTYpe():
    # 获取参数,page为页数，type为类型
    page = int(request.args.get('page'))
    type = request.args.get('tag')
    # 请求地址
    url = 'https://book.douban.com/tag/'+str(type)+'?start='+str((page-1)*20)+'&type=T'
    # 请求头
    # 发送请求
    response = requests.get(url, headers=headers)
    # 获取响应内容
    html = response.text
    data = {
    }
    data['books'] = []
        # 匹配数据
        # 匹配书名
    reg = '<li class="subject-item">(.*?)</li>'
    reg = re.compile(reg, re.S)
    result = re.findall(reg, html)
    for i in result:
        book = {}
        # 去除回车
        i = i.replace('\n', '')
        # 去除制表符
        i = i.replace('\t', '')
        # 去除空格
        i = i.replace('\s', '')
        i = i.replace('\r', '')
        # 去除多余空格
        i = re.sub(' +', ' ', i)
        # 匹配书名
        img_reg = '<img class="" src="(.*?)" width="90">'
        img_reg = re.compile(img_reg, re.S)
        img_result = re.findall(img_reg, i)
        book['cover'] = img_result[0]

        
        name_reg = '<a href="https://book.douban.com/subject/(.*?)/" title="(.*?)" onclick="(.*?)">(.*?)</a>'
        name_reg = re.compile(name_reg, re.S)
        name_result = re.findall(name_reg, i)
        print(name_result)
        book['id'] = name_result[0][0]
        book['name'] = name_result[0][1]

        data_reg = '<div class="pub">(.*?)</div>'
        data_reg = re.compile(data_reg, re.S)
        data_result = re.findall(data_reg, i)
        book['info'] = data_result[0] 
        #book['publish'] = data_result[0][2]
        #book['price'] = data_result[0][4].replace('元', '')

        comment_reg = '<span class="(.*?)">(.*?)</span>'
        comment_reg = re.compile(comment_reg, re.S)
        comment_result = re.findall(comment_reg, i)
        book['comment'] = comment_result[1][1]
        
        data['books'].append(book)
        data['code'] = 200
    return jsonify(data)
    

@app.route("/search", methods=[ 'GET'])
def search():
    # 获取参数,q为搜索字段
    q  = request.args.get('q')
    # 请求地址
    url = 'https://search.douban.com/book/subject_search?search_text='+q+''
    print(url)
    # 请求头
    # 发送请求
    response = requests.get(url, headers=headers)
    # 等待响应
    response.encoding = 'utf-8'
    #等待1s，获取完整的响应内容
    # 获取响应内容
    html = response.text
    # 去除回车
    html = html.replace('\n', '')
        # 去除制表符
    html = html.replace('\t', '')
        # 去除空格
    html = html.replace('\s', '')
        # 去除多余空格
    html = re.sub(' +', ' ', html)
    mydata = {
    }
    mydata['books'] = []
        # 匹配数据
        # 匹配书名
    reg = 'window.__DATA__ =(.*?);'
    reg = re.compile(reg, re.S)
    result = re.findall(reg, html)
    with open('./main.js', 'r', encoding='utf-8') as f:
        decrypt_js = f.read()
    ctx = execjs.compile(decrypt_js)
    data = ctx.call('decrypt', result[0])
    for item in data['payload']['items']:
        if item['tpl_name'] == 'search_subject':
            book = {}
            book['cover'] = item['cover_url']
            book['name'] = item['title']
            book['info'] = item['abstract']
            book['comment_count'] = item['rating']['count']
            book['rating'] = item['rating']['value']
            book['id'] = item['id']
            mydata['books'].append(book)
        elif item['tpl_name'] == 'search_common':
            author = {}
            author['name'] = item['title']
            author['id'] = item['id']
            author['info'] = item['abstract_2']
            author['img'] = item['cover_url']
            mydata['author'] = author
    mydata['code'] = 200
    mydata['msg'] = 'success'
    print(mydata)
    return jsonify(mydata)

if __name__ == '__main__':
    app.run(host='0.0.0.0',port=5000,debug=True)

