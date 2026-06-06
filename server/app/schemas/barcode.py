from pydantic import BaseModel


class HsnInfo(BaseModel):
    hsn: str
    description: str
    gst: int


class ProductInfo(BaseModel):
    barcode: str
    name: str
    barcode_format: str
    mrp: str | None = None
    hsn: HsnInfo | None = None
    images: list[str]
    attributes: dict[str, str]
