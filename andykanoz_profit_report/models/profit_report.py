from odoo import fields, models, tools


class AndykanozProfitReport(models.Model):
    """SQL-based profit report per POS order line.

    One row per (pos_order_line). Group/pivot by category to get the numbers
    Andyka needs for monthly profit analysis without Accounting Enterprise.
    """
    _name = 'andykanoz.profit.report'
    _description = 'POS Profit Report by Category'
    _auto = False
    _rec_name = 'product_id'
    _order = 'date desc'

    # ------------------------------------------------------------------
    # Dimensions
    # ------------------------------------------------------------------
    date = fields.Datetime(string='Order Date', readonly=True)
    order_id = fields.Many2one('pos.order', string='POS Order', readonly=True)
    config_id = fields.Many2one('pos.config', string='POS Config', readonly=True)
    session_id = fields.Many2one('pos.session', string='POS Session', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist', readonly=True)

    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    product_tmpl_id = fields.Many2one('product.template', string='Product Template', readonly=True)
    categ_id = fields.Many2one('product.category', string='Product Category', readonly=True)

    # ------------------------------------------------------------------
    # Measures
    # ------------------------------------------------------------------
    qty = fields.Float(string='Quantity', readonly=True)
    revenue = fields.Float(
        string='Revenue',
        readonly=True,
        help='Line subtotal net of discount and pricelist, before tax',
    )
    cost = fields.Float(
        string='Cost (COGS)',
        readonly=True,
        help='qty * current standard_price of the product (per company)',
    )
    profit = fields.Float(
        string='Profit',
        readonly=True,
        help='Revenue - Cost',
    )
    margin = fields.Float(
        string='Margin %',
        readonly=True,
        group_operator='avg',
        help='Profit / Revenue * 100',
    )

    # ------------------------------------------------------------------
    # SQL view
    # ------------------------------------------------------------------
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        # NOTE on standard_price:
        # In Odoo 18, product.product.standard_price is a company-dependent
        # field stored as JSONB: {"<company_id>": <cost>, ...}.
        # We extract the value for the order's company using ->> and cast to
        # numeric. If the key is missing we fall back to 0.
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    l.id                                    AS id,
                    o.date_order                            AS date,
                    o.id                                    AS order_id,
                    o.config_id                             AS config_id,
                    o.session_id                            AS session_id,
                    o.company_id                            AS company_id,
                    o.pricelist_id                          AS pricelist_id,
                    l.product_id                            AS product_id,
                    pp.product_tmpl_id                      AS product_tmpl_id,
                    pt.categ_id                             AS categ_id,
                    l.qty                                   AS qty,
                    l.price_subtotal                        AS revenue,
                    (l.qty * COALESCE(
                        (pp.standard_price ->> o.company_id::text)::numeric,
                        0.0
                    ))                                      AS cost,
                    (l.price_subtotal - l.qty * COALESCE(
                        (pp.standard_price ->> o.company_id::text)::numeric,
                        0.0
                    ))                                      AS profit,
                    CASE
                        WHEN l.price_subtotal = 0 THEN 0.0
                        ELSE (
                            (l.price_subtotal - l.qty * COALESCE(
                                (pp.standard_price ->> o.company_id::text)::numeric,
                                0.0
                            )) / l.price_subtotal
                        ) * 100.0
                    END                                     AS margin
                FROM pos_order_line l
                JOIN pos_order        o  ON o.id = l.order_id
                JOIN product_product  pp ON pp.id = l.product_id
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                WHERE o.state IN ('paid', 'invoiced', 'done')
            )
        """)
