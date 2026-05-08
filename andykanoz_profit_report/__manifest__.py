{
    'name': 'Andykanoz Profit Report',
    'version': '18.0.1.0.0',
    'category': 'MyCustom/Modules',
    'summary': 'Profit report per product category from POS orders (Community-compatible)',
    'description': """
Andykanoz Profit Report
=======================
Revenue vs COGS report per product category, computed directly from POS order
lines without requiring Accounting Enterprise.

FEATURES
--------
* SQL-based report view (fast, no cron / no stored table to maintain)
* Revenue = pos.order.line.price_subtotal (net of discount & pricelist, before tax)
* Cost = qty * product.standard_price (current cost, per company)
* Profit = Revenue - Cost
* Margin % = Profit / Revenue
* Filters: This Month, Last Month, This Year, custom date range
* Group By: Product Category, Product, Pricelist, POS Config, Order, Day/Week/Month
* Views: Pivot (default), Graph, List
* Only counts orders with state paid / invoiced / done (excludes draft & cancelled)
* Supports Odoo 18 JSONB company-dependent standard_price
* Supports pricelists — revenue already reflects the price after pricelist rules

HOW TO USE
----------
1. After installing, open: Point of Sale > Reporting > Profit by Category
2. The default view is Pivot, filtered to "This Month" and grouped by Category.
3. To see a specific month: click the "Order Date" filter > choose month/year.
4. To break down per product: click "+" on a category row, then group by Product.
5. To compare pricelists: remove the Category group, add the Pricelist group.
6. To export: click the cloud-download icon in the top-right of the pivot view.
7. Switch to Graph view for a bar chart of profit per category.
8. Switch to List view for line-by-line detail (each POS order line = 1 row).

IMPORTANT NOTES ON COST ACCURACY
--------------------------------
* Cost is read from the CURRENT value of product.standard_price.
  If you change a product's cost later, historical months will recompute.
  This is a limitation of Odoo Community (no historical cost layers).
* For products with BoM (e.g. Rice Bowl), make sure standard_price reflects
  the real ingredient cost. You can auto-compute it from the BoM:
  Inventory > Products > [pick product] > Action > Compute Price from BoM.
  Recommended: run this monthly after updating raw material prices.
* Products without a set standard_price will show cost = 0 and profit = revenue.
  Double-check by opening the product and looking at the "Cost" field on the
  Purchase tab.
* Revenue uses price_subtotal (BEFORE tax). If you want revenue including tax,
  this would need a code change — ask if you need it.

TROUBLESHOOTING
---------------
* Report is empty?
  - Make sure at least one POS session has been closed with paid orders.
  - Check the date filter — by default it shows only the current month.
* Profit looks too high?
  - Your products probably have standard_price = 0. Set it correctly.
* Profit looks negative?
  - Either the product is genuinely sold below cost (check pricelist / discount),
    or standard_price is set too high.

DEPENDENCIES
------------
* point_of_sale
* product

NO dependency on Accounting Enterprise, Inventory valuation, or stock landed costs.
    """,
    'author': 'Andyka',
    'depends': ['point_of_sale', 'product'],
    'data': [
        'security/ir.model.access.csv',
        'views/profit_report_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
