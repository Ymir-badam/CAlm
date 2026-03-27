from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Document
from notebooks.models import Notebook
from .services import process_document

@login_required
def upload_document(request, notebook_id):
    notebook = Notebook.objects.get(id=notebook_id, user=request.user)

    if request.method == "POST":
        file = request.FILES["file"]

        document = Document.objects.create(
            notebook=notebook,
            title=file.name,
            file=file,
            qdrant_collection=""
        )

        process_document(document)

        return redirect("notebook_detail", notebook_id=notebook.id)

    return render(request, "upload.html", {"notebook": notebook})
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
from documents.models import Document
from documents.charts import generate_chart_config, generate_waterfall_config, generate_variance_config


@login_required
@require_GET
def document_chart(request, doc_id):
    """
    GET /documents/<doc_id>/chart/
    Returns Chart.js config + summary KPIs for a CSV document.
    """
    try:
        doc = Document.objects.get(id=doc_id, notebook__user=request.user)
    except Document.DoesNotExist:
        return JsonResponse({"error": "Document not found."}, status=404)

    if not doc.title.lower().endswith(".csv"):
        return JsonResponse({"error": "Only CSV documents support chart generation."}, status=400)

    try:
        data = generate_chart_config(doc.file.path)
        return JsonResponse(data)
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        return JsonResponse({"error": "Failed to generate chart."}, status=500)


@login_required
@require_GET
def document_waterfall(request, doc_id):
    """
    GET /documents/<doc_id>/waterfall/
    Expects CSV with columns: Label, Value  (or Label, Actual, Budget).
    Returns a waterfall/bridge Chart.js config.
    """
    try:
        doc = Document.objects.get(id=doc_id, notebook__user=request.user)
    except Document.DoesNotExist:
        return JsonResponse({"error": "Document not found."}, status=404)

    try:
        import csv
        items = []
        with open(doc.file.path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cols = list(row.keys())
                label = row[cols[0]]
                val   = float(str(row[cols[1]]).replace(",", "").replace("£", "").replace("$", "").strip() or 0)
                items.append((label, val))

        config = generate_waterfall_config(items)
        return JsonResponse({"config": config, "chart_type": "waterfall"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_GET
def document_variance(request, doc_id):
    """
    GET /documents/<doc_id>/variance/
    Expects CSV with columns: Label, Actual, Budget.
    Returns variance Chart.js config + meta stats.
    """
    try:
        doc = Document.objects.get(id=doc_id, notebook__user=request.user)
    except Document.DoesNotExist:
        return JsonResponse({"error": "Document not found."}, status=404)

    try:
        import csv
        labels, actuals, budgets = [], [], []
        with open(doc.file.path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            cols   = reader.fieldnames or []
            for row in reader:
                def clean(c):
                    return float(str(row.get(c, 0)).replace(",", "").replace("£", "").replace("$", "").strip() or 0)
                labels.append(row[cols[0]])
                actuals.append(clean(cols[1]))
                budgets.append(clean(cols[2]) if len(cols) > 2 else 0.0)

        config = generate_variance_config(labels, actuals, budgets)
        return JsonResponse(config)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
def chart_dashboard(request):
    from notebooks.models import Notebook
    notebooks     = Notebook.objects.filter(user=request.user)
    csv_documents = Document.objects.filter(
        notebook__in=notebooks,
        title__iendswith='.csv'
    ).select_related('notebook').order_by('-uploaded_at')

    preselect_doc = request.GET.get('doc', '')   # ← new

    return render(request, r'chart_dashboard.html', {
        'csv_documents':  csv_documents,
        'preselect_doc':  preselect_doc,           # ← new
    })