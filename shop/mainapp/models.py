import sys
from PIL import Image
from io import BytesIO

from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.urls import reverse

# Create your models here.


User = get_user_model()


def get_product_url(obj, viewname):
    ct_model = obj.__class__.meta.model_name
    return reverse(viewname, kwargs={'ct_model': ct_model, 'slug': obj.slug})


class MinResolutionException(Exception):
    pass


class MaxResolutionException(Exception):
    pass


class MaxImgSizeException(Exception):
    pass


class LatestProductManager:

    @staticmethod
    def get_products_for_main(*args, **kwargs):
        with_respect_to = kwargs.get('with_respect_to')
        products = []
        ct_models = ContentType.objects.filter(model__in=args)
        for ct_model in ct_models:
            model_products = ct_model.model_class()._base_manager.all().order_by('-id')[:5]
            products.extend(model_products)
        if with_respect_to:
            ct_model = ContentType.objects.filter(model=with_respect_to)
            if ct_model.exists() and with_respect_to in args:
                return sorted(
                    products, key=lambda x: x.__class__._meta_.model_name.startswith(with_respect_to), reverse=True
                )

        return products


class LatestProducts:

    objects = LatestProductManager()


# Customer
class Customer(models.Model):

    user = models.ForeignKey(User, verbose_name='Пользователь', on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, verbose_name='Номер телефона')
    address = models.CharField(max_length=255, verbose_name='Адрес')

    def __str__(self):
        return f'Покупатель: {self.user.first_name, self.user.last_name}'


# Category
class Category(models.Model):

    name = models.CharField(max_length=255, verbose_name='Имя категории')
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name


# Product
class Product(models.Model):

    MIN_RESOLUTION = (400, 400)
    MAX_RESOLUTION = (2000, 2000)
    MAX_IMAGE_SIZE = 3145728

    class Meta:
        abstract = True

    category = models.ForeignKey(Category, verbose_name='Категория', on_delete=models.CASCADE)
    title = models.CharField(max_length=255, verbose_name='Наименование')
    slug = models.SlugField(unique=True)
    image = models.ImageField(verbose_name='Изображение')
    description = models.TextField(verbose_name='Описание', null=True)
    price = models.DecimalField(max_digits=9, decimal_places=2)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        image = self.image
        img = Image.open(image)
        min_height, min_width = self.MIN_RESOLUTION
        max_height, max_width = self.MAX_RESOLUTION
        if img.size > self.MAX_IMAGE_SIZE:
            raise MaxImgSizeException('Вес изображения не должен превышать 3MB')
        if img.height < min_height or img.width < min_width:
            raise MinResolutionException('Разрешение изображения меньше минимального')
        if img.height > max_width or img.width > max_width:
            raise MaxResolutionException('Разрешение изображения больше максимального')

        image = self.image
        img = Image.open(image)
        new_img = img.convert('RGB')
        new_img = new_img.resize((200, 200), Image.ANTIALIAS)
        filestream = BytesIO()
        file_ = new_img.save(filestream, 'JPEG', quality=90)
        file_.seek(0)
        name = '{}.{}'.format(*self.image.name.split('.'))
        self.image = InMemoryUploadedFile(
            filestream, 'ImageField', name, 'jpeg/image', sys.getsizeof(file_), None
        )
        super().save(*args, **kwargs)


# Cart product
class CartProduct(models.Model):

    user = models.ForeignKey('Customer', verbose_name='Покупатель', on_delete=models.CASCADE)
    cart = models.ForeignKey('Cart', verbose_name='Корзина', on_delete=models.CASCADE, related_name='related_products')
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    quantity = models.PositiveIntegerField(default=1)
    final_price = models.DecimalField(max_digits=9, decimal_places=2, verbose_name='Общая цена')

    def __str__(self):
        return f'Продукт: {self.product.title} (для корзины)'

# Order
# class Order(models.Model):


# Cart
class Cart(models.Model):

    owner = models.ForeignKey('Customer', verbose_name='Владелец', on_delete=models.CASCADE)
    products = models.ManyToManyField(CartProduct, blank=True, related_name='related_cart')
    total_products = models.PositiveIntegerField(default=0)
    final_price = models.DecimalField(max_digits=9, decimal_places=2, verbose_name='Общая цена')

    def __str__(self):
        return str(self.id)


# Specs
class Specs(models.Model):

    content = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    name = models.CharField(max_length=255, verbose_name='Имя товара для характеристик')

    def __str__(self):
        return f'Характеристики для товара: {self.name}'


class Notebook(Product):

    diagonal = models.CharField(max_length=255, verbose_name='Диагональ')
    display = models.CharField(max_length=255, verbose_name='Тип дисплея')
    processorFQ = models.CharField(max_length=255, verbose_name='Частота процессора')
    ram = models.CharField(max_length=255, verbose_name='Оперативная память')
    video = models.CharField(max_length=255, verbose_name='Видеокарта')
    time_wout_charge = models.CharField(max_length=255, verbose_name='Время автономной работы')

    def __str__(self):
        return f'{self.category.name} : {self.title}'

    def get_absolute_url(self):
        return get_product_url(self, 'product_detail')


class Smartphone(Product):

    diagonal = models.CharField(max_length=255, verbose_name='Диагональ')
    display = models.CharField(max_length=255, verbose_name='Тип дисплея')
    resolution = models.CharField(max_length=255, verbose_name='Разрешение экрана')
    processorFQ = models.CharField(max_length=255, verbose_name='Частота процессора')
    ram = models.CharField(max_length=255, verbose_name='Оперативная память')
    accum_cap = models.CharField(max_length=255, verbose_name='Емкость аккумулятора')
    time_wout_charge = models.CharField(max_length=255, verbose_name='Время работы аккумулятора')
    sd = models.BooleanField(default=True)
    sd_cap = models.CharField(max_length=255, verbose_name='Максимальный объем SD карты')
    main_cam = models.CharField(max_length=255, verbose_name='Главная камера')
    frontal_cam = models.CharField(max_length=255, verbose_name='Фронтальная камера')

    def __str__(self):
        return f'{self.category.name} : {self.title}'

    def get_absolute_url(self):
        return get_product_url(self, 'product_detail')
