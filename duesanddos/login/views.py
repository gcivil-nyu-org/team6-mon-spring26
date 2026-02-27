from django.http import HttpResponse


def index(request):
    return HttpResponse("Hello, world. This is going to be the login and registration app.")