import logging
from odoo import http
from odoo.http import request
from odoo.addons.website.tools import get_base_domain
import werkzeug.urls

_logger = logging.getLogger(__name__)

class Website(http.Controller):
    @http.route('/akghardware/<int:website_id>', type='http', auth="none", sitemap=False , website=True)
    def website_force_akghardware(self, website_id, path='/', isredir=False, **kw):
        website = request.env['website'].sudo().browse(website_id)
        website.sudo()._force()
        return request.redirect(path)





