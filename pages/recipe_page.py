from mysql.connector import MySQLConnection
from nicegui import ui

from database import queries
from database.DataAccessObjects import DaoRecipePage
from database.update_cost import update_costs

from . import constants, page_setup
from .components.Buttons import DropdownNavigate
from .components.ConfirmDialogs import ConfirmDeleteRecipe
from .components.GridOfCards import RecipeCards
from .components.InputDialogs import RecipeInputDialog
from .components.Notifications import NotifyAwaitInput
from .components.UpdateDialogs import RecipeUpdateDialog
from .components.UtilsAggrids import SelectableAggrid


def recipe_page(connection: MySQLConnection):
    page_setup.font_setup()
    page_setup.style_setup(
        responsive_ag=True, dense_card=True, dynamic_scroll_padding=True
    )
    DAO_RECIPE = DaoRecipePage(connection=connection)

    def reinitialize():
        # Reinitialize input dialog
        input_dialog.refresh()
        existed_products = [
            i["product_name"]
            for i in DAO_RECIPE.query_data(queries.existed["product_name"])
        ]
        input_dialog.existed_products = existed_products
        update_dialog.refresh()
        # Reinitialize aggrid and cards
        new_product_overview, new_recipes_data = DAO_RECIPE.fetch_recipe_data()
        notify_null.notify_if_null_data(new_product_overview)
        overview_grid.refresh(new_product_overview)
        recipe_cards.recreate(new_recipes_data)

    def commit_input():
        product_basic, recipe_details = input_dialog.get_grid_values()
        input_uoms = [i["uom_name"] for i in product_basic]
        input_materials = [i["material_name"] for i in recipe_details]

        # Insert new uom and product basics
        DAO_RECIPE.insert_new_names("uom_name", input_uoms)
        DAO_RECIPE.insert_new_names("material_name", input_materials)
        # Insert product first so product_id can be reference by recipe

        DAO_RECIPE.insert_product_records(product_basic[0])
        # Insert recipe details
        DAO_RECIPE.insert_recipe_records(
            product_basic[0]["product_name"], recipe_details
        )
        update_costs(DAO_RECIPE)
        reinitialize()

    def commit_update(product_id: int):
        update_basic, update_detail = update_dialog.get_grid_values()
        update_uoms = [i["uom_name"] for i in update_basic]
        update_materials = [i["material_name"] for i in update_detail]

        # Insert new uom and product basics

        DAO_RECIPE.insert_new_names("uom_name", update_uoms)
        DAO_RECIPE.insert_new_names("material_name", update_materials)
        # Insert product first so product_id can be reference by recipe
        DAO_RECIPE.update_product_records(
            product_id, update_dialog.original_basic, update_basic[0]
        )
        # Insert recipe details
        DAO_RECIPE.update_recipe_records(
            product_id, update_dialog.original_detail, update_detail
        )
        update_costs(DAO_RECIPE)
        reinitialize()

    # Recipes are to be deleted first, because the foreign key product_id in
    # products table is referencing the recipes table
    ### Product_id is also refercne by order_details! Be careful of this delete
    def commit_delete(product_id: int):
        uom_id = DAO_RECIPE.query_data(
            "SELECT uom_id from orderapp.products where product_id = %s", (product_id,)
        )[0]["uom_id"]
        material_ids = DAO_RECIPE.query_data(
            "SELECT material_id from orderapp.recipes WHERE product_id = %s",
            (product_id,),
        )
        material_ids = [i["material_id"] for i in material_ids]

        DAO_RECIPE.commit_delete(product_id, "recipes")
        DAO_RECIPE.commit_delete(product_id, "product_prices")
        DAO_RECIPE.commit_delete(product_id, "product_costs")
        DAO_RECIPE.commit_delete(product_id, "products")
        # Will check for existence and clean up none-referecing uom_id AFTER product deletions
        DAO_RECIPE.clean_up_uom(uom_id)
        DAO_RECIPE.clean_up_materials(material_ids)
        update_costs(DAO_RECIPE)
        reinitialize()

    # Fetch SQL data and construct input/display schema
    product_overview, recipes_data = DAO_RECIPE.fetch_recipe_data()
    existed_products = DAO_RECIPE.query_data(queries.existed["product_name"])
    existed_products = (
        [i["product_name"] for i in existed_products] if existed_products else []
    )
    product_template = [
        s
        for s in DAO_RECIPE.get_value_options(constants.PRODUCTS_TEMPLATE, ["uom_name"])
    ]
    recipe_template = [
        s
        for s in DAO_RECIPE.get_value_options(
            constants.RECIPES_TEMPLATE, ["material_name"]
        )
        if s.field in ["material_name", "quantity"]
    ]
    # Notification for null data
    # Check for overview data intitally and on reinitialize
    notify_null = NotifyAwaitInput("請點擊「新增產品」輸入首筆資料")
    notify_null.notify_if_null_data(product_overview)

    # Dialog for inputting new recipe records to be inserted
    input_dialog = RecipeInputDialog(
        product_template, recipe_template, existed_products, commit_input
    )

    update_dialog = RecipeUpdateDialog(
        product_template, recipe_template, on_confirm=commit_update
    )

    # Dialog for deleting order records
    confirm_delete = ConfirmDeleteRecipe(
        "刪除資料（含此產品之成本紀錄）無法復原，請確認是否刪除", DAO_RECIPE
    )
    confirm_delete.on_confirm = commit_delete
    with ui.column().classes("w-full max-w-7xl h-full"):
        with ui.row().classes("w-full "):
            # Dropdown for page navigation
            DropdownNavigate(constants.PAGES["/recipes"], constants.PAGES)
            # Navigate to materials page
            to_materials = ui.button(text="材料成本")
            to_materials.classes("ml-auto text-base md:text-lg").props(
                "flat icon-right='last_page' padding='none'"
            )
            to_materials.on_click(lambda: ui.navigate.to("/materials"))

        # Buttons for open input dialogue, unselect, and show_delete
        with ui.row().classes("w-full gap-1 !divide-y-2"):
            ui.button("新增產品", on_click=input_dialog.open)
            with ui.button(icon="deselect") as unselect:
                ui.tooltip("取消所有選取")
            with ui.button(icon="edit_note").classes("ml-auto") as show_modify:
                ui.tooltip("顯示刪除/修改按鈕")

        # Display products overview
        overview_grid = SelectableAggrid(
            constants.PRODUCTS_OVERVIEW_TEMPLATE, product_overview
        )
        # Display selected (if not selected = all) recipes of products
        recipe_cards = RecipeCards(
            constants.RECIPES_TEMPLATE,
            recipes_data,
            "product",
            on_update=update_dialog.start_update,
            on_delete=confirm_delete.start,
        )
        recipe_cards.select(all=False)

        # Deferred binding
        unselect.on_click(overview_grid.uncheck_all)
        show_modify.on_click(recipe_cards.show_modify)
        overview_grid.select_cards = recipe_cards.select
