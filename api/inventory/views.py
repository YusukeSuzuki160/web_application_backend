from api.inventory.exceptions import BusinessException
from django.db.models import F, Value, Sum
from django.db.models.functions import Coalesce
from rest_framework.exceptions import NotFound
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Product, Purchase, Sales
from .serializers import (
    ProductSerializer,
    PurchaseSerializer,
    SalesSerializer,
    InventorySerializer,
)
from rest_framework import status
from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
)


class ProductView(APIView):
    """
    商品操作に関する関数
    """

    def get_object(self, pk):
        try:
            return Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            raise NotFound

    def get(self, request, id=None, format=None):
        """
        商品一覧もしくは一意の商品を取得する
        """
        if id is None:
            queryset = Product.objects.all()
            serializer = ProductSerializer(queryset, many=True)
        else:
            product = self.get_object(id)
            serializer = ProductSerializer(product)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, format=None):
        """
        商品を新規作成する
        """
        serializer = ProductSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def put(self, request, id, format=None):
        """
        商品を更新する
        """
        product = self.get_object(id)
        serializer = ProductSerializer(instance=product, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, id, format=None):
        """
        商品を削除する
        """
        product = self.get_object(id)
        product.delete()
        return Response(status=status.HTTP_200_OK)


class PurchaseView(APIView):
    """
    仕入れ操作に関する関数
    """

    def post(self, request, format=None):
        """
        仕入れを新規作成する
        """
        serializer = PurchaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class SalesView(APIView):
    """
    販売操作に関する関数
    """

    def post(self, request, format=None):
        """
        販売を新規作成する
        """
        serializer = SalesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        purchase = Purchase.objects.filter(product=request.data["product"]).aggregate(
            quantity_sum=Coalesce(Sum("quantity"), 0)
        )
        sales = Sales.objects.filter(product=request.data["product"]).aggregate(
            quantity_sum=Coalesce(Sum("quantity"), 0)
        )
        if purchase["quantity_sum"] < sales["quantity_sum"] + int(
            request.data["quantity"]
        ):
            raise BusinessException("在庫数量を超過することはできません。")
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class InventoryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, id=None, format=None):
        if id is None:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        else:
            purchase = (
                Purchase.objects.filter(product=id)
                .prefetch_related("product")
                .values(
                    "id",
                    "quantity",
                    type=Value("1"),
                    date=F("purchase_date"),
                    unit=F("product__price"),
                )
            )
            sales = (
                Sales.objects.filter(product=id)
                .prefetch_related("product")
                .values(
                    "id",
                    "quantity",
                    type=Value("2"),
                    date=F("sales_date"),
                    unit=F("product__price"),
                )
            )
            queryset = purchase.union(sales).order_by(F("date"))
            serializer = InventorySerializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)


class LoginView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = []

    def post(self, request):
        serializer = TokenObtainPairSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        access = serializer.validated_data.get("access", None)
        refresh = serializer.validated_data.get("refresh", None)
        if access:
            response = Response(status=status.HTTP_200_OK)
            max_age = settings.COOKIE_TIME
            response.set_cookie("access", access, httponly=True, max_age=max_age)
            response.set_cookie("refresh", refresh, httponly=True)
            return response
        return Response(
            {"errMsg": "ユーザー認証に失敗しました。"},
            status=status.HTTP_401_UNAUTHORIZED,
        )


class RetryView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = []

    def post(self, request):
        request.data["refresh"] = request.META.get("HTTP_REFRESH_TOKEN")
        serializer = TokenRefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        access = serializer.validated_data.get("access", None)
        refresh = serializer.validated_data.get("refresh", None)
        if access:
            response = Response(status=status.HTTP_200_OK)
            max_age = settings.COOKIE_TIME
            response.set_cookie("access", access, httponly=True, max_age=max_age)
            response.set_cookie("refresh", refresh, httponly=True)
            return response
        return Response(
            {"errMsg": "ユーザー認証に失敗しました。"},
            status=status.HTTP_401_UNAUTHORIZED,
        )


class LogoutView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        response = Response(status=status.HTTP_200_OK)
        response.delete_cookie("access")
        response.delete_cookie("refresh")
        return response


class SyncView(APIView):
    """
    同期処理に関する関数
    """

    pass


class AsyncView(APIView):
    """
    非同期処理に関する関数
    """

    pass


class SummaryView(APIView):
    """
    集計処理に関する関数
    """

    pass
