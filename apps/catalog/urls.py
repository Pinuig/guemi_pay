from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("data-bundles", views.DataBundleViewSet, basename="data-bundle")
router.register("airtime-rules", views.AirtimeRuleViewSet, basename="airtime-rule")
router.register("canal-plans", views.CanalPlanViewSet, basename="canal-plan")
router.register("utility-services", views.UtilityServiceConfigViewSet, basename="utility-service")

urlpatterns = router.urls
