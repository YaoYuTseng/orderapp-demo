from database.FieldSchema import FieldSchema

PAGES = {
    "/orders": "當日訂單",
    "/future_orders": "預約訂單",
    "/previous_orders": "過去訂單",
    "/recipes": "產品設定",
    "/materials": "材料成本",
    "/purchases": "採購紀錄",
    "/vendors": "廠商資料",
}

ORDERS_TEMPLATE: list[FieldSchema] = [
    FieldSchema(header_name="產品", field="product_name"),
    FieldSchema(header_name="數量", field="quantity"),
    FieldSchema(header_name="單位", field="uom_name"),
    FieldSchema(header_name="金額", field="price_total"),
]
PREVIOUS_ORDERS_OVERVIEW: list[FieldSchema] = [
    FieldSchema(header_name="日期", field="order_date"),
    FieldSchema(header_name="訂單", field="order_counts"),
    FieldSchema(header_name="總成本", field="summed_finished_cost"),
    FieldSchema(header_name="總收入", field="summed_finished_price"),
]

PREVIOUS_ORDERS_DETAIL: list[FieldSchema] = [
    FieldSchema(header_name="產品", field="product_name"),
    FieldSchema(header_name="數量", field="quantity"),
    FieldSchema(header_name="單位", field="uom_name"),
    FieldSchema(header_name="成本", field="products_cost"),
    FieldSchema(header_name="金額", field="price_total"),
]

PRODUCTS_TEMPLATE: list[FieldSchema] = [
    FieldSchema(header_name="產品名稱", field="product_name"),
    FieldSchema(header_name="單位", field="uom_name"),
    FieldSchema(header_name="定價", field="price"),
]

PRODUCTS_OVERVIEW_TEMPLATE: list[FieldSchema] = [
    FieldSchema(header_name="產品", field="product_name"),
    FieldSchema(header_name="單位", field="uom_name"),
    FieldSchema(header_name="定價", field="price"),
    FieldSchema(header_name="成本", field="cost_per_product"),
]

RECIPES_TEMPLATE: list[FieldSchema] = [
    FieldSchema(header_name="原料", field="material_name"),
    FieldSchema(header_name="每克成本", field="cost_per_material"),
    FieldSchema(header_name="克數", field="quantity"),
    FieldSchema(header_name="原料成本", field="total_material_cost"),
]

PURCHASES_OVERVIEW_TEMPLATE: list[FieldSchema] = [
    FieldSchema(header_name="訂購日期", field="purchase_date"),
    FieldSchema(header_name="廠商", field="vendor_name"),
    FieldSchema(header_name="原料", field="material_name_list"),
    FieldSchema(header_name="總金額", field="purchase_summed_price"),
]

PURCHASE_DETAILS_TEMPLATE: list[FieldSchema] = [
    FieldSchema(header_name="原料", field="material_name"),
    FieldSchema(header_name="克數", field="quantity"),
    FieldSchema(header_name="金額", field="price_total"),
]

MATERIALS_TEMPLATE: list[FieldSchema] = [
    FieldSchema(header_name="材料", field="material_name"),
    FieldSchema(header_name="庫存克數", field="material_stocked"),
    FieldSchema(header_name="每克金額", field="cost_per_material"),
]

VENDORS_OVERVIEW: list[FieldSchema] = [
    FieldSchema(header_name="廠商", field="vendor_name"),
    FieldSchema(header_name="市話", field="office_phone"),
    FieldSchema(header_name="統編", field="tax_id"),
]


VENDORS_TEMPLATE: list[FieldSchema] = [
    FieldSchema(header_name="廠商", field="vendor_name"),
    FieldSchema(header_name="市話", field="office_phone"),
    FieldSchema(header_name="手機", field="mobile_phone"),
    FieldSchema(header_name="地址", field="address"),
    FieldSchema(header_name="統編", field="tax_id"),
    FieldSchema(header_name="聯絡人", field="contact_name"),
    FieldSchema(header_name="聯絡人手機", field="contact_mobile_phone"),
    FieldSchema(header_name="營業日", field="open_days"),
    FieldSchema(header_name="註記", field="note"),
]
