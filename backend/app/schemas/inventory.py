from pydantic import BaseModel


class WarehouseRow(BaseModel):
    codigo_bodega: str
    nombre_bodega: str
    stock: float
    comprometido: float
    pedido: float


class SaveInventoryRequest(BaseModel):
    codigo_articulo: str
    nombre_articulo: str
    grupo: str = ""
    unidad_venta: str = ""
    unidad_compra: str = ""
    almacen_predeterminado: str = ""
    activo: bool = True
    bodegas: list[WarehouseRow]
