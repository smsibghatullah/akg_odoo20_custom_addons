def migrate(cr, version):
    """Rebuild res_partner.commercial_partner_id where it is NULL (left empty by the migration)."""
    cr.execute("""
        UPDATE res_partner
           SET commercial_partner_id = id
         WHERE commercial_partner_id IS NULL AND (is_company OR parent_id IS NULL)
    """)
    for _i in range(10):  # contacts under a company/parent: take the parent's commercial partner
        cr.execute("""
            UPDATE res_partner c
               SET commercial_partner_id = p.commercial_partner_id
              FROM res_partner p
             WHERE c.parent_id = p.id
               AND c.commercial_partner_id IS NULL
               AND p.commercial_partner_id IS NOT NULL
        """)
        if not cr.rowcount:
            break
    cr.execute("UPDATE res_partner SET commercial_partner_id = id WHERE commercial_partner_id IS NULL")
