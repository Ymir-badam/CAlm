from django.http import StreamingHttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from requests import session

from .models import ChatSession, Message
from notebooks.models import Notebook
from documents.models import Document

from rag.search import hybrid_search,full_scan
from rag.reranker import rerank
from llm.factory import get_llm
from .tokens import count_tokens
from .credits import calculate_cost
import csv

import os
import google.generativeai as genai
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# ===============================
# Create Chat Session
# ===============================
@login_required
def create_chat_session(request, notebook_id):
    notebook = get_object_or_404(
        Notebook,
        id=notebook_id,
        user=request.user
    )

    if request.method == "POST":
        selected_doc_ids = request.POST.getlist("documents")
        print("Selected Document IDs:", selected_doc_ids)

        session = ChatSession.objects.create(notebook=notebook)

        if selected_doc_ids:
            session.selected_documents.set(selected_doc_ids)

        return redirect("chat_page", session_id=session.id)

    return redirect("notebook_detail", notebook_id=notebook.id)


# ===============================
# Chat Streaming Endpoint
# ===============================
import json
from users.models import DailyActivitySummary
from concurrent.futures import ThreadPoolExecutor
from django.db.models import F
from django.utils import timezone
@login_required
def chat_stream(request, session_id):

    session = get_object_or_404(
        ChatSession,
        id=session_id,
        notebook__user=request.user
    )

    if request.method == "POST":
        data = json.loads(request.body)
        query = data.get("query")
        document_ids = data.get("documents", [])
        list_of_titles=[]
        for i in document_ids:
            document=Document.objects.get(id=i)
            list_of_titles.append(document.title)
    else:
        return StreamingHttpResponse("Invalid request method")
    

    if not query or not isinstance(query, str) or query.strip() == "":
        return StreamingHttpResponse("Query cannot be empty")

    ######################Kundey mova query validation and sanitization phase###########
    prompt_validation= f"""
    
    These are the documents available for reference:

    {", ".join(list_of_titles) if list_of_titles else "No documents selected"}
    
    classify the query : {query}
 into one of the following categories:
1 Non RAG if it can be answered without referring to the document
2 RAG if it requires retrieval of specific information from the document
3 FULL SCAN if it asks for analysis, conclusions, or insights based on the entire document 
4 UNKNOWN if it cannot be classified into the above categories
5 EMPTY if the query is empty or contains only whitespace
Provide only the category name as the answer.

"""
    # model = genai.GenerativeModel("gemini-2.0-flash-lite")
    # response_valid=model.generate_content(prompt_validation)
    if len(list_of_titles)>0:
        category ="RAG"
    else:
        category="Non RAG"
    print("Query Category:", category)
    if category == "Non RAG":
        input_tokens = count_tokens(query)
        llm = get_llm("gemini-2.5-flash")
        user_msg=query
        query+="Format your response using Markdown: use ## for section headings, **bold** for key terms, bullet lists for enumerated points, and | tables | for structured comparisons or data. give me output not more than 1000 tokens"
        query+="\n\nAlso, if the question is related to CA exams, provide exam-focused insights, tips, and examples relevant to the Indian context."
        query+="\n\nFor numerical problems, show complete step-by-step working with journal entries or calculations as appropriate."
        query+="\n\nHighlight exam-critical points with '⚠ Exam tip:' — e.g., common MCQ traps, mark-heavy topics, or examiner-favoured phrasings."
        query+="\n\nUse ₹ for all monetary amounts and give India-specific examples where helpful."
        query+="\n\nIf the question spans multiple CA levels or topics, clarify which level the answer applies to."
        query+="\n\nKeep your tone clear, concise, and encouraging — students may be stressed. and output should not more than 1000 tokens."
        llm_response = llm.generate(query)
        output_tokens = count_tokens(llm_response)
        cost = calculate_cost(
                        "gemini-2.5-flash",
                        input_tokens,
                        output_tokens
                    )
        obj, created = DailyActivitySummary.objects.get_or_create(
        user=request.user,
        date=timezone.now().date(),
        defaults={'total_count': 1}  # starts at 1 on first activity
        )

        if not created:
            DailyActivitySummary.objects.filter(pk=obj.pk).update(
                total_count=F('total_count') + 1
            )


        Message.objects.create(
                            session=session,
                            role="user",
                            content=user_msg,
                            input_tokens=input_tokens,
                            output_tokens=0,
                            credits_used=0
                        )

        Message.objects.create(
                            session=session,
                            role="assistant",
                            content=llm_response,
                            sources = ["General CA syllabus"] ,
                            input_tokens=input_tokens,
                            output_tokens=output_tokens,
                            credits_used=cost
                        )
        return StreamingHttpResponse(llm_response, content_type="text/plain")
    elif category in ["RAG", "FULL SCAN"]:

        documents = Document.objects.filter(
            id__in=document_ids
        )
        for i in document_ids:
            document = Document.objects.get(id=i)
            print("Documents for RAG:", document)

        all_results = []
        if not documents.exists():
            return StreamingHttpResponse("No documents selected for RAG")
        


        if category == "RAG":

            for doc in documents:
                title = Document.objects.get(id=doc.id)
                if "csv" in title.title.lower():
                    with open(title.file.path, "r", encoding="utf-8") as f:
                        reader = csv.DictReader(f)
                        rows = list(reader)
                    results = "\n".join(
                        ", ".join(f"{k}: {v}" for k, v in row.items() if str(v).strip())
                        for row in rows
                    )

                    all_results.append(results)
                else:
                    results = hybrid_search(doc, query)
                    all_results.extend([r["text"] for r in results if "text" in r])

            if not all_results:
                return StreamingHttpResponse("No relevant context found")

            reranked = rerank(query, all_results)
            top_context = "\n\n".join(
            [r for r in reranked[:5]]
            )
            # Get top document IDs
            top_doc_ids = [doc.id for doc in session.selected_documents.all()[:3]]  
            messages = session.message_set.all().order_by("created_at")
            print(messages)
            chat_conversation = "\n".join(
                [f"{m.role.capitalize()}: {m.content}" for m in messages]
            )
            
            prompt = f"""You are an expert CA exam tutor helping Indian students prepare for ICAI's CA Foundation, Intermediate, and Final level exams.

            CONTEXT (from study material):
            {top_context}

            CHAT HISTORY:
            {chat_conversation}

            STUDENT'S QUESTION:
            {query}

            INSTRUCTIONS:
            - Answer based on the context provided. If the answer is not in the context, answer from your knowledge base.
            - Cite relevant sections, acts, or standards where applicable (e.g., AS, Ind AS, GST Act, Companies Act 2013, Income Tax Act).
            - Use ₹ for all monetary amounts and give India-specific examples where helpful.
            - For numerical problems, show complete step-by-step working with journal entries or calculations as appropriate.
            - Highlight exam-critical points with "⚠ Exam tip:" — e.g., common MCQ traps, mark-heavy topics, or examiner-favoured phrasings.
            - Keep your tone clear, concise, and encouraging — students may be stressed.
            - If the question spans multiple CA levels or topics, clarify which level the answer applies to.
            - Also, if the question is related to CA exams, provide exam-focused insights, tips, and examples relevant to the Indian context."
            - For numerical problems, show complete step-by-step working with journal entries or calculations as appropriate."
        -Highlight exam-critical points with '⚠ Exam tip:' — e.g., common MCQ traps, mark-heavy topics, or examiner-favoured phrasings."
        -Use ₹ for all monetary amounts and give India-specific examples where helpful."
        -If the question spans multiple CA levels or topics, clarify which level the answer applies to."
        -Keep your tone clear, concise, and encouraging — students may be stressed. and output should not more than 1000 tokens."
            """

            input_tokens = count_tokens(prompt)
            profile = request.user.userprofile

            if profile.credits_balance <= 0:
                return StreamingHttpResponse("No credits remaining")

            llm = get_llm("gemini-2.5-flash")

            # ----------------------------
            # Streaming Generator
            # ----------------------------
            def generate():
                output_text = ""

                try:
                    for chunk in llm.generate(prompt):
                        output_text += chunk
                        yield chunk

                    output_tokens = count_tokens(output_text)
                    cost = calculate_cost(
                        "gemini-2.5-flash",
                        input_tokens,
                        output_tokens
                    )

                    # Atomic DB update
                    with transaction.atomic():
                        profile.credits_balance -= cost
                        profile.total_tokens_used += (
                            input_tokens + output_tokens
                        )
                        profile.save()
                        obj, created = DailyActivitySummary.objects.get_or_create(
                        user=request.user,
                        date=timezone.now().date(),
                        defaults={'total_count': 1}  # starts at 1 on first activity
                        )

                        if not created:
                            DailyActivitySummary.objects.filter(pk=obj.pk).update(
                                total_count=F('total_count') + 1
                            )

                        Message.objects.create(
                            session=session,
                            role="user",
                            content=query,
                            input_tokens=input_tokens,
                            output_tokens=0,
                            credits_used=0
                        )

                        Message.objects.create(
                            session=session,
                            role="assistant",
                            content=output_text,
                            sources = ["Unknown"] * len(reranked[:5]), # save list of docs
                            input_tokens=input_tokens,
                            output_tokens=output_tokens,
                            credits_used=cost
                        )

                except Exception as e:
                    yield f"\n\nError: {str(e)}"

            response = StreamingHttpResponse(generate(), content_type="text/plain")
            response["X-Top-Docs"] = json.dumps(top_doc_ids)
            return response
        elif category == "FULL SCAN":
            all_summaries = []
            total_input_tokens = 0
            
            def process_doc(doc):
                return full_scan(doc, query) 

            with ThreadPoolExecutor(max_workers=5) as executor:
                all_summaries = list(executor.map(process_doc, documents))

            combined_summary_text = "\n\n".join(all_summaries)
            final_prompt = f"Summarize these analyses for the query: {query}\n\n{combined_summary_text}"
            
            # 3. Create a Generator for Streaming
            def generate_full_scan():
                nonlocal total_input_tokens
                full_response_text = ""
                
                # Count tokens for the aggregate prompt
                total_input_tokens = count_tokens(final_prompt) 
                
                # Use streaming for the final reduction
                # stream = model.generate_content(final_prompt, stream=True)
                stream=["yeah sure ", "this is a streamed response ", "for the full scan category."] # Mock stream for testing
                for chunk in stream:
                    full_response_text += chunk.text
                    yield chunk.text

                # 4. Post-stream processing (Credits & DB)
                output_tokens = count_tokens(full_response_text)
                cost = calculate_cost("gemini-2.5-flash", total_input_tokens, output_tokens)
                
                with transaction.atomic():
                    profile.credits_balance -= cost
                    profile.save()
                    # Create your Message objects here...

            return StreamingHttpResponse(generate_full_scan(), content_type="text/plain")
            
        else:
            return StreamingHttpResponse("Query cannot be classified or is empty")


# ===============================
# Chat Page
# ===============================
import markdown as md_lib

@login_required
def chat_page(request, session_id):
    session = get_object_or_404(
        ChatSession,
        id=session_id,
        notebook__user=request.user
    )

    messages = session.message_set.all().order_by("created_at")

    # Pre-render markdown for assistant messages
    for msg in messages:
        if msg.role == "assistant":
            msg.rendered_content = md_lib.markdown(
                msg.content,
                extensions=['tables', 'fenced_code', 'nl2br']
            )

    return render(request, "chat.html", {
        "session": session,
        "messages": messages
    })

# ===============================
# Toggle Document Selection (AJAX)
# ===============================
@login_required
@require_POST
def toggle_document(request, session_id):

    session = get_object_or_404(
        ChatSession,
        id=session_id,
        notebook__user=request.user
    )

    doc_id = request.POST.get("document_id")

    document = get_object_or_404(
        Document,
        id=doc_id,
        notebook=session.notebook
    )

    if session.selected_documents.filter(id=document.id).exists():
        session.selected_documents.remove(document)
        action = "removed"
    else:
        session.selected_documents.add(document)
        action = "added"

    return JsonResponse({
        "status": "success",
        "action": action
    })