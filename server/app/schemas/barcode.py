from pydantic import BaseModel


class ProductInfo(BaseModel):
    barcode: str
    name: str
    barcode_format: str
    mrp: str | None = None
    images: list[str]
    attributes: dict[str, str]
