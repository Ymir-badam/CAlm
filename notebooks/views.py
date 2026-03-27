from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Notebook
from chat.models import ChatSession


@login_required
def dashboard(request):
    profile = request.user.userprofile
    return render(request, "dashboard.html", {"profile": profile})


@login_required
def notebook_list(request):
    notebooks = Notebook.objects.filter(user=request.user)
    return render(request, "notebook_list.html", {"notebooks": notebooks})


@login_required
def create_notebook(request):
    if request.method == "POST":
        name = request.POST.get("name")
        Notebook.objects.create(user=request.user, name=name)
        return redirect("notebook_list")

    return render(request, "create_notebook.html")


@login_required
def notebook_detail(request, notebook_id):
    notebook = get_object_or_404(
        Notebook,
        id=notebook_id,
        user=request.user
    )
    documents = notebook.document_set.all()
    chat_sessions = ChatSession.objects.filter(notebook=notebook)

    return render(request, "notebook_detail.html", {
        "notebook": notebook,
        "documents": documents,
        "chat_sessions": chat_sessions,
    })