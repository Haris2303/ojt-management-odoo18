# from odoo import api, SUPERUSER_ID

# def create_portal_user_rule(cr, registry):
#     env = api.Environment(cr, SUPERUSER_ID, {})

#     try:
#         model_participant_id = env.ref('solvera_ojt_core.model_ojt_participant').id
#         group_portal_id = env.ref('base.group_portal').id
#         rule_xml_id = 'solvera_ojt_core.ojt_participant_portal_user_rule'

#         rule_vals = {
#             'name': 'OJT Participant: Portal User Rule',
#             'model_id': model_participant_id,
#             'groups': [(6, 0, [group_portal_id])],
#             'perm_read': True,
#             'perm_write': False,
#             'perm_create': False,
#             'perm_delete': False,
#             'domain_force': "[('partner_id', '=', user.partner_id.id)]"
#         }

#         rule = env.ref(rule_xml_id, raise_if_not_found=False)
#         if rule:
#             rule.write(rule_vals)
#         else:
#             # Odoo 16+ requires the module name in the id when creating through code
#             env['ir.rule'].create({
#                 'id': rule_xml_id,
#                 **rule_vals
#             })
#     except Exception:
#         # Fails silently if refs don't exist yet, will be re-attempted on next update.
#         pass