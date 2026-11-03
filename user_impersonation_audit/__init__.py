from . import controllers
from . import models
from . import wizard


def uninstall_hook(env):
    env['user.impersonation.session']._uia_end_all_on_uninstall()
