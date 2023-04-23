---
title: 基于爬虫的豆瓣图书查询 v1.0.0
language_tabs:
  - shell: Shell
  - http: HTTP
  - javascript: JavaScript
  - ruby: Ruby
  - python: Python
  - php: PHP
  - java: Java
  - go: Go
toc_footers: []
includes: []
search: true
code_clipboard: true
highlight_theme: darkula
headingLevel: 2
generator: "@tarslib/widdershins v4.0.15"

---

# 基于爬虫的豆瓣图书查询

> v1.0.0 Alpha

> 本项目基于 豆瓣+Requests的爬虫模拟，请勿遍历爬取

> 服务器带宽有限，，请勿遍历爬取

> BaseUrl = http://douban.sar.tw.cn

> 如有需要可以自行部署

> 部署请参考下一章

# 部署

## 基于宝塔管理平台的部署

> 1. 先把python上传到服务器，再在软件商店安装python项目管理，添加项目，选择 flask和uwsgi，可以不勾选安装依赖

> 2. 安装如下的库

|库名| 版本 |
|---|---|
|cmake	|3.26.3	|
|Flask	|2.0.3	|
|gevent	|22.10.2	|
|PyExecJS	|1.5.1	|
|requests	| 2.18.4	|
|requests-unixsocket	| 0.1.5	|

> 3. 启动项目


# 文档

## GET 获取图书标签下的图书

GET /getType

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|page|query|string| 否 |从1开始，默认为1|
|tag|query|string| 是 |参考 https://book.douban.com/tag/?view=type&icn=index-sorttags-all 页面中的tag|

> 返回示例

> 成功

```json
{
  "books": [
    {
      "comment": "8.5",
      "cover": "https://img2.doubanio.com/view/subject/s/public/s34327482.jpg",
      "id": "36104107",
      "info": " 马伯庸 / 湖南文艺出版社 / 2022-10 / 45.00元 ",
      "name": "长安的荔枝"
    },
    {
      "comment": "6.1",
      "cover": "https://img1.doubanio.com/view/subject/s/public/s34413297.jpg",
      "id": "36218542",
      "info": " 徐纪周、朱俊懿、白文君 / 青岛出版社 / 2023-2 / 68.00元 ",
      "name": "狂飙"
    },
    {
      "comment": "9.0",
      "cover": "https://img9.doubanio.com/view/subject/s/public/s34303676.jpg",
      "id": "36084340",
      "info": " 蔡崇达 / 浙江文艺出版社、广州出版社 / 2022-9-5 / 59.80元 ",
      "name": "命运"
    },
    {
      "comment": "8.9",
      "cover": "https://img1.doubanio.com/view/subject/s/public/s2768378.jpg",
      "id": "2567698",
      "info": " 刘慈欣 / 重庆出版社 / 2008-1 / 23.00 ",
      "name": "三体"
    },
    {
      "comment": "8.3",
      "cover": "https://img1.doubanio.com/view/subject/s/public/s34295659.jpg",
      "id": "36073906",
      "info": " [智利]本哈明·拉巴图特 / 施杰 / 人民文学出版社 / 2022-9-1 / 59.00元 ",
      "name": "当我们不再理解世界"
    },
    {
      "comment": "8.5",
      "cover": "https://img2.doubanio.com/view/subject/s/public/s34201041.jpg",
      "id": "35875393",
      "info": " 张天翼 / 人民文学出版社 / 2022-4-1 / 58 ",
      "name": "如雪如山"
    },
    {
      "comment": "7.1",
      "cover": "https://img9.doubanio.com/view/subject/s/public/s34400654.jpg",
      "id": "36074757",
      "info": " [日本] 东野圭吾 / 李盈春 / 南海出版公司 / 2023-3 / 69.00元 ",
      "name": "白鸟与蝙蝠"
    },
    {
      "comment": "8.2",
      "cover": "https://img9.doubanio.com/view/subject/s/public/s33855006.jpg",
      "id": "35192665",
      "info": " 双雪涛 / 北京日报出版社 / 2021-4 / 59 ",
      "name": "平原上的摩西"
    },
    {
      "comment": "9.0",
      "cover": "https://img1.doubanio.com/view/subject/s/public/s33640730.jpg",
      "id": "34998019",
      "info": " 杨本芬 / 北京联合出版公司 / 2020-6 / 38.00元 ",
      "name": "秋园"
    },
    {
      "comment": "9.0",
      "cover": "https://img2.doubanio.com/view/subject/s/public/s34358582.jpg",
      "id": "36155568",
      "info": " 马伯庸 / 上海文艺出版社 / 2022-12 / 108.00元 ",
      "name": "大医·日出篇"
    },
    {
      "comment": "8.6",
      "cover": "https://img9.doubanio.com/view/subject/s/public/s34293555.jpg",
      "id": "36069426",
      "info": " 马伯庸 / 上海文艺出版社 / 2022-9 / 108.00元 ",
      "name": "大医·破晓篇"
    },
    {
      "comment": "9.4",
      "cover": "https://img1.doubanio.com/view/subject/s/public/s29053580.jpg",
      "id": "4913064",
      "info": " 余华 / 作家出版社 / 2012-8-1 / 20.00元 ",
      "name": "活着"
    },
    {
      "comment": "9.3",
      "cover": "https://img2.doubanio.com/view/subject/s/public/s3078482.jpg",
      "id": "3066477",
      "info": " 刘慈欣 / 重庆出版社 / 2008-5 / 32.00 ",
      "name": "三体Ⅱ"
    },
    {
      "comment": "8.9",
      "cover": "https://img2.doubanio.com/view/subject/s/public/s33685372.jpg",
      "id": "35031587",
      "info": " [日] 叶真中显 / 林佩瑾 / 北京联合出版公司 / 2020-7 / 58.00元 ",
      "name": "绝叫"
    },
    {
      "comment": "9.2",
      "cover": "https://img9.doubanio.com/view/subject/s/public/s26012674.jpg",
      "id": "5363767",
      "info": " 刘慈欣 / 重庆出版社 / 2010-11 / 38.00元 ",
      "name": "三体Ⅲ"
    },
    {
      "comment": "9.0",
      "cover": "https://img1.doubanio.com/view/subject/s/public/s34273798.jpg",
      "id": "36021908",
      "info": " 葛亮 / 人民文学出版社 / 2022-8 / 78 ",
      "name": "燕食记"
    },
    {
      "comment": "8.3",
      "cover": "https://img2.doubanio.com/view/subject/s/public/s34072342.jpg",
      "id": "35695541",
      "info": " 杨本芬 / 北京联合出版公司 / 2022-2-1 / 39.80 ",
      "name": "我本芬芳"
    },
    {
      "comment": "8.8",
      "cover": "https://img2.doubanio.com/view/subject/s/public/s3697882.jpg",
      "id": "3633461",
      "info": " 刘震云 / 长江文艺出版社 / 2009-3 / 29.80 ",
      "name": "一句顶一万句"
    },
    {
      "comment": "9.1",
      "cover": "https://img9.doubanio.com/view/subject/s/public/s33450235.jpg",
      "id": "34432750",
      "info": " 迟子建 / 人民文学出版社 / 2019-6-1 / 32.00元 ",
      "name": "额尔古纳河右岸"
    },
    {
      "comment": "8.6",
      "cover": "https://img2.doubanio.com/view/subject/s/public/s34400651.jpg",
      "id": "36062363",
      "info": " [日本] 夏目漱石、[日本] 太宰治 等 / 王子豪 / 广西师范大学出版社 / 2023-2 / 65.00 ",
      "name": "月海与游梦人"
    }
  ],
  "code": 200
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|成功|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» books|[object]|true|none||none|
|»» comment|string|true|none||none|
|»» cover|string|true|none||none|
|»» id|string|true|none||none|
|»» info|string|true|none||none|
|»» name|string|true|none||none|
|» code|integer|true|none||none|

## GET 搜索

GET /search

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|q|query|string| 是 |搜索内容|

> 返回示例

> 成功

```json
{
  "author": {
    "id": 4514884,
    "img": "https://img1.doubanio.com/view/personage/raw/public/d3c8174f362ab45c39ffaa1e74ccbe59.jpg",
    "info": "作者 / 1955-02-17 / 生死疲劳 / 檀香刑 / 蛙",
    "name": "莫言 Yan Mo"
  },
  "books": [
    {
      "comment_count": 22969,
      "cover": "https://img1.doubanio.com/view/subject/m/public/s34086258.jpg",
      "id": 35587028,
      "info": "莫言 / 浙江文艺出版社 / 2022-1 / 69.90",
      "name": "生死疲劳",
      "rating": 9.1
    },
    {
      "comment_count": 22251,
      "cover": "https://img1.doubanio.com/view/subject/m/public/s33562530.jpg",
      "id": 26905337,
      "info": "莫言 / 浙江文艺出版社 / 2017-1 / 56.00元",
      "name": "檀香刑",
      "rating": 9.2
    },
    {
      "comment_count": 14158,
      "cover": "https://img1.doubanio.com/view/subject/m/public/s33895248.jpg",
      "id": 26904658,
      "info": "莫言 / 浙江文艺出版社 / 2017-1 / 49.00",
      "name": "丰乳肥臀",
      "rating": 8.8
    },
    {
      "comment_count": 17528,
      "cover": "https://img9.doubanio.com/view/subject/m/public/s33895236.jpg",
      "id": 26904483,
      "info": "莫言 / 浙江文艺出版社 / 2017-1 / 37.00元",
      "name": "蛙",
      "rating": 8.9
    },
    {
      "comment_count": 15286,
      "cover": "https://img1.doubanio.com/view/subject/m/public/s33696230.jpg",
      "id": 35141940,
      "info": "莫言 / 人民文学出版社 / 2020-8-1 / 59",
      "name": "晚熟的人",
      "rating": 7.9
    },
    {
      "comment_count": 2293,
      "cover": "https://img1.doubanio.com/view/subject/m/public/s33895260.jpg",
      "id": 26904661,
      "info": "莫言 / 浙江文艺出版社 / 2017-1 / 69.00元",
      "name": "天堂蒜薹之歌",
      "rating": 8.9
    },
    {
      "comment_count": 7517,
      "cover": "https://img9.doubanio.com/view/subject/m/public/s33895205.jpg",
      "id": 26905339,
      "info": "莫言 / 浙江文艺出版社 / 2017-1 / 49.00元",
      "name": "红高粱家族",
      "rating": 8.8
    },
    {
      "comment_count": 4037,
      "cover": "https://img1.doubanio.com/view/subject/m/public/s33895267.jpg",
      "id": 26904516,
      "info": "莫言 / 浙江文艺出版社 / 2017-1 / 49.00元",
      "name": "酒国",
      "rating": 8.1
    },
    {
      "comment_count": 19,
      "cover": "https://img1.doubanio.com/view/subject/m/public/s24451898.jpg",
      "id": 20406947,
      "info": "莫言 / 百花文艺出版社 / 2012-12 / 998.00元",
      "name": "莫言诺贝尔奖典藏文集（全二十册） : 全新修订版莫言文集",
      "rating": 9.4
    },
    {
      "comment_count": 6634,
      "cover": "https://img2.doubanio.com/view/subject/m/public/s33895232.jpg",
      "id": 35041507,
      "info": "莫言 / 浙江文艺出版社 / 2020-3 / 66.00元",
      "name": "生死疲劳 : 2020修订升级版",
      "rating": 8.9
    },
    {
      "comment_count": 936,
      "cover": "https://img9.doubanio.com/view/subject/m/public/s33665086.jpg",
      "id": 35096959,
      "info": "莫言 / 浙江文艺出版社 / 2020-7 / 49.00元",
      "name": "透明的红萝卜 : 莫言中篇小说精品系列1",
      "rating": 8.5
    },
    {
      "comment_count": 137,
      "cover": "https://img1.doubanio.com/view/subject/m/public/s33666579.jpg",
      "id": 34974328,
      "info": "莫言 / 浙江文艺出版社 / 2020-7 / 49.00元",
      "name": "梦境与杂种 : 莫言中篇小说精品系列6",
      "rating": 9.1
    },
    {
      "comment_count": 663,
      "cover": "https://img9.doubanio.com/view/subject/m/public/s33895264.jpg",
      "id": 26920399,
      "info": "莫言 / 浙江文艺出版社 / 2017-1 / 37.00元",
      "name": "十三步",
      "rating": 7.9
    },
    {
      "comment_count": 724,
      "cover": "https://img9.doubanio.com/view/subject/m/public/s22792335.jpg",
      "id": 19977686,
      "info": "莫言 / 上海文艺出版社 / 2012-10 / 37.00元",
      "name": "四十一炮 : 莫言作品系列",
      "rating": 7.5
    },
    {
      "comment_count": 16,
      "cover": "https://img1.doubanio.com/view/subject/m/public/s33490340.jpg",
      "id": 34842272,
      "info": "莫言 / 浙江文艺出版社 / 2019-7 / 69.00元",
      "name": "讲故事的人 : 莫言作品典藏大系（卷24）",
      "rating": 9.3
    }
  ],
  "code": 200,
  "msg": "success"
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|成功|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» author|object|true|none||none|
|»» id|integer|true|none||none|
|»» img|string|true|none||none|
|»» info|string|true|none||none|
|»» name|string|true|none||none|
|» books|[object]|true|none||none|
|»» comment_count|integer|true|none||none|
|»» cover|string|true|none||none|
|»» id|integer|true|none||none|
|»» info|string|true|none||none|
|»» name|string|true|none||none|
|»» rating|number|true|none||none|
|» code|integer|true|none||none|
|» msg|string|true|none||none|

## GET 获取书籍详情

GET /getBookDetail

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|id|query|string| 是 |不能为空，豆瓣的i图书d|

> 返回示例

> 成功

```json
{
  "book": {
    "ISBN": "9787100215220",
    "auther": "[英]安斯加·艾伦",
    "auther_introduction": " 继《虚无主义》后，“交界译丛”又一力作！ 徐贲、徐英瑾 推荐 每个人或许都有自己的“犬儒时刻”，是屈服于心中的“黑暗面”，还是拨开迷雾，迎接真相？还原犬儒主义的真面目，激活思想潜流的真精神。 认识犬儒主义，重识时代，直面自我！ 【编辑推荐】 ★犬儒主义是什么？ 古希腊哲 学家在大街上狗一般的 野生状态； 近代知识分子在认同焦虑与深深失望间摇摆的社会心态； 在社交媒体上匿名冷嘲热讽、在现实中唯唯诺诺的普通人…… 愤世嫉俗？玩世不恭？缺乏羞耻心? 深入浅出，系统阐明古今犬儒主义流变简史。 还原犬儒主义的真面目，激活思想潜流的真精神。 ★为什么要认识犬儒主义？ 数千年来，犬儒主义始终紧扣各自的时代： 公元前4世纪，第欧根尼让亚历山大大帝走开，不要挡住阳光； 文艺复兴时期，犬儒主义者形象在莎士比亚的作品中重生； 19世纪，尼采借用犬儒主义，试探“另一种生活”的可能性； 如今，犬儒主义表现为巨婴式的、无休止的失望与不满…… 了解一个时代的犬儒主义，就是窥见那个时代的侧面。 ★直面自我，写给对思想抱有热情的你、我、他 遴选自“麻省理工大学出版社基本知识系列”丛书，汇集各领域专家，专为大众读者写作。 以显白之语，丰富注释，深入解读与日常息息相关的专业议题。 大字反色插页，随文提示核心要点，面对复杂世界不迷失！ 拨开纷纷扰扰，认清犬儒主义，走出情绪， 重新定位和思考自身，拥抱更好的自我！ 【内容简介】 每个人或许都有自己的“犬儒时刻”。 每当陷入绝望，我们内心深处总会有一个声音：“我恨变得愤世嫉俗，但是……” 愤世嫉俗？玩世不恭？缺乏羞耻心？…… 犬儒主义是什么？什么样的人可以称为犬儒主义者？我们都是犬儒主义者？ 从木桶中特立独行的哲学家到网络时代涨落不停的不良情绪，作者安斯加尔·艾伦描绘了从公元前4世纪希腊犬儒主义者的“无畏直言”到当代多面、复杂的犬儒主义表现的历史。借助其后莎士比亚、拉伯雷、卢梭等人的著作，本书记录了文艺复兴和启蒙运动对犬儒主义的挪用；通过尼采、福柯、斯劳特戴克等哲学家的思想，作者追踪了犬儒主义从古代到现代的转变，并重新思考了现代犬儒主义在当代社会中的地位和作用，不仅梳理、提炼了哲学史层面上的知识，更能帮助我们在对犬儒主义的认识和反思中，重新定位和思考我们自身。 【学者推荐】 本书呼吁人们行动起来，同时深思熟虑地介绍了犬儒主义，适合所有层次的读者。 ——休·罗伯茨（Hugh Roberts） 强烈推荐给学生群体，也推荐给未来的教育工作者。本书所汇集的各种当代读物和对它们的反思，代表了对当下全貌的杰出贡献。 ——圣地亚哥·瓦尔加斯·奥利瓦（Santiago Vargas Oliva） 可以说，犬儒主义是苏格拉底传统中最具原创性和影响力的分支，从上个世纪开始，由于斯洛特迪克、福柯和巴赫金等人的工作，犬儒主义已成为学术界重新关注的焦点。安斯加尔·艾伦 的《犬儒主义》是近年来的最新进展之一。艾伦展示了犬儒主义如何从古希腊人的无畏言论演化成现当代的厌世消极，进而帮助我们探索犬儒主义所激发的伦理、社会和文化实践问题。社会底层的犬儒主义虽然有一些弱者抵抗的价值，但它接受了作为“既成事实”的社会环境，并“以生存和收益的名义尽可能去适应现实“。它很容易与权力阶层的犬儒主义合流，成为当代社会的主要危险——政治绝望和放弃个人责任。虽然犬儒主义一直处于哲学的边缘，但它仍然是今天致力于社会和文化变革者的重要试金石。 ——徐贲（美国加州圣玛丽学院英文系教授，复旦大学社科高研院兼职教授。著有《颓废与沉默：透视犬儒文化》《犬儒与玩笑：假面社会的政治幽默》等） 对于中国的西学研究来说，晚期希腊哲学与罗马哲学似乎是一个没有存在感的领域。无论是本书涉及的犬儒主义，还是大致属于同一个时期的皮浪主义、伊壁鸠鲁主义、斯多葛主义，都在很多人的学术手电的照耀范围之外。殊不知对于当下年轻人的倦怠感与躺平状态而言，这些过渡时期的哲学思想才能 提供足够的解释资源。譬如，难道我们在当下年轻人的“不买房宣言”里不能看到顶着大木桶行走在雅典街头的犬儒主义大师第欧根尼的身影吗？也正是基于这种直觉，本书作者艾伦淡化了学界在古典犬儒主义与现代犬儒主义之间划下的楚河汉界，并通过这种策略试图让古典犬儒主义的意义在现代被激活。或许读完此书之后，读者会重估犬儒主义的当代意义，并重新思考目下种种人生选择的合理性。 —— 徐英瑾（复旦大学哲学学院 教授） 福柯和斯洛特戴克克关于犬儒主义的著作出版以后，犬儒主义这一长久沉默的古代哲学学派重新引起了人们的注意。对犬儒主义而言，哲学是一种特殊的生活方式而不仅仅是理论教义。这样一个生活哲学传统在漫长的欧洲历史中一直若隐若现地出没。这本书不仅仅是对这个传统简明扼要的清晰展示，而且还厘清了它在不同时代的各种变形、内在冲突以及它作为遗产的价值和意义之所在。 ——汪民安（清华大学人文学院中文系教授） “Cynicism”，一个 无法翻译的词，到处都能遇到带有”cynicism”性质的表述，可是要下一个简短的定义却是一项无法完成的任务，因为它的力量和它的弱点，人们喜欢它的地方和抵触它的地方，都是彼此混合的，它“冷漠厌世”的内涵可用于抵抗虛伪、欺诈，也能伤害诚挚的人心，它是一个人心智成熟的标志，同时又是他走向极端的起点。 对“cynicism”的常见中译“犬儒主义”，很少被人用对过。它看上去好像在说那些懦弱、卑屈的知识分子，然而实际上，“犬儒”的创始人第欧根尼所倡导的“狗一样活着”，不仅气懦弱无关，而且还向体制化的教育、体制化的人格培养射出了最犀利的箭矢。 本书作者艾伦精准地找到了“cynicism”最爱针对的对象，那就是受教育者的“耻感”，他们在面对“无耻”行为时会局促不安。不过,“cynicism”在历史沿革中，因为结合于其他各路思潮，被众多的文艺作品吸收，而变得面相极多。艾伦的这本梳理性作品，可以说是做了一件超高难度的工作。 ——云也退（作家、书评人、译者） 这是一部记述明畅、辨析深入的思想论著。在对“犬儒主义”这一哲学思潮的历史追索中，作者特别注重区别“古代犬儒主义”(Cynicism）与“现代犬儒主义” (cynicism)二者，后者是近代以来人们逐渐将一些特定的意涵附丽于传统术语的、层累式的概念。“古代犬儒主义”的代表人物是第欧根尼，他在公众面前的特立独行之举，挑战了当时标准的文明与道德的观念。在作者看来,第欧根尼在演说后当众拉屎的行为，其实是把耻感置于教育的核心位置：“古代犬儒派试图逃离由 ‘丢脸’所强制的那种羞耻与服从的秩序。”对于“现代犬儒主义”，作者做了有力的批判，指出它很可能只是一种逃避和自我欺骗，尤其会产生消极影响的，是当代的犬儒主义者“对公民职责和社会责任的搁置”。这样一部明快、清醒、引深思的作品，对当下的中国读者似乎别具意味。 ——乔纳森（书评人） 【丛书简介】 交界，谓边际相连，有共同疆界，寓意抵达前沿、跨越分歧、建立共识之可能。该丛书围绕当下公众或思想界聚焦的主题，提供由各领域专家撰写的知识概述，从基础原理出发，逐步切入关键论题，使读者得以理解并探讨更为复杂的观念。",
    "comment": {
      "star1": "0.0",
      "star2": "1.4",
      "star3": "11.0",
      "star4": "31.5",
      "star5": "56.2"
    },
    "cover": "https://img1.doubanio.com/view/subject/s/public/s34418457.jpg",
    "introduction": " 继《虚无主义》后，“交界译丛”又一力作！ 徐贲、徐英瑾 推荐 每个人或许都有自己的“犬儒时刻”，是屈服于心中的“黑暗面”，还是拨开迷雾，迎接真相？还原犬儒主义的真面目，激活思想潜流的真精神。 认识犬儒主义，重识时代，直面自我！ 【编辑推荐】 ★犬儒主义是什么？ 古希腊哲 学家在大街上狗一般的 野生状态； 近代知识分子在认同焦虑与深深失望间摇摆的社会心态； 在社交媒体上匿名冷嘲热讽、在现实中唯唯诺诺的普通人…… 愤世嫉俗？玩世不恭？缺乏羞耻心? 深入浅出，系统阐明古今犬儒主义流变简史。 还原犬儒主义的真面目，激活思想潜流的真精神。 ★为什么要认识犬儒主义？ 数千年来，犬儒主义始终紧扣各自的时代： 公元前4世纪，第欧根尼让亚历山大大帝走开，不要挡住阳光； 文艺复兴时期，犬儒主义者形象在莎士比亚的作品中重生； 19世纪，尼采借用犬儒主义，试探“另一种生活”...",
    "name": "犬儒主义",
    "price": "75",
    "publisher": "商务印书馆",
    "score": "9.1",
    "score_num": "73"
  },
  "code": 200
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|成功|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» book|object|true|none||none|
|»» ISBN|string|true|none||none|
|»» auther|string|true|none||none|
|»» auther_introduction|string|true|none||none|
|»» comment|object|true|none||none|
|»»» star1|string|true|none||none|
|»»» star2|string|true|none||none|
|»»» star3|string|true|none||none|
|»»» star4|string|true|none||none|
|»»» star5|string|true|none||none|
|»» cover|string|true|none||none|
|»» introduction|string|true|none||none|
|»» name|string|true|none||none|
|»» price|string|true|none||none|
|»» publisher|string|true|none||none|
|»» score|string|true|none||none|
|»» score_num|string|true|none||none|
|» code|integer|true|none||none|

## GET 获取新书

GET /getNewBook

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|page|query|string| 否 |分页，从0开始（默认为0）|
|type|query|string| 否 |全部（默认）、文学、小说、历史文化、 社会纪实 、科学新知、艺术设计、商业经管、绘本漫画|

> 返回示例

> 成功

```json
{
  "books": [
    {
      "auther": " [法]玛格丽特·杜拉斯 ",
      "comment": "8.6",
      "cover": "https://img9.doubanio.com/view/subject/s/public/s34395096.jpg",
      "id": "36168765",
      "name": "战时笔记和其他",
      "price": " 69 ",
      "publish": " 中信出版社 "
    },
    {
      "auther": " [日本] 铃木凉美 ",
      "comment": "8.4",
      "cover": "https://img1.doubanio.com/view/subject/s/public/s34501399.jpg",
      "id": "36285832",
      "name": "献给爱与子宫的花束：夜女郎的母女论",
      "price": " 59.00 ",
      "publish": " 广西师范大学出版社 "
    },
    {
      "auther": " [英] 约翰·济慈 ",
      "comment": "9.4",
      "cover": "https://img2.doubanio.com/view/subject/s/public/s34432553.jpg",
      "id": "36108578",
      "name": "伊莎贝拉：插图珍藏版",
      "price": " 江苏凤凰文艺出版社 ",
      "publish": " 2023-3 "
    },
    {
      "auther": " (美) 西尔维娅·普拉斯 ",
      "comment": "8.6",
      "cover": "https://img1.doubanio.com/view/subject/s/public/s34397830.jpg",
      "id": "36223089",
      "name": "精灵：普拉斯诗集",
      "price": " 65 ",
      "publish": " 北京联合出版公司 "
    },
    {
      "auther": " 栾颖新 ",
      "comment": "9.2",
      "cover": "https://img9.doubanio.com/view/subject/s/public/s34459226.jpg",
      "id": "36234556",
      "name": "那个苹果也很好：在巴黎学会自由",
      "price": " 59.80 ",
      "publish": " 湖南文艺出版社 "
    },
    {
      "auther": " 钱理群 ",
      "comment": "5.4",
      "cover": "https://img2.doubanio.com/view/subject/s/public/s34502663.jpg",
      "id": "36361500",
      "name": "中国现代文学新讲",
      "price": " 129.00 ",
      "publish": " 九州出版社 "
    },
    {
      "auther": " [波]切斯瓦夫·米沃什 ",
      "comment": "9.1",
      "cover": "https://img2.doubanio.com/view/subject/s/public/s34465761.jpg",
      "id": "36229551",
      "name": "旧金山海湾景象",
      "price": " 68.00 ",
      "publish": " 广西师范大学出版社 "
    },
    {
      "auther": " 周志文 ",
      "comment": "8.7",
      "cover": "https://img9.doubanio.com/view/subject/s/public/s34470366.jpg",
      "id": "36226439",
      "name": "巡礼之年 （全三册）：野姜花/井旁边大门前面/横式风景",
      "price": " 108.00 ",
      "publish": " 上海社会科学院出版社 "
    },
    {
      "auther": " [英] 詹姆斯·鲍斯威尔 ",
      "comment": "9.4",
      "cover": "https://img2.doubanio.com/view/subject/s/public/s34484682.jpg",
      "id": "36145658",
      "name": "约翰生传：全译本",
      "price": " 698.00 ",
      "publish": " 上海译文出版社 "
    },
    {
      "auther": " 赖慈芸 ",
      "comment": "7.8",
      "cover": "https://img1.doubanio.com/view/subject/s/public/s34486450.jpg",
      "id": "36246347",
      "name": "翻译侦探事务所",
      "price": " 45.00 ",
      "publish": " 生活·读书·新知三联书店 "
    },
    {
      "auther": " 亦凡 ",
      "comment": "9.1",
      "cover": "https://img1.doubanio.com/view/subject/s/public/s34375900.jpg",
      "id": "36084858",
      "name": "晚安也是早安",
      "price": " 68 ",
      "publish": " 安徽文艺出版社 "
    },
    {
      "auther": " 骆以军 ",
      "comment": "7.9",
      "cover": "https://img1.doubanio.com/view/subject/s/public/s34474008.jpg",
      "id": "36175324",
      "name": "无限阅读",
      "price": " 70.00 ",
      "publish": " 上海文艺出版社 "
    },
    {
      "auther": " [英]C.S.路易斯 ",
      "comment": "",
      "cover": "https://img1.doubanio.com/view/subject/s/public/s34462610.jpg",
      "id": "36235388",
      "name": "论《失乐园》",
      "price": " 68 ",
      "publish": " 华东师范大学出版社 "
    },
    {
      "auther": " [加]戴维·斯泰恩斯 ",
      "comment": "",
      "cover": "https://img1.doubanio.com/view/subject/s/public/s34484680.jpg",
      "id": "36285086",
      "name": "遇见自己：艾丽丝·门罗剑桥文学指南",
      "price": " 69.00 ",
      "publish": " 陕西人民出版社 "
    },
    {
      "auther": " [英] 威廉·莎士比亚 ",
      "comment": "",
      "cover": "https://img2.doubanio.com/view/subject/s/public/s34478161.jpg",
      "id": "36127412",
      "name": "莎士比亚悲剧集：插图珍藏版",
      "price": " 江苏凤凰文艺出版社 ",
      "publish": " 2023-4 "
    },
    {
      "auther": " [英] A.S. 拜厄特 ",
      "comment": "8.8",
      "cover": "https://img1.doubanio.com/view/subject/s/public/s34368820.jpg",
      "id": "36179107",
      "name": "小说中的肖像",
      "price": " 48.00 ",
      "publish": " 上海三联书店 "
    },
    {
      "auther": " [法]让-吕克·斯坦梅茨 ",
      "comment": "",
      "cover": "https://img9.doubanio.com/view/subject/s/public/s34465986.jpg",
      "id": "36170476",
      "name": "兰波传：追寻天才诗人的足迹",
      "price": " 精装 <",
      "publish": " 商务印书馆 "
    },
    {
      "auther": " [新西兰]伊恩·特拉福德 ",
      "comment": "9.0",
      "cover": "https://img1.doubanio.com/view/subject/s/public/s34414957.jpg",
      "id": "36246339",
      "name": "茫：士兵日记1916-1919",
      "price": " 68.00 ",
      "publish": " 中国工人出版社 "
    },
    {
      "auther": " [日]小川糸 ",
      "comment": "8.9",
      "cover": "https://img1.doubanio.com/view/subject/s/public/s34472559.jpg",
      "id": "36234533",
      "name": "悠悠荡荡小天国",
      "price": " 49.8 ",
      "publish": " 湖南文艺出版社 "
    }
  ],
  "code": 200
}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|成功|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» books|[object]|true|none||none|
|»» auther|string|true|none||none|
|»» comment|string|true|none||none|
|»» cover|string|true|none||none|
|»» id|string|true|none||none|
|»» name|string|true|none||none|
|»» price|string|true|none||none|
|»» publish|string|true|none||none|
|» code|integer|true|none||none|

# 错误码

|代码|名称|说明|
|---|---|---|
|200|成功||
|10020|参数错误|缺少参数|
|10021|参数为空|参数为空，你好像还没给参数赋值|
|10022|页数异常|页数不能小于等于0|


