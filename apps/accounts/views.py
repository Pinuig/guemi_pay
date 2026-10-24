from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SavedRecipient
from .serializers import MeSerializer, RegisterSerializer, SavedRecipientSerializer


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class MeView(APIView):
    def get(self, request):
        return Response(MeSerializer(request.user).data)

    def patch(self, request):
        serializer = MeSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class SavedRecipientListCreateView(generics.ListCreateAPIView):
    serializer_class = SavedRecipientSerializer

    def get_queryset(self):
        qs = SavedRecipient.objects.filter(user=self.request.user)
        service_type = self.request.query_params.get("service_type")
        if service_type:
            qs = qs.filter(service_type=service_type)
        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
