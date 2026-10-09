"""CMS management views (internal)."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_POST
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.dateparse import parse_date

from apps.core.generic import GHDIListView, GHDICreateView, GHDIUpdateView, GHDidDetailView

from .forms import (
    CarouselSlideForm, EventForm, ImpactStatForm, MediaItemForm, NewsArticleForm, PageForm,
    PageSectionForm, TeamMemberForm,
)
from .models import (
    CarouselSlide, ContactMessage, Event, ImpactStat, MediaItem, NewsArticle, Page,
    PageSection, PageStatus, TeamMember,
)
from apps.partners.models import Partner
from apps.partners.views import PartnerCreateView as BasePartnerCreateView, PartnerListView as BasePartnerListView, PartnerUpdateView as BasePartnerUpdateView


@login_required
@permission_required("cms.view_page", raise_exception=True)
def cms_dashboard(request):
    from apps.hr.models import Department, Employee
    from apps.programs.models import Program, Project

    context = {
        "page_title": "CMS Dashboard",
        "pages": Page.objects.count(),
        "published_pages": Page.objects.filter(status="published").count(),
        "articles": NewsArticle.objects.count(),
        "published_articles": NewsArticle.objects.filter(status="published").count(),
        "events": Event.objects.count(),
        "media": MediaItem.objects.count(),
        "videos": MediaItem.objects.filter(media_type=MediaItem.MediaType.VIDEO).count(),
        "gallery_items": MediaItem.objects.filter(media_type=MediaItem.MediaType.IMAGE).count(),
        "team": TeamMember.objects.count(),
        "staff": Employee.objects.filter(status=Employee.Status.ACTIVE).count(),
        "departments": Department.objects.count(),
        "programs": Program.objects.count(),
        "projects": Project.objects.count(),
        "partners": Partner.objects.count(),
        "stats": ImpactStat.objects.count(),
        "messages_pending": ContactMessage.objects.filter(is_handled=False).count(),
        "recent_articles": NewsArticle.objects.order_by("-created_at")[:6],
        "recent_pages": Page.objects.order_by("-updated_at")[:6],
        "recent_messages": ContactMessage.objects.order_by("-created_at")[:6],
        "recent_events": Event.objects.order_by("-created_at")[:6],
        "recent_publications": NewsArticle.objects.filter(status="published").order_by("-publish_at", "-created_at")[:6],
    }
    return render(request, "cms/dashboard.html", context)


@login_required
@permission_required("cms.view_page", raise_exception=True)
def site_pages(request):
    """Index editable presentation content for every public landing route."""
    registry = [
        ("Homepage", "home", "/"), ("About", "about-us", "/about/"), ("Governance", "governance", "/governance/"),
        ("Programs", "programs", "/programs/"), ("Impact", "impact", "/impact/"), ("Partners", "partners", "/partners/"),
        ("Leadership", "leadership", "/leadership/"), ("Careers", "careers", "/careers/"), ("News", "news", "/news/"),
        ("Impact stories", "stories", "/stories/"), ("Events", "events", "/events/"), ("Gallery", "gallery", "/gallery/"),
        ("Videos", "videos", "/videos/"), ("Contact", "contact", "/contact/"), ("Support / donations", "donate", "/donate/"),
        ("Privacy policy", "privacy-policy", "/privacy-policy/"), ("Terms of use", "terms-of-use", "/terms-of-use/"),
    ]
    existing = {page.slug: page for page in Page.objects.filter(slug__in=[slug for _, slug, _ in registry])}
    rows = [{"title": title, "slug": slug, "route": route, "page": existing.get(slug)} for title, slug, route in registry]
    return render(request, "cms/site_pages.html", {"site_pages": rows, "page_title": "Website pages"})


class PageListView(GHDIListView):
    model = Page
    permission_required = "cms.view_page"
    search_fields = ("title", "slug")
    title = "Pages"

    def get_queryset(self):
        return super().get_queryset().select_related("author")


class ThematicPageListView(PageListView):
    title = "Thematic Areas"
    template_name = "cms/thematic_list.html"

    def get_queryset(self):
        return super().get_queryset().filter(page_type="thematic")

    def _auto_create_url(self):
        if self.request.user.has_perm("cms.add_page"):
            return reverse("cms:thematic_create")
        return None


class PageDetailView(GHDidDetailView):
    model = Page
    permission_required = "cms.view_page"
    template_name = "cms/page_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["sections"] = self.object.sections.all()
        context["section_form"] = PageSectionForm()
        return context


class PageCreateView(GHDICreateView):
    model = Page
    form_class = PageForm
    permission_required = "cms.add_page"
    template_name = "cms/page_form.html"
    title = "New Page"

    def get_initial(self):
        initial = super().get_initial()
        slug = self.request.GET.get("slug", "").strip()
        title = self.request.GET.get("page_title", "").strip()
        if slug and not Page.objects.filter(slug=slug).exists():
            initial.update({"slug": slug, "title": title or slug.replace("-", " ").title(), "status": "draft"})
        return initial

    def get_success_url(self):
        return reverse("cms:page_detail", args=[self.object.pk])


class ThematicPageCreateView(PageCreateView):
    title = "New Thematic Area"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields.pop("page_type", None)
        return form

    def form_valid(self, form):
        form.instance.page_type = "thematic"
        return super().form_valid(form)


class AboutPageCreateView(PageCreateView):
    title = "Create About Page"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields.pop("page_type", None)
        form.fields.pop("slug", None)
        return form

    def get_initial(self):
        initial = super().get_initial()
        initial.update({"title": "About us", "slug": "about-us", "page_type": "standard"})
        return initial

    def form_valid(self, form):
        form.instance.slug = "about-us"
        form.instance.page_type = "standard"
        return super().form_valid(form)


class PageUpdateView(GHDIUpdateView):
    model = Page
    form_class = PageForm
    permission_required = "cms.change_page"
    template_name = "cms/page_form.html"
    title = "Edit Page"

    def get_success_url(self):
        return reverse("cms:page_detail", args=[self.object.pk])


@login_required
def about_page_manage(request):
    page = Page.objects.filter(slug="about-us").first()
    if page:
        if request.user.has_perm("cms.change_page"):
            return redirect("cms:page_edit", pk=page.pk)
        if request.user.has_perm("cms.view_page"):
            return redirect("cms:page_detail", pk=page.pk)
        raise PermissionDenied
    if request.user.has_perm("cms.add_page"):
        return redirect("cms:about_page_create")
    raise PermissionDenied


@login_required
@permission_required("cms.change_page", raise_exception=True)
def page_section_add(request, pk):
    page = get_object_or_404(Page, pk=pk)
    form = PageSectionForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        section = form.save(commit=False)
        section.page = page
        section.save()
        messages.success(request, "Section added.")
    return redirect("cms:page_detail", pk)


@login_required
@permission_required("cms.change_page", raise_exception=True)
@require_POST
def page_section_delete(request, pk, section_id):
    get_object_or_404(PageSection, pk=section_id, page_id=pk).delete()
    messages.success(request, "Section removed.")
    return redirect("cms:page_detail", pk)


class NewsListView(GHDIListView):
    model = NewsArticle
    permission_required = "cms.view_newsarticle"
    search_fields = ("title", "summary")
    title = "News & Stories"
    template_name = "cms/news_list.html"

    def get_queryset(self):
        qs = super().get_queryset()
        category = self.request.GET.get("category", "")
        status = self.request.GET.get("status", "")
        if category in NewsArticle.Category.values:
            qs = qs.filter(category=category)
        if status in PageStatus.values:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = NewsArticle.Category.choices
        context["statuses"] = PageStatus.choices
        return context


class NewsDetailView(GHDidDetailView):
    model = NewsArticle
    permission_required = "cms.view_newsarticle"
    template_name = "cms/news_detail.html"


class NewsCreateView(GHDICreateView):
    model = NewsArticle
    form_class = NewsArticleForm
    permission_required = "cms.add_newsarticle"
    template_name = "cms/news_form.html"
    title = "Write Article"

    def get_success_url(self):
        return reverse("cms:news_detail", args=[self.object.pk])


class NewsUpdateView(GHDIUpdateView):
    model = NewsArticle
    form_class = NewsArticleForm
    permission_required = "cms.change_newsarticle"
    template_name = "cms/news_form.html"
    title = "Edit Article"

    def get_success_url(self):
        return reverse("cms:news_detail", args=[self.object.pk])


@login_required
@permission_required("cms.publish_article", raise_exception=True)
@require_POST
def news_publish(request, pk):
    article = get_object_or_404(NewsArticle, pk=pk)
    article.status = "published"
    article.publish_at = article.publish_at or timezone.now()
    article.save(update_fields=["status", "publish_at", "updated_at"])
    messages.success(request, "Article published.")
    return redirect("cms:news_detail", pk)


@login_required
@permission_required("cms.publish_article", raise_exception=True)
@require_POST
def news_unpublish(request, pk):
    article = get_object_or_404(NewsArticle, pk=pk)
    article.status = "draft"
    article.save(update_fields=["status", "updated_at"])
    messages.success(request, "Article returned to draft and removed from the public site.")
    return redirect("cms:news_detail", pk)


@login_required
@permission_required("cms.change_page", raise_exception=True)
@require_POST
def page_publish(request, pk):
    page = get_object_or_404(Page, pk=pk)
    page.status = "published"
    page.publish_at = page.publish_at or timezone.now()
    page.save(update_fields=["status", "publish_at", "updated_at"])
    messages.success(request, "Page published.")
    return redirect("cms:page_detail", pk)


@login_required
@permission_required("cms.change_page", raise_exception=True)
@require_POST
def page_unpublish(request, pk):
    page = get_object_or_404(Page, pk=pk)
    page.status = "draft"
    page.save(update_fields=["status", "updated_at"])
    messages.success(request, "Page returned to draft and removed from the public site.")
    return redirect("cms:page_detail", pk)


@login_required
@require_POST
def content_delete(request, content_type, pk):
    models = {
        "page": (Page, "cms.delete_page", "cms:page_list", "Page deleted."),
        "news": (NewsArticle, "cms.delete_newsarticle", "cms:news_list", "Article deleted."),
        "event": (Event, "cms.delete_event", "cms:event_list", "Event deleted."),
        "impact": (ImpactStat, "cms.delete_impactstat", "cms:impact_list", "Impact statistic deleted."),
        "team": (TeamMember, "cms.delete_teammember", "cms:team_list", "Team member deleted."),
        "media": (MediaItem, "cms.delete_mediaitem", "cms:media_list", "Media record deleted."),
    }
    selected = models.get(content_type)
    if selected is None:
        raise PermissionDenied
    model, permission, success_route, notice = selected
    if not request.user.has_perm(permission):
        raise PermissionDenied
    get_object_or_404(model, pk=pk).delete()
    messages.success(request, notice)
    return redirect(success_route)


@login_required
@permission_required("partners.delete_partner", raise_exception=True)
@require_POST
def partner_delete(request, pk):
    get_object_or_404(Partner, pk=pk).delete()
    messages.success(request, "Partner deleted.")
    return redirect("cms:partner_list")


class CMSPartnerCreateView(BasePartnerCreateView):
    def get_success_url(self):
        return reverse("cms:partner_list")


class CMSPartnerListView(BasePartnerListView):
    def _auto_create_url(self):
        if self.request.user.has_perm("partners.add_partner"):
            return reverse("cms:partner_create")
        return None


class CMSPartnerUpdateView(BasePartnerUpdateView):
    def get_success_url(self):
        return reverse("cms:partner_list")


class EventListView(GHDIListView):
    model = Event
    permission_required = "cms.view_event"
    search_fields = ("name", "venue")
    title = "Events"
    template_name = "cms/event_list.html"

    def get_queryset(self):
        qs = super().get_queryset()
        status = self.request.GET.get("status", "")
        start_date = self.request.GET.get("start_date", "")
        end_date = self.request.GET.get("end_date", "")
        if status in Event.Status.values:
            qs = qs.filter(status=status)
        if parsed_start := parse_date(start_date):
            qs = qs.filter(date__gte=parsed_start)
        if parsed_end := parse_date(end_date):
            qs = qs.filter(date__lte=parsed_end)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["statuses"] = Event.Status.choices
        return context


class EventCreateView(GHDICreateView):
    model = Event
    form_class = EventForm
    permission_required = "cms.add_event"
    template_name = "cms/event_form.html"
    title = "New Event"
    success_url = reverse_lazy("cms:event_list")


class EventUpdateView(GHDIUpdateView):
    model = Event
    form_class = EventForm
    permission_required = "cms.change_event"
    template_name = "cms/event_form.html"
    title = "Edit Event"
    success_url = reverse_lazy("cms:event_list")


class MediaListView(GHDIListView):
    model = MediaItem
    permission_required = "cms.view_mediaitem"
    search_fields = ("title", "tags", "category")
    title = "Media Library"

    def get_queryset(self):
        qs = super().get_queryset()
        media_type = self.request.GET.get("type") or getattr(self, "default_type", "")
        if media_type:
            qs = qs.filter(media_type=media_type)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["types"] = MediaItem.MediaType.choices
        return context


class GalleryMediaListView(MediaListView):
    default_type = MediaItem.MediaType.IMAGE
    title = "Gallery"


class VideoMediaListView(MediaListView):
    default_type = MediaItem.MediaType.VIDEO
    title = "Videos"


class MediaDetailView(GHDidDetailView):
    model = MediaItem
    permission_required = "cms.view_mediaitem"
    template_name = "cms/media_detail.html"


class MediaCreateView(GHDICreateView):
    model = MediaItem
    form_class = MediaItemForm
    permission_required = "cms.add_mediaitem"
    template_name = "cms/media_form.html"
    title = "Upload Media"

    def get_initial(self):
        initial = super().get_initial()
        media_type = self.request.GET.get("media_type")
        if media_type in MediaItem.MediaType.values:
            initial["media_type"] = media_type
        return initial

    def form_valid(self, form):
        form.instance.uploaded_by = self.request.user
        return super().form_valid(form)


class MediaUpdateView(GHDIUpdateView):
    model = MediaItem
    form_class = MediaItemForm
    permission_required = "cms.change_mediaitem"
    template_name = "cms/media_form.html"
    title = "Edit Media"


class ImpactStatListView(GHDIListView):
    model = ImpactStat
    permission_required = "cms.view_impactstat"
    title = "Impact Statistics"


class ImpactStatCreateView(GHDICreateView):
    model = ImpactStat
    form_class = ImpactStatForm
    permission_required = "cms.add_impactstat"
    template_name = "cms/impact_form.html"
    title = "New Impact Statistic"
    success_url = reverse_lazy("cms:impact_list")


class ImpactStatUpdateView(GHDIUpdateView):
    model = ImpactStat
    form_class = ImpactStatForm
    permission_required = "cms.change_impactstat"
    template_name = "cms/impact_form.html"
    title = "Edit Impact Statistic"
    success_url = reverse_lazy("cms:impact_list")


class TeamListView(GHDIListView):
    model = TeamMember
    permission_required = "cms.view_teammember"
    title = "Leadership & Governance"


class TeamCreateView(GHDICreateView):
    model = TeamMember
    form_class = TeamMemberForm
    permission_required = "cms.add_teammember"
    template_name = "cms/team_form.html"
    title = "Add Team Member"
    success_url = reverse_lazy("cms:team_list")


class TeamUpdateView(GHDIUpdateView):
    model = TeamMember
    form_class = TeamMemberForm
    permission_required = "cms.change_teammember"
    template_name = "cms/team_form.html"
    title = "Edit Team Member"
    success_url = reverse_lazy("cms:team_list")


@login_required
@permission_required("cms.change_contactmessage", raise_exception=True)
def message_list(request):
    messages_qs = ContactMessage.objects.order_by("-created_at")
    return render(request, "cms/message_list.html", {"messages_qs": messages_qs, "page_title": "Contact Messages"})


@login_required
@permission_required("cms.change_contactmessage", raise_exception=True)
@require_POST
def message_handle(request, pk):
    message = get_object_or_404(ContactMessage, pk=pk)
    message.is_handled = not message.is_handled
    message.save(update_fields=["is_handled"])
    return redirect("cms:message_list")


class CarouselListView(GHDIListView):
    model = CarouselSlide
    permission_required = "cms.view_carouselslide"
    title = "Homepage Carousel"


class CarouselCreateView(GHDICreateView):
    model = CarouselSlide
    form_class = CarouselSlideForm
    permission_required = "cms.add_carouselslide"
    template_name = "cms/carousel_form.html"
    title = "Add Carousel Slide"


class CarouselUpdateView(GHDIUpdateView):
    model = CarouselSlide
    form_class = CarouselSlideForm
    permission_required = "cms.change_carouselslide"
    template_name = "cms/carousel_form.html"
    title = "Edit Carousel Slide"


@login_required
@permission_required("cms.delete_carouselslide", raise_exception=True)
@require_POST
def carousel_delete(request, pk):
    get_object_or_404(CarouselSlide, pk=pk).delete()
    messages.success(request, "Carousel slide deleted.")
    return redirect("cms:carousel_list")


