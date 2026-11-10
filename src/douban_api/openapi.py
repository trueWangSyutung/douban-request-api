"""OpenAPI 3.1 规范（唯一来源）。

``/openapi.json`` 直接返回本模块生成的对象；文档站构建时导出成
``docs/openapi.json`` 供 Redoc 渲染，CI 会校验两者没有漂移。
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .version import __version__

BOOK = {
    "type": "object",
    "description": "列表页图书条目",
    "properties": {
        "id": {"type": "string", "example": "2567698"},
        "name": {"type": "string", "example": "三体"},
        "cover": {"type": "string", "format": "uri"},
        "url": {"type": "string", "format": "uri"},
        "info": {"type": "string", "example": "刘慈欣 / 重庆出版社 / 2008-1 / 23.00元"},
        "auther": {"type": "string", "description": "作者（历史字段名，拼写保持兼容）"},
        "publisher": {"type": "string"},
        "publish_date": {"type": "string"},
        "price": {"type": "string", "example": "23.00"},
        "binding": {"type": "string"},
        "comment": {"type": "string", "description": "评分，如 8.9"},
        "rating_count": {"type": "string", "description": "评价人数"},
        "rating": {"type": ["number", "null"]},
        "comment_count": {"type": ["integer", "null"]},
    },
}

DETAIL = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "url": {"type": "string", "format": "uri"},
        "name": {"type": "string"},
        "cover": {"type": "string"},
        "auther": {"type": "string"},
        "authors": {"type": "array", "items": {"type": "string"}},
        "publisher": {"type": "string"},
        "producer": {"type": "string"},
        "publish_date": {"type": "string"},
        "pages": {"type": "string"},
        "binding": {"type": "string"},
        "price": {"type": "string"},
        "ISBN": {"type": "string"},
        "subtitle": {"type": "string"},
        "original_title": {"type": "string"},
        "translator": {"type": "string"},
        "series": {"type": "string"},
        "score": {"type": "string", "example": "8.9"},
        "score_num": {"type": "string", "example": "519247"},
        "comment": {
            "type": "object",
            "properties": {
                f"star{i}": {"type": "string", "description": "百分比"} for i in range(1, 6)
            },
        },
        "introduction": {"type": "string"},
        "auther_introduction": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "info": {"type": "object", "additionalProperties": {"type": "string"}},
    },
}

ERROR = {
    "type": "object",
    "required": ["code", "msg"],
    "properties": {
        "code": {"type": "integer", "example": 10020},
        "msg": {"type": "string", "example": "参数错误"},
    },
}

META = {
    "type": "object",
    "properties": {
        "cached": {"type": "boolean", "description": "是否命中缓存"},
        "elapsed_ms": {"type": "number"},
        "version": {"type": "string"},
        "ttl": {"type": "integer"},
    },
}


def _ok(schema: dict[str, Any], description: str) -> dict[str, Any]:
    return {
        "get": {
            "summary": description,
            "parameters": [],
            "responses": {
                "200": {
                    "description": "成功",
                    "content": {"application/json": {"schema": schema}},
                },
                "400": {
                    "description": "参数错误",
                    "content": {"application/json": {"schema": ERROR}},
                },
                "404": {
                    "description": "资源不存在",
                    "content": {"application/json": {"schema": ERROR}},
                },
                "429": {
                    "description": "触发限流",
                    "content": {"application/json": {"schema": ERROR}},
                },
                "502": {
                    "description": "上游失败",
                    "content": {"application/json": {"schema": ERROR}},
                },
            },
        }
    }


def _q(name: str, description: str, *, required: bool = False, schema: dict | None = None) -> dict:
    return {
        "name": name,
        "in": "query",
        "required": required,
        "description": description,
        "schema": schema or {"type": "string"},
    }


def build_spec(base_url: str = "https://bookapi.oaixiv.org") -> dict[str, Any]:
    spec: dict[str, Any] = {
        "openapi": "3.1.0",
        "info": {
            "title": "豆瓣图书查询 API",
            "version": __version__,
            "description": (
                "基于 Flask + lxml 的豆瓣图书信息聚合接口。带 TTL 缓存、单飞合并、gzip、"
                "ETag/304、限流与上游重试。请勿高频遍历，数据版权归豆瓣所有。"
            ),
            "license": {
                "name": "MIT",
                "url": "https://github.com/trueWangSyutung/douban-request-api/blob/master/license",
            },
        },
        "servers": [
            {"url": base_url, "description": "在线 API（Cloudflare Worker）"},
            {"url": "http://127.0.0.1:5000", "description": "本地开发"},
            {
                "url": "https://trueWangSyutung.github.io/douban-request-api/api/v1",
                "description": "GitHub Pages 静态快照（只读）",
            },
        ],
        "tags": [
            {"name": "图书", "description": "列表、详情"},
            {"name": "搜索", "description": "关键词搜索"},
            {"name": "系统", "description": "健康检查与指标"},
        ],
        "path_servers": {},
        "paths": {},
        "components": {
            "schemas": {
                "Book": BOOK,
                "BookDetail": DETAIL,
                "Error": ERROR,
                "Meta": META,
            }
        },
    }
    paths = spec["paths"]
    paths["/api/v1/books/latest"] = _ok(
        {
            "type": "object",
            "properties": {
                "code": {"type": "integer", "example": 200},
                "type": {"type": "string"},
                "page": {"type": "integer"},
                "books": {"type": "array", "items": BOOK},
                "meta": META,
            },
        },
        "获取最新图书",
    )
    paths["/api/v1/books/latest"]["get"]["parameters"] = [
        _q("type", "分类，默认「全部」，取值见豆瓣最新图书页", required=False),
        _q("page", "页码，从 0 开始", schema={"type": "integer", "minimum": 0, "default": 0}),
    ]
    paths["/api/v1/books/latest"]["get"]["tags"] = ["图书"]

    paths["/api/v1/books/tag"] = _ok(
        {
            "type": "object",
            "properties": {
                "code": {"type": "integer", "example": 200},
                "tag": {"type": "string"},
                "page": {"type": "integer"},
                "books": {"type": "array", "items": BOOK},
                "meta": META,
            },
        },
        "按标签获取图书",
    )
    paths["/api/v1/books/tag"]["get"]["parameters"] = [
        _q("tag", "标签名，例如 小说 / 历史 / 科幻", required=True),
        _q("page", "页码，从 1 开始", schema={"type": "integer", "minimum": 1, "default": 1}),
    ]
    paths["/api/v1/books/tag"]["get"]["tags"] = ["图书"]

    paths["/api/v1/books/{id}"] = _ok(
        {
            "type": "object",
            "properties": {
                "code": {"type": "integer", "example": 200},
                "book": DETAIL,
                "meta": META,
            },
        },
        "获取图书详情",
    )
    paths["/api/v1/books/{id}"]["get"]["parameters"] = [
        {
            "name": "id",
            "in": "path",
            "required": True,
            "description": "豆瓣图书 ID（4-12 位数字）",
            "schema": {"type": "string", "pattern": r"^\d{4,12}$"},
            "example": "2567698",
        }
    ]
    paths["/api/v1/books/{id}"]["get"]["tags"] = ["图书"]

    paths["/api/v1/search"] = _ok(
        {
            "type": "object",
            "properties": {
                "code": {"type": "integer", "example": 200},
                "msg": {"type": "string"},
                "q": {"type": "string"},
                "total": {"type": "integer"},
                "books": {"type": "array", "items": BOOK},
                "author": {"type": "object", "description": "命中作者时返回"},
                "series": {"type": "array", "items": {"type": "object"}},
                "meta": META,
            },
        },
        "关键词搜索图书",
    )
    paths["/api/v1/search"]["get"]["parameters"] = [
        _q("q", "搜索关键词", required=True, schema={"type": "string", "maxLength": 64}),
    ]
    paths["/api/v1/search"]["get"]["tags"] = ["搜索"]

    paths["/healthz"] = {
        "get": {
            "summary": "健康检查",
            "tags": ["系统"],
            "responses": {"200": {"description": "服务正常"}},
        }
    }
    paths["/metrics"] = {
        "get": {
            "summary": "运行指标（缓存命中率、上游请求数）",
            "tags": ["系统"],
            "responses": {"200": {"description": "指标"}},
        }
    }

    legacy = {
        "/getNewBook": ("获取最新图书（旧版路径）", ["type", "page"]),
        "/getType": ("按标签获取图书（旧版路径）", ["tag", "page"]),
        "/getBookDetail": ("获取图书详情（旧版路径）", ["id"]),
        "/search": ("关键词搜索（旧版路径）", ["q"]),
    }
    for path, (summary, _) in legacy.items():
        spec["paths"][path] = deepcopy(
            spec["paths"][
                {
                    "/getNewBook": "/api/v1/books/latest",
                    "/getType": "/api/v1/books/tag",
                    "/getBookDetail": "/api/v1/books/{id}",
                    "/search": "/api/v1/search",
                }[path]
            ]
        )
        spec["paths"][path]["get"]["summary"] = summary + "，等价于 /api/v1 接口"
        spec["paths"][path]["get"]["deprecated"] = True

    spec.pop("path_servers", None)
    return spec


OPENAPI_SPEC = build_spec()
