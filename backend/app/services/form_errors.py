"""Các lỗi của luồng bóc tách Google Form (hiển thị thông báo tiếng Việt cho người dùng)."""

from __future__ import annotations


class FormParserError(Exception):
    """Lỗi gốc của module bóc tách form."""


class InvalidFormUrlError(FormParserError):
    pass


class FormFetchError(FormParserError):
    pass


class FormRequiresLoginError(FormParserError):
    pass


class FormClosedError(FormParserError):
    pass


class FormStructureError(FormParserError):
    pass
