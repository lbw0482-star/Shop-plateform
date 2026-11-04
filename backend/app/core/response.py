from typing import Any


def ok(data: Any = None, message: str = "success") -> dict[str, Any]:
    return {"data": data, "message": message}


def page(items: list[Any], total: int, page_no: int, page_size: int) -> dict[str, Any]:
    return {
        "items": items,
        "page": page_no,
        "page_size": page_size,
        "total": total,
    }

