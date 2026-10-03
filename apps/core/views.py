"""Core views: global search, organisation & system settings, activity feed helpers."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import redirect, render

from .forms import OrganizationSettingForm, SystemSettingForm
from .models import OrganizationSetting, SystemSetting
from .search import global_search


def page_not_found(request, exception=None):
    """Project-wide branded 404 handler for production and non-debug requests."""
    response = render(
        request,
        "errors/404.html",
        {
            "title": "Page not found",
            "message": "The page you are looking for does not exist or may have been moved.",
        },
        status=404,
    )
    response["X-GHDI-Not-Found"] = "1"
    return response


@login_required
def search_view(request):
    query = request.GET.get("q", "")
    results = global_search(query, request.user)
    return render(
        request,
        "core/search_results.html",
        {"query": query, "results": results, "result_count": len(results)},
    )


@login_required
def search_suggest(request):
    """Compact suggestion list for the topbar search."""
    query = request.GET.get("q", "")
    results = global_search(query, request.user, limit_per_type=3)
    return render(request, "core/_search_suggest.html", {"query": query, "results": results[:8]})


@login_required
@permission_required("core.change_organizationsetting", raise_exception=True)
def settings_org(request):
    org = OrganizationSetting.load()
    form = OrganizationSettingForm(request.POST or None, request.FILES or None, instance=org)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Organization settings saved.")
        return redirect("core:settings_org")
    return render(request, "core/settings_org.html", {"form": form, "org": org})


@login_required
@permission_required("core.change_organizationsetting", raise_exception=True)
def settings_system(request):
    if request.method == "POST":
        for key, _value in SystemSetting.objects.all().values_list("key", "value"):
            if key in request.POST:
                SystemSetting.set(key, request.POST.get(key, ""))
        messages.success(request, "System settings saved.")
        return redirect("core:settings_system")
    return render(request, "core/settings_system.html", {"settings_list": SystemSetting.objects.all()})


@login_required
def settings_index(request):
    if not request.user.has_perm("core.change_organizationsetting"):
        return redirect("dashboard:index")
    return redirect("core:settings_org")
