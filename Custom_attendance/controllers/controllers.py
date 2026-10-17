# -*- coding: utf-8 -*-
# from odoo import http


# class CustomAttendance(http.Controller):
#     @http.route('/custom_attendance/custom_attendance', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_attendance/custom_attendance/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_attendance.listing', {
#             'root': '/custom_attendance/custom_attendance',
#             'objects': http.request.env['custom_attendance.custom_attendance'].search([]),
#         })

#     @http.route('/custom_attendance/custom_attendance/objects/<model("custom_attendance.custom_attendance"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_attendance.object', {
#             'object': obj
#         })
