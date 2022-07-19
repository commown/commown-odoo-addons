def migrate(cr, version):
    cr.execute("UPDATE coupon_campaign " "SET can_auto_cumulate=FALSE")
    cr.execute("UPDATE coupon_campaign " "SET can_cumulate=NOT coupons_are_exclusive")
    cr.execute("ALTER TABLE coupon_campaign " "DROP COLUMN coupons_are_exclusive")
