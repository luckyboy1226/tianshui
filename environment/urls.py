from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RemoteSensingImageViewSet,
    EcologicalIndexViewSet,
    RSEIResultViewSet,
    ProcessingTaskViewSet
)

router = DefaultRouter()
router.register(r'remote-sensing-images', RemoteSensingImageViewSet)
router.register(r'ecological-indices', EcologicalIndexViewSet)
router.register(r'rsei-results', RSEIResultViewSet)
router.register(r'processing-tasks', ProcessingTaskViewSet)

app_name = 'environment'

urlpatterns = [
    path('api/', include(router.urls)),
] 