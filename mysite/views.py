from django.shortcuts import render, redirect
from rest_framework import generics
from .models import Book, Rating
from .serializers import BookSerializers
from rest_framework.views import APIView
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm
from django.http import JsonResponse
from collections import defaultdict
from django.db import connection

# Execute SQL Queries
def execute_sql(query, params=None):
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        if query.strip().lower().startswith("select"):
            return cursor.fetchall()
        else:
            connection.commit()
            return cursor.rowcount


# Login
def loginPage(request):

    page = 'login'

    if request.user.is_authenticated:
        return redirect('show')

    if request.method == 'POST':
        username = request.POST.get('username').lower()
        password = request.POST.get('password')

        # ORM
        # try:
        #     user = User.objects.get(username=username)
        #
        #     user = authenticate(request, username=username, password=password)
        #
        #     if user is not None:
        #         login(request, user)
        #         return redirect('show')
        #     else:
        #         return JsonResponse({'error': 'Username or Password is wrong!'})
        #
        # except:
        #     return JsonResponse({'error': 'User does not exist :('})

        # SQL
        query = "SELECT * FROM auth_user WHERE username = %s"
        user = execute_sql(query, [username])

        if user:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('show')
            else:
                return JsonResponse({'error': 'Username or Password is wrong!'})
        else:
            return JsonResponse({'error': 'User does not exist :('})

    context = {'page': page}
    return render(request, "view/login_register.html", context)


def logoutUser(request):
    logout(request)
    return redirect('login')


# Register
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

        # ORM
        # if title:
        #     books = Book.objects.filter(title__icontains=title)
        # else:
        #     books = Book.objects.all()

        # SQL
        if title:
            query = "SELECT * FROM mysite_book WHERE title ILIKE %s"
            params = [f"%{title}%"]
        else:
            query = "SELECT * FROM mysite_book"
            params = []

        books = execute_sql(query, params)

        user_ratings = {}
        if request.user.is_authenticated:
            # ORM
            # ratings = Rating.objects.filter(user=request.user)
            # user_ratings = {rating.book.id: rating.rating for rating in ratings}

            # SQL
            query = "SELECT book_id, rating FROM mysite_rating WHERE user_id = %s"
            user_ratings_list = execute_sql(query, [request.user.id])
            user_ratings = {rating[0]: rating[1] for rating in user_ratings_list}

        data = []
        # SQL
        for book in books:
            data.append({
                'id': book[0],
                'title': book[1],
                'genre': book[3],
                'author': book[2],
                'user_rating': int(user_ratings.get(book[0], -1))
            })

        # ORM
        # for book in books:
        #     numRate = book.getNumRate()
        #     data.append({
        #         'id': book.id,
        #         'title': book.title,
        #         'genre': book.genre,
        #         'author': book.author,
        #         'rate': book.getAverageRate(),
        #         'numRate': numRate if numRate < 1000 else "1k+",
        #         'user_rating': int(user_ratings.get(book.id, -1))
        #     })
        context = {"data": data, 'page': page}

        return render(request, "view/bookList.html", context=context)

    @csrf_exempt
    def post(self, request):

        title_id = request.POST.get('title_id')
        rating = request.POST.get('rating')

        # ORM
        # if title_id and rating:
        #     book = Book.objects.get(id=title_id)
        #     rating = int(rating)
        # 
        #     user_rating, created = Rating.objects.get_or_create(user=request.user, book=book,
        #                                                         defaults={'rating': rating})
        # 
        #     if created or user_rating.rating != rating:
        #         user_rating.rating = rating
        #         user_rating.save()
        #     else:
        #         user_rating.delete()

        # SQL
        if title_id and rating:
            rating = int(rating)
            query = "SELECT * FROM mysite_rating WHERE user_id = %s AND book_id = %s"
            user_rating = execute_sql(query, [request.user.id, title_id])
            print(user_rating)
            if user_rating:
                if user_rating[0][1] == rating:
                    query = "DELETE FROM mysite_rating WHERE user_id = %s AND book_id = %s"
                    execute_sql(query, [request.user.id, title_id])
                else:
                    query = "UPDATE mysite_rating SET rating = %s WHERE user_id = %s AND book_id = %s"
                    execute_sql(query, [rating, request.user.id, title_id])
            else:
                query = "INSERT INTO mysite_rating (user_id, book_id, rating) VALUES (%s, %s, %s)"
                execute_sql(query, [request.user.id, title_id, rating])

        return redirect('show')


# Suggest Books
@login_required
def suggest(request):

    page = 'suggest'

    # If Post Method (Update, Delete or Add a new Rating) Happens in Suggest Page
    if request.method == "POST":
        # Create an instance of BookList
        book_list_view = BookList()
        # Call the post method with the request
        return book_list_view.post(request)

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
            # SQL
            query = "SELECT * FROM mysite_book"
            fav_books = [execute_sql(query)]

    if fav_books:
        data = []
        
        # SQL
        for books in fav_books:
            for book in books:
                data.append({
                    'id': book[0],
                    'title': book[1],
                    'genre': book[3],
                    'author': book[2],
                    'user_rating': int(user_ratings.get(book[0], -1))
                })

        # ORM
        # for books in fav_books:
        #     for book in books:
        #         numRate = book.getNumRate()
        #         data.append({
        #             'id': book.id,
        #             'title': book.title,
        #             'genre': book.genre,
        #             'author': book.author,
        #             'rate': book.getAverageRate(),
        #             'numRate': numRate if numRate < 1000 else "1k+",
        #             'user_rating': int(user_ratings.get(book.id, -1))
        #         })
        context = {"data": data, 'page': page}

        return render(request, "view/bookList.html", context=context)

    else:
        return JsonResponse({'error': 'there is not enough data about you'})


def suggestWithAuthor(ratings):

    books = []
    fav_authors = {rating.book.author for rating in ratings if rating.rating > 3}

    # ORM
    # for author in fav_authors:
    #     books.append(Book.objects.filter(author=author))

    # SQL
    for author in fav_authors:
        query = "SELECT * FROM mysite_book WHERE author = %s"
        books.append(execute_sql(query, [author]))

    return books


def suggestWithGenre(ratings):

    books = []

    genre_counts = defaultdict(int)
    for rating in ratings:
        if rating.rating > 3:
            genre_counts[rating.book.genre] += 1

    # ORM
    # Find the genre with the maximum count of high score
    # if genre_counts:
    #     fav_genre = max(genre_counts, key=genre_counts.get)
    #
    #     books.append(Book.objects.filter(genre=fav_genre))

    # SQL
    if genre_counts:
        fav_genre = max(genre_counts, key=genre_counts.get)
        query = "SELECT * FROM mysite_book WHERE genre = %s"
        return [execute_sql(query, [fav_genre])]

    return books

