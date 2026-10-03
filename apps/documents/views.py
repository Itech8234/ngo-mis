"""Document management views with versioning."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from pathlib import Path

from apps.audit.middleware import log_action

from apps.core.generic import GHDIListView, GHDICreateView, GHDIUpdateView, GHDidDetailView

from .forms import DocumentForm, DocumentVersionForm
from .models import AccessLevel, Document, DocumentVersion


def accessible_documents(user):
    """Apply the same access policy to document lists, details and downloads."""
    documents = Document.objects.all()
    if not user.has_perm("documents.view_restricted_document"):
        documents = documents.filter(~Q(access_level=AccessLevel.RESTRICTED) | Q(owner=user))
    if not user.has_perm("documents.view_confidential_document"):
        documents = documents.filter(~Q(access_level=AccessLevel.CONFIDENTIAL) | Q(owner=user))
    return documents


class DocumentListView(GHDIListView):
    model = Document
    permission_required = "documents.view_document"
    search_fields = ("title", "description", "tags")
    title = "Documents"

    def get_queryset(self):
        qs = accessible_documents(self.request.user).select_related("category", "owner")
        category = self.request.GET.get("category")
        access = self.request.GET.get("access")
        if category:
            qs = qs.filter(category_id=category)
        if access:
            qs = qs.filter(access_level=access)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from .models import DocumentCategory

        context["categories"] = DocumentCategory.objects.all()
        context["access_levels"] = AccessLevel.choices
        context["expiring"] = accessible_documents(self.request.user).filter(
            expires_at__isnull=False
        ).order_by("expires_at")[:5]
        return context


class DocumentDetailView(GHDidDetailView):
    model = Document
    permission_required = "documents.view_document"
    template_name = "documents/document_detail.html"

    def get_queryset(self):
        return accessible_documents(self.request.user).select_related("category", "owner")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["versions"] = self.object.versions.select_related("uploaded_by")
        context["version_form"] = DocumentVersionForm()
        return context


@login_required
@permission_required("documents.view_document", raise_exception=True)
def document_download(request, pk):
    document = get_object_or_404(accessible_documents(request.user), pk=pk)
    try:
        source = document.file.open("rb")
    except (FileNotFoundError, OSError, ValueError):
        raise Http404("The stored document is unavailable.")
    log_action(
        request.user, "download", module="documents", model="document",
        object_id=document.pk, object_repr=str(document), request=request,
    )
    response = FileResponse(source, as_attachment=True, filename=Path(document.file.name).name)
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "private, no-store"
    return response


@login_required
@permission_required("documents.view_document", raise_exception=True)
def document_version_download(request, pk, version_id):
    document = get_object_or_404(accessible_documents(request.user), pk=pk)
    version = get_object_or_404(DocumentVersion, document=document, pk=version_id)
    try:
        source = version.file.open("rb")
    except (FileNotFoundError, OSError, ValueError):
        raise Http404("The stored document version is unavailable.")
    log_action(
        request.user, "download_version", module="documents", model="document",
        object_id=document.pk, object_repr=f"{document} v{version.version}", request=request,
    )
    response = FileResponse(source, as_attachment=True, filename=Path(version.file.name).name)
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "private, no-store"
    return response


class DocumentCreateView(GHDICreateView):
    model = Document
    form_class = DocumentForm
    permission_required = "documents.add_document"
    template_name = "documents/document_form.html"
    title = "Upload Document"

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


class DocumentUpdateView(GHDIUpdateView):
    model = Document
    form_class = DocumentForm
    permission_required = "documents.change_document"
    template_name = "documents/document_form.html"
    title = "Edit Document"

    def get_queryset(self):
        return accessible_documents(self.request.user)


@login_required
@permission_required("documents.change_document", raise_exception=True)
def document_new_version(request, pk):
    document = get_object_or_404(accessible_documents(request.user), pk=pk)
    form = DocumentVersionForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        version = form.save(commit=False)
        version.document = document
        version.version = document.version + 1
        version.uploaded_by = request.user
        version.save()
        # Archive current file into history, then promote the new file
        DocumentVersion.objects.create(
            document=document, file=document.file, version=document.version,
            note="Archived before update", uploaded_by=request.user,
        )
        document.file = version.file
        document.version += 1
        document.save(update_fields=["file", "version", "updated_at"])
        messages.success(request, f"Document updated to version {document.version}.")
    return redirect("documents:document_detail", pk)
