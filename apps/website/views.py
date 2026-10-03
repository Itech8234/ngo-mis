"""Public website views + PWA endpoints."""
from types import SimpleNamespace

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.db.models import Q

from .forms import ContactForm


def _published_pages():
    from apps.cms.models import Page

    return Page.objects.filter(status="published")


def home(request):
    from apps.cms.models import CarouselSlide, Event, ImpactStat, NewsArticle
    from apps.cms.models import Page as CmsPage
    from apps.partners.models import Partner
    from apps.programs.models import Program

    cms_slides = [slide for slide in CarouselSlide.objects.filter(is_active=True) if slide.image_url]
    hero_slides = [
        {
            "image": slide.image_url,
            "image_alt": slide.image_alt or slide.title,
            "eyebrow": slide.eyebrow,
            "title": slide.title,
            "title_highlight": slide.title_highlight,
            "subtitle": slide.subtitle,
            "cta_url": slide.cta_url,
            "cta_label": slide.cta_label,
            "secondary_url": slide.secondary_url,
            "secondary_label": slide.secondary_label,
        }
        for slide in cms_slides
    ]
    from apps.core.templatetags.ghdi_extras import video_embed_url

    featured_video = next(
        (
            article
            for article in NewsArticle.objects.filter(status="published")
            .exclude(video_url="")
            .order_by("-publish_at", "-created_at")
            if video_embed_url(article.video_url)
        ),
        None,
    )
    context = {
        "page_title": "Home",
        "featured_programs": Program.objects.filter(status="active")[:3],
        "thematic_pages": CmsPage.objects.filter(
            page_type="thematic", status="published"
        ).filter(Q(publish_at__isnull=True) | Q(publish_at__lte=timezone.now())).order_by("nav_order", "title"),
        "impact_stats": ImpactStat.objects.filter(is_active=True)[:6],
        "latest_news": NewsArticle.objects.filter(status="published", category="news").order_by("-publish_at").select_related("author")[:3],
        "latest_stories": NewsArticle.objects.filter(status="published", category="story").order_by("-publish_at").select_related("author")[:3],
        "upcoming_events": Event.objects.filter(status="upcoming").order_by("date")[:3],
        # Logo wall: show every published partner — those with an uploaded logo
        # render the logo image, the rest render a branded monogram lockup, so
        # the marquee is never empty just because artwork is pending.
        "partners": Partner.objects.filter(show_on_website=True)[:12],
        "featured_video": featured_video,
        "about": CmsPage.objects.filter(slug="about-us", status="published").first(),
        "nav_pages": _published_pages().filter(show_in_nav=True).order_by("nav_order"),
        # Published CMS slides take priority; bundled slides keep the homepage
        # presentable until editors add their first slide.
        "hero_slides": hero_slides or [
            {
                "image": "https://images.unsplash.com/photo-1500648702958-65bf62c1a7bc?auto=format&fit=crop&w=1920&q=70",
                "image_alt": "Community members gathered together",
                "eyebrow": "Humanitarian & Development · Yobe State, Nigeria",
                "title": "Protecting and empowering",
                "title_highlight": "vulnerable communities",
                "subtitle": "GHDI works with communities in northeast Nigeria to deliver protection, education, and community resilience — driven by local leadership, transparency and accountability.",
                "cta_url": reverse("website:programs"),
                "cta_label": "Explore our programs",
                "secondary_url": reverse("website:impact"),
                "secondary_label": "See our impact",
            },
            {
                "image": "https://images.unsplash.com/photo-1529075586666-549f440e3b6f?auto=format&fit=crop&w=1920&q=70",
                "image_alt": "Children learning in a classroom",
                "eyebrow": "Education for every child",
                "title": "Safe learning for",
                "title_highlight": "children and young people",
                "subtitle": "We support access to quality, safe education that builds futures and strengthens communities for generations to come.",
                "cta_url": reverse("website:programs"),
                "cta_label": "Our education work",
                "secondary_url": reverse("website:about"),
                "secondary_label": "About GHDI",
            },
            {
                "image": "https://images.unsplash.com/photo-1469571486292-0ba58a3f068b?auto=format&fit=crop&w=1920&q=70",
                "image_alt": "Partners joining hands at a community meeting",
                "eyebrow": "Locally led solutions",
                "title": "Together, for",
                "title_highlight": "locally led change",
                "subtitle": "We partner with local organisations and communities to design and deliver solutions that last, because local voices know best.",
                "cta_url": reverse("website:partners"),
                "cta_label": "See our partners",
                "secondary_url": reverse("website:contact"),
                "secondary_label": "Work with us",
            },
            {
                "image": "https://images.unsplash.com/photo-1488521787991-ed7bbaae773c?auto=format&fit=crop&w=1920&q=70",
                "image_alt": "Volunteers distributing supplies to a community",
                "eyebrow": "Accountability & transparency",
                "title": "Every contribution,",
                "title_highlight": "measurable impact",
                "subtitle": "We track, report and publish our results so that communities, partners and donors can see exactly what their support achieves.",
                "cta_url": reverse("website:impact"),
                "cta_label": "Read our results",
                "secondary_url": reverse("website:governance"),
                "secondary_label": "Our governance",
            },
        ],
    }
    return render(request, "website/home.html", context)


def page_detail(request, slug):
    from apps.cms.models import Page as CmsPage

    page = get_object_or_404(CmsPage, slug=slug)
    if not page.is_live and not request.user.is_authenticated:
        from django.http import Http404

        raise Http404("Page not found")
    if page.page_type == "thematic":
        return render(request, "website/thematic.html", {"page": page, "sections": page.sections.all(), "nav_pages": _published_pages().filter(show_in_nav=True).order_by("nav_order")})
    context = {
        "page": page,
        "sections": page.sections.all(),
        "nav_pages": _published_pages().filter(show_in_nav=True).order_by("nav_order"),
    }
    template = "website/governance.html" if page.page_type == "governance" else "website/page.html"
    return render(request, template, context)


def _contact_email():
    """Public contact address, taken from organisation settings where set."""
    try:
        from apps.core.models import OrganizationSetting

        org = OrganizationSetting.load()
        if org is not None and getattr(org, "email", ""):
            return org.email
    except Exception:  # database not yet migrated
        pass
    return getattr(settings, "GHDI_ORG_EMAIL", "info@ghdi.org.ng")


def _fallback_page(title, summary, content, page_type="standard"):
    """Bundled copy for a permanent public page whose CMS row is absent.

    A fresh install (or a test database) has no CMS rows yet, but ``/about/``,
    ``/governance/``, ``/privacy-policy/`` and ``/terms-of-use/`` are permanent
    addresses linked from the header, the footer and external partners, so they
    must never 404. Bundled copy keeps the site navigable until an editor
    publishes the real page, which then wins.
    """
    return SimpleNamespace(
        title=title,
        summary=summary,
        content=content,
        seo_title=title,
        seo_description=summary,
        featured_image="",
        page_type=page_type,
        sections=[],
    )


def _render_cms_page(request, slug, fallback):
    """Render a permanent public page from the CMS, falling back to bundled copy.

    Mirrors ``page_detail`` visibility rules: an unpublished draft is previewable
    by authenticated staff only; everyone else sees the published page or the
    bundled default.
    """
    from apps.cms.models import Page as CmsPage

    page = CmsPage.objects.filter(slug=slug).first()
    if page is not None and not page.is_live and not request.user.is_authenticated:
        page = None
    context = {
        "page": page if page is not None else fallback,
        "sections": page.sections.all() if page is not None else [],
        "nav_pages": _published_pages().filter(show_in_nav=True).order_by("nav_order"),
    }
    page_type = getattr(context["page"], "page_type", "standard")
    template = "website/governance.html" if page_type == "governance" else "website/page.html"
    return render(request, template, context)


def about(request):
    return _render_cms_page(
        request,
        "about-us",
        _fallback_page(
            "About us",
            f"{settings.GHDI_ORG_NAME} is a Nigerian humanitarian and development "
            "organisation working with vulnerable communities across northeast Nigeria.",
            "We work alongside communities, local authorities and partners to deliver "
            "protection, education and community resilience programming. Our teams are "
            "recruited locally, decisions are taken with community leadership, and results "
            "are tracked, reported and published so that partners and communities can see "
            "what their support achieves.\n\n"
            "Our work is guided by humanitarian principles, safeguarding standards and a "
            "commitment to transparency and accountability at every level of the "
            "organisation.",
        ),
    )


def governance(request):
    return _render_cms_page(
        request,
        "governance",
        _fallback_page(
            "Governance & accountability",
            "How GHDI is governed, how decisions are made, and how we stay accountable "
            "to the communities and partners we serve.",
            "An independent board provides strategic oversight and approves our policies, "
            "budgets and annual reports. Day-to-day delivery is led by the management team, "
            "with programme, finance, procurement, human resources and monitoring & "
            "evaluation functions each accountable for their own controls.\n\n"
            "We operate documented safeguarding, financial control, procurement and data "
            "protection policies, and results are tracked against indicators and reported to "
            "partners and communities.",
            page_type="governance",
        ),
    )
def privacy(request):
    return _render_cms_page(
        request,
        "privacy-policy",
        _fallback_page(
            "Privacy policy",
            f"How {settings.GHDI_ORG_NAME} collects, uses and protects personal data.",
            "This policy explains what personal information we collect through this "
            "website, why we collect it, and the choices you have.\n\n"
            "Information we collect. When you use our contact form, subscribe to updates or "
            "pledge a donation we collect the details you provide — typically your name, "
            "email address, telephone number and the content of your message. We also record "
            "standard technical information such as pages requested, browser type and IP "
            "address, which we use to keep the site secure and available.\n\n"
            "How we use it. We use your information to respond to your enquiry, to process "
            "and acknowledge donations, to send updates you have asked for, and to protect "
            "the website and its users. We do not sell personal data.\n\n"
            "Sharing. We share information only with service providers who help us operate "
            "this website and deliver services, and where required by Nigerian law or by a "
            "funder's audit obligation.\n\n"
            "Retention and your rights. We keep personal data only as long as it is needed "
            "for the purpose it was collected for. You may ask us to access, correct or "
            "delete the information we hold about you.\n\n"
            "Cookies. We use only the cookies required for security and for remembering your "
            "preferences. We do not run third-party advertising trackers.\n\n"
            "Contact. Questions about this policy can be sent to " + _contact_email() + ".",
        ),
    )


def terms(request):
    return _render_cms_page(
        request,
        "terms-of-use",
        _fallback_page(
            "Terms of use",
            f"The terms that apply when you use the {settings.GHDI_ORG_NAME} website.",
            "Acceptance. By using this website you accept these terms. If you do not accept "
            "them, please do not use the site.\n\n"
            "Permitted use. You may browse, download and print material for your own "
            "reference. You may not use the site to break the law, interfere with its "
            "operation, or attempt to gain access to systems or data you are not authorised "
            "to use.\n\n"
            "Intellectual property. Reports, photographs, logos and written content remain "
            "the property of the organisation or its licensors. Please credit us when "
            "reproducing material for non-commercial, educational purposes.\n\n"
            "Accuracy. We aim to keep published information current, but organisational and "
            "programme data is updated periodically and is provided for general information.\n\n"
            "Donations. Pledges made through this website are recorded in good faith and "
            "acknowledged by our team. Contact us immediately if you believe a pledge was "
            "recorded in error.\n\n"
            "External links. Links to other websites are provided for convenience; we are "
            "not responsible for their content.\n\n"
            "Liability. The website is provided on an 'as is' basis and, to the extent "
            "permitted by law, we are not liable for indirect or consequential loss arising "
            "from its use.\n\n"
            "Changes. We may update these terms; the current version always appears on this "
            "page.\n\n"
            "Governing law. These terms are governed by the laws of the Federal Republic of "
            "Nigeria.\n\n"
            "Contact. Questions about these terms can be sent to " + _contact_email() + ".",
        ),
    )





def news_list(request, category=None):
    from apps.cms.models import NewsArticle

    articles = NewsArticle.objects.filter(status="published").order_by("-publish_at")
    if category:
        articles = articles.filter(category=category)
    featured = articles.filter(is_featured=True).first()
    return render(
        request,
        "website/news_list.html",
        {"articles": articles[:24], "featured": featured, "category": category, "nav_pages": _published_pages().filter(show_in_nav=True).order_by("nav_order")},
    )


def stories(request):
    return news_list(request, category="story")


def news_detail(request, slug):
    from apps.cms.models import NewsArticle

    article = get_object_or_404(NewsArticle, slug=slug)
    if not article.is_live and not request.user.is_authenticated:
        from django.http import Http404

        raise Http404("Article not found")
    article.views += 1
    article.save(update_fields=["views"])
    related = NewsArticle.objects.filter(status="published", category=article.category).exclude(pk=article.pk)[:3]
    return render(request, "website/news_detail.html", {"article": article, "related": related, "nav_pages": _published_pages().filter(show_in_nav=True).order_by("nav_order")})


def events_list(request):
    from apps.cms.models import Event

    upcoming = Event.objects.filter(status="upcoming").order_by("date")
    past = Event.objects.filter(status="completed").order_by("-date")[:6]
    return render(request, "website/events.html", {"upcoming": upcoming, "past": past, "nav_pages": _published_pages().filter(show_in_nav=True).order_by("nav_order")})


def event_detail(request, slug):
    from apps.cms.models import Event

    event = get_object_or_404(Event, slug=slug)
    return render(request, "website/event_detail.html", {"event": event, "nav_pages": _published_pages().filter(show_in_nav=True).order_by("nav_order")})


def impact(request):
    from apps.beneficiaries.models import Beneficiary
    from apps.cms.models import ImpactStat, NewsArticle
    from apps.programs.models import Project

    stats = list(ImpactStat.objects.filter(is_active=True))
    if not stats:
        stats = [
            {"label": "People Reached", "value": Beneficiary.objects.filter(is_active=True).count(), "suffix": "+"},
            {"label": "Projects Implemented", "value": Project.objects.count(), "suffix": ""},
        ]
    context = {
        "page_title": "Our Impact",
        "stats": stats,
        "stories": NewsArticle.objects.filter(status="published", category="story")[:3],
        "nav_pages": _published_pages().filter(show_in_nav=True).order_by("nav_order"),
    }
    return render(request, "website/impact.html", context)


def public_programs(request):
    from apps.programs.models import Program

    return render(
        request,
        "website/programs.html",
        {"programs": Program.objects.filter(status="active"), "nav_pages": _published_pages().filter(show_in_nav=True).order_by("nav_order")},
    )


def partners_public(request):
    from apps.partners.models import Partner

    return render(
        request,
        "website/partners.html",
        {"partners": Partner.objects.filter(show_on_website=True), "nav_pages": _published_pages().filter(show_in_nav=True).order_by("nav_order")},
    )


def leadership(request):
    from apps.cms.models import TeamMember

    members = TeamMember.objects.all()
    return render(
        request,
        "website/leadership.html",
        {
            "leaders": members.filter(category="leadership"),
            "board": members.filter(category="board"),
            "management": members.filter(category="management"),
            "nav_pages": _published_pages().filter(show_in_nav=True).order_by("nav_order"),
        },
    )


def donate(request):
    """Dedicated donation page: pledge form + giving-option cards.

    GHDI records the pledge as a ``DonationIntent`` for follow-up by the
    partnerships team; no payment credentials are ever collected here.
    """
    from apps.cms.models import DonationIntent

    from .forms import DonationForm

    form = DonationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        intent = form.save()
        messages.success(
            request,
            f"Thank you, {intent.name}! Your {intent.get_kind_display().lower()} "
            "pledge has been recorded — our partnerships team will contact you shortly.",
        )
        return redirect("website:donate")
    return render(
        request,
        "website/donate.html",
        {"form": form, "nav_pages": _published_pages().filter(show_in_nav=True).order_by("nav_order")},
    )


def careers(request):
    from apps.hr.models import Vacancy

    vacancies = Vacancy.objects.filter(status="open", is_public=True).order_by("-created_at")
    return render(request, "website/careers.html", {"vacancies": vacancies, "nav_pages": _published_pages().filter(show_in_nav=True).order_by("nav_order")})


def contact(request):
    form = ContactForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Thank you for reaching out. Our team will respond shortly.")
        return redirect("website:contact")
    return render(request, "website/contact.html", {"form": form, "nav_pages": _published_pages().filter(show_in_nav=True).order_by("nav_order")})


from django.conf import settings
from django.http import JsonResponse


def manifest(request):
    """PWA Web App Manifest."""
    org_name = settings.GHDI_ORG_NAME
    data = {
        "name": f"{org_name} Information System",
        "short_name": "GHDI MIS",
        "description": "Management Information System for the Garkuwa Humanitarian and Development Initiative",
        "start_url": "/app/",
        "scope": "/",
        "display": "standalone",
        "background_color": "#f8fafc",
        "theme_color": "#0f766e",
        "orientation": "portrait-primary",
        "icons": [
            {
                "src": "/static/img/icon-192.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any maskable",
            },
            {
                "src": "/static/img/icon-512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any maskable",
            },
        ],
    }
    return JsonResponse(data)


def service_worker(request):
    """PWA service worker: network-first for static assets & navigations,
    cache fallback for offline. Keeps returning visitors on fresh assets."""
    sw = (
        "const CACHE = 'ghdi-shell-v2';\n"
        "const CORE = ['/app/', '/static/js/app.js', '/static/css/ghdi.css', '/offline/'];\n"
        "self.addEventListener('install', e => {\n"
        "  e.waitUntil(caches.open(CACHE).then(c => Promise.all(CORE.map(u => c.add(u).catch(() => null)))).then(() => self.skipWaiting()));\n"
        "});\n"
        "self.addEventListener('activate', e => {\n"
        "  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));\n"
        "});\n"
        "async function networkFirst(request) {\n"
        "  const cache = await caches.open(CACHE);\n"
        "  try {\n"
        "    const res = await fetch(request);\n"
        "    if (res && res.ok) cache.put(request, res.clone());\n"
        "    return res;\n"
        "  } catch (err) {\n"
        "    const cached = await cache.match(request);\n"
        "    if (cached) return cached;\n"
        "    if (request.mode === 'navigate') {\n"
        "      const offline = await caches.match('/offline/');\n"
        "      if (offline) return offline;\n"
        "    }\n"
        "    throw err;\n"
        "  }\n"
        "}\n"
        "self.addEventListener('fetch', e => {\n"
        "  const url = new URL(e.request.url);\n"
        "  if (e.request.method !== 'GET' || url.origin !== location.origin) return;\n"
        "  if (url.pathname.startsWith('/media/')) return;\n"
        "  if (url.pathname.startsWith('/static/')) {\n"
        "    e.respondWith(networkFirst(e.request));\n"
        "    return;\n"
        "  }\n"
        "  if (e.request.mode === 'navigate') {\n"
        "    e.respondWith(networkFirst(e.request));\n"
        "  }\n"
        "});\n"
    )
    response = HttpResponse(sw, content_type="application/javascript")
    response["Service-Worker-Allowed"] = "/"
    response["Cache-Control"] = "no-cache"
    return response


def offline_page(request):
    """Graceful offline placeholder page."""
    return render(request, "pwa/offline.html", {"page_title": "You are offline"})


def robots_txt(request):
    """robots.txt allowing public pages, disallowing the internal app."""
    body = "User-agent: *\nAllow: /\nDisallow: /app/\nDisallow: /admin/\n"
    return HttpResponse(body, content_type="text/plain")


# MARKER_WEBSITE_PWA
