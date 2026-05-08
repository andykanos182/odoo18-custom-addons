# Product Checker (andykanoz_product_checker)

Odoo 18 custom module — dedicated scanner-oriented backend page to quickly check product availability, price, and stock.

## Features

- **Scanner-friendly search**: Auto-focus barcode input with debounced auto-search (500ms) + Enter key trigger
- **Large product image** (~400px) for visual verification
- **Price info**: Default pricelist + switchable dropdown to any pricelist
- **Stock on hand** from default variant
- **Cost**, category, barcode, internal reference display
- **Ecommerce info**: Is Published status + Ecommerce Category
- **Scan history sidebar** (last 20 scans, click to reload)
- **Quick-create form** when product not found (Name, Barcode, Cost, Sales Price, Pricelist + Price, Category, Is Published, Ecommerce Category)
- **Open Full Product Form** button to jump to standard Odoo product form

## Search Logic (in order)

1. Exact match on `barcode` (product.template)
2. Exact match on `default_code` (product.template)
3. Exact match on variant barcode (product.product) — returns its template
4. Fuzzy match on `name` (ilike)

## Installation

1. Copy this folder to your Odoo addons path:
   ```
   D:\MyServer\Odoo18\Addons\andykanoz_product_checker\
   ```

2. Restart Odoo service (or Docker container):
   ```
   docker restart <your-odoo-container>
   ```

3. In Odoo:
   - Activate Developer Mode
   - Go to **Apps** → **Update Apps List**
   - Search for "Product Checker"
   - Click **Install**

4. A new top-level menu **"Product Checker"** will appear in the main menu bar.

## Dependencies

- `base`
- `product`
- `stock`
- `website_sale` (required for `is_published` and `public_categ_ids` fields)

## Usage

1. Click the **Product Checker** menu
2. The barcode input is auto-focused — just scan with your barcode scanner
3. Product info displays instantly with large image
4. Change pricelist from the dropdown to see different prices
5. If product not found → click **Create New Product** to fill quick form
6. Click any item in the right sidebar to re-view a previously scanned product

## Technical Notes

- Uses OWL framework (Odoo 18 native)
- All backend communication via ORM RPC (no custom HTTP routes needed)
- Scan history stored in frontend state only (not persisted to DB)
- Uses `product.template` as primary search model, with fallback to `product.product` variants

## Customization Tips

- To change history limit: edit `product_checker.js` → `if (this.state.history.length > 20)`
- To change debounce delay: edit `product_checker.js` → `setTimeout(..., 500)`
- To change image size: edit `product_checker.scss` → `.o_pc_product_image { flex: 0 0 400px; }`
