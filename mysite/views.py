from django.shortcuts import render, redirect, get_object_or_404
from rest_framework import generics
from .models import Book, Rating, User
from .serializers import BookSerializers
from rest_framework.views import APIView
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm
from django.http import JsonResponse
from collections import defaultdict


def loginPage(request):

    page = 'login'

    if request.user.is_authenticated:
        return redirect('show')

    if request.method == 'POST':
        username = request.POST.get('username').lower()
        password = request.POST.get('password')

        try:
            user = User.objects.get(username=username)

            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                return redirect('show')
            else:
                return JsonResponse({'error': 'Username or Password is wrong!'})

        except:
            return JsonResponse({'error': 'User does not exist :('})

    context = {'page': page}
    return render(request, "view/login_register.html", context)


def logoutUser(request):
    logout(request)
    return redirect('login')


def registerPage(request):

    page = 'register'
    form = UserCreationForm()

    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.username = user.username.lower()
            user.save()
            login(request, user)
            return redirect('show')
        else:
            return JsonResponse({'error': 'Some problem with form.'})

    context = {'page': page, 'form': form}
    return render(request, "view/login_register.html", context)


class BookListCreate(generics.ListCreateAPIView):
    queryset = Book.objects.all()
    serializer_class = BookSerializers


class BookRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    queryset = Book.objects.all()
    serializer_class = BookSerializers
    lookup_field = "pk"


class BookList(APIView):
    def get(self, request, format=None):

        page = 'show'

        title = request.GET.get('q') if request.GET.get('q') != None else ''

        if title:
            books = Book.objects.filter(title__icontains=title)
        else:
            books = Book.objects.all()

        user_ratings = {}
        if request.user.is_authenticated:
            ratings = Rating.objects.filter(user=request.user)
            user_ratings = {rating.book.id: rating.rating for rating in ratings}

        data = []
        for book in books:
            numRate = book.getNumRate()
            data.append({
                'id': book.id,
                'title': book.title,
                'genre': book.genre,
                'author': book.author,
                'rate': book.getAverageRate(),
                'numRate': numRate if numRate < 1000 else "1k+",
                'user_rating': int(user_ratings.get(book.id, -1))
            })
        context = {"data": data, 'page': page}

        return render(request, "view/bookList.html", context=context)

    @csrf_exempt
    def post(self, request):

        title_id = request.POST.get('title_id')
        rating = request.POST.get('rating')

        if title_id and rating:
            book = Book.objects.get(id=title_id)
            rating = int(rating)

            user_rating, created = Rating.objects.get_or_create(user=request.user, book=book,
                                                                defaults={'rating': rating})

            if created or user_rating.rating != rating:
                user_rating.rating = rating
                user_rating.save()
            else:
                user_rating.delete()

        return redirect('show')


@login_required
def suggest(request):

    page = 'suggest'

    if request.user.is_authenticated:
        ratings = Rating.objects.filter(user=request.user)
        user_ratings = {rating.book.id: rating.rating for rating in ratings}

        suggestion_type = request.GET.get('type')
        if suggestion_type == 'author':
            # Suggest books based on favorite authors
            fav_books = suggestWithAuthor(ratings)
        elif suggestion_type == 'genre':
            fav_books = suggestWithGenre(ratings)
        else:
            # Handle the default case or error
            fav_books = [Book.objects.all()]

    if fav_books:

        data = []
        for books in fav_books:
            for book in books:
                numRate = book.getNumRate()
                data.append({
                    'id': book.id,
                    'title': book.title,
                    'genre': book.genre,
                    'author': book.author,
                    'rate': book.getAverageRate(),
                    'numRate': numRate if numRate < 1000 else "1k+",
                    'user_rating': int(user_ratings.get(book.id, -1))
                })
        context = {"data": data, 'page': page}

        return render(request, "view/bookList.html", context=context)

    else:
        return JsonResponse({'error': 'there is not enough data about you'})


def suggestWithAuthor(ratings):

    books = []
    fav_authors = {rating.book.author for rating in ratings if rating.rating > 3}

    print(fav_authors)

    for author in fav_authors:
        books.append(Book.objects.filter(author=author))

    return books


def suggestWithGenre(ratings):

    books = []

    genre_counts = defaultdict(int)
    for rating in ratings:
        if rating.rating > 3:
            genre_counts[rating.book.genre] += 1

    # Find the genre with the maximum count of high score
    if genre_counts:
        fav_genre = max(genre_counts, key=genre_counts.get)

        books.append(Book.objects.filter(genre=fav_genre))

    return books


