"""统一错误类型与业务错误码。

兼容旧版：10020 / 10021 / 10022 语义保持不变，新增错误码见 ``ERROR_CODES``。
"""

from __future__ import annotations

from typing import Any

ERROR_CODES: dict[int, str] = {
    10020: "参数错误或缺失",
    10021: "参数为空",
    10022: "页数不能小于等于 0",
    10030: "上游（豆瓣）请求失败或超时",
    10040: "目标内容不存在",
    10050: "请求过于频繁，请稍后重试",
    10060: "上游响应解析失败",
    10070: "服务内部错误",
}


class ApiError(Exception):
    """可直接序列化为 ``{"code": ..., "msg": ...}`` 的业务异常。"""

    code: int = 10070
    http_status: int = 500
    msg: str = "服务内部错误"

    def __init__(
        self,
        msg: str | None = None,
        *,
        code: int | None = None,
        http_status: int | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(msg or self.msg)
        if code is not None:
            self.code = code
        if http_status is not None:
            self.http_status = http_status
        if msg:
            self.msg = msg
        self.extra = extra or {}

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"code": self.code, "msg": self.msg}
        payload.update(self.extra)
        return payload


class ValidationError(ApiError):
    http_status = 400
    code = 10020
    msg = "参数错误"


class EmptyParamError(ApiError):
    http_status = 400
    code = 10021
    msg = "参数为空"


class UpstreamError(ApiError):
    http_status = 502
    code = 10030
    msg = "上游（豆瓣）请求失败或超时"


class NotFoundError(ApiError):
    http_status = 404
    code = 10040
    msg = "目标内容不存在"


class ParseError(ApiError):
    http_status = 502
    code = 10060
    msg = "上游响应解析失败"


class RateLimitedError(ApiError):
    http_status = 429
    code = 10050
    msg = "请求过于频繁，请稍后重试"
