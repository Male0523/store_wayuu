from django.contrib.admin.apps import AdminConfig


class WayuuAdminConfig(AdminConfig):
    default_site = 'config.admin_site.WayuuAdminSite'