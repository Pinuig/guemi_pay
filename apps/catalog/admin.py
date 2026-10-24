from django.contrib import admin

from .models import AirtimeRule, CanalPlan, DataBundle, UtilityServiceConfig


@admin.register(DataBundle)
class DataBundleAdmin(admin.ModelAdmin):
    list_display = ("operator", "period", "data_label", "validity_label", "price", "is_active")
    list_filter = ("operator", "period", "is_active")
    list_editable = ("price", "is_active")
    ordering = ("operator", "period", "price")


@admin.register(AirtimeRule)
class AirtimeRuleAdmin(admin.ModelAdmin):
    list_display = ("operator", "min_amount", "max_amount", "is_active")
    list_editable = ("min_amount", "max_amount", "is_active")


@admin.register(CanalPlan)
class CanalPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "monthly_price", "sort_order", "is_active")
    list_editable = ("monthly_price", "sort_order", "is_active")


@admin.register(UtilityServiceConfig)
class UtilityServiceConfigAdmin(admin.ModelAdmin):
    list_display = ("service_type", "account_type", "reference_label", "min_amount", "is_active")
    list_editable = ("min_amount", "is_active")
