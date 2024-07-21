from django.urls import path
from . import views


urlpatterns = [
    path("login", views.loginPage, name='login'),
    path("logout", views.logoutUser, name='logout'),
    path("register", views.registerPage, name='register'),
    path("books_create/", views.BookListCreate.as_view(), name="books-view-create"),
    path("books_create/<int:pk>", views.BookRetrieveUpdateDestroy.as_view(), name="update"),
    path("books/", views.BookList.as_view(), name="show"),
    path("books/suggest/", views.suggest, name="suggest"),
]