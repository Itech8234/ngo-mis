"""GHDI link & navigation integrity checker.

Static checks (always run, no database required):

* every ``{% url 'name' %}`` referenced in a template must reverse
* every sidebar / bottom-nav / quick-action destination must reverse

Live check (``--live``, requires a database with users):

* for every user, every rendered navigation destination must respond with a
  2xx after following redirects -- catching dead links, 403s and 500s that a
  permission or URL change may have introduced.

Exits with status 1 when any check fails, so it can gate CI::

    python manage.py check_links
    python manage.py check_links --live
"""
import pathlib
import re

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.urls import NoReverseMatch, reverse

from apps.core.navigation import QUICK_ACTIONS, SIDEBAR_ITEMS

# Argument shapes tried when reversing a name found in a template, since the
# checker cannot know the real signature of each route.
REVERSE_CANDIDATES = (([], {}), ([1], {}), ([], {"pk": 1}), ([1, 2], {}))

URL_TAG = re.compile(r"""\{%\s*url\s+['"]([\w:.\-]+)['"]""")


def _reverses(name):
    """True when the URL name can be reversed with any common signature."""
    for args, kwargs in REVERSE_CANDIDATES:
        try:
            reverse(name, args=args, kwargs=kwargs)
            return True
        except NoReverseMatch:
            continue
    return False


class Command(BaseCommand):
    help = "Verify that template {% url %} tags and role navigation never dead-end."

    def add_arguments(self, parser):
        parser.add_argument(
            "--live",
            action="store_true",
            help="Also log in as every user and HTTP-check each navigation destination.",
        )

    def handle(self, *args, **options):
        failures = 0
        failures += self._check_templates()
        failures += self._check_navigation_registry()
        if options["live"]:
            failures += self._check_live_navigation()

        self.stdout.write("")
        if failures:
            raise CommandError(f"check_links found {failures} problem(s).")
        self.stdout.write(self.style.SUCCESS("check_links: all links resolve."))

    # -- static checks ----------------------------------------------------
    def _check_templates(self):
        """Reverse every ``{% url %}`` tag used across the template tree."""
        templates_root = pathlib.Path(settings.BASE_DIR) / "templates"
        usages = {}
        for path in templates_root.rglob("*.html"):
            text = path.read_text(encoding="utf-8", errors="ignore")
            for match in URL_TAG.finditer(text):
                usages.setdefault(match.group(1), set()).add(path.name)

        broken = sorted(name for name in usages if not _reverses(name))
        self.stdout.write(
            f"Template URL names: {len(usages)} used, {len(broken)} broken"
        )
        for name in broken:
            self.stdout.write(self.style.ERROR(f"  - {name} (in {sorted(usages[name])[:3]})"))
        return len(broken)

    def _check_navigation_registry(self):
        """Verify every sidebar and quick-action target reverses."""
        names = sorted({item[1] for item in SIDEBAR_ITEMS})
        names += sorted({item[1] for item in QUICK_ACTIONS})
        broken = [name for name in names if not _reverses(name)]
        self.stdout.write(
            f"Navigation targets: {len(names)} declared, {len(broken)} broken"
        )
        for name in broken:
            self.stdout.write(self.style.ERROR(f"  - {name}"))
        return len(broken)

    # -- live check -------------------------------------------------------
    def _check_live_navigation(self):
        """HTTP-check each rendered navigation entry for every user."""
        from django.contrib.auth import get_user_model
        from django.test import Client

        from apps.core.navigation import bottom_nav_for, quick_actions_for, sidebar_for

        users = list(get_user_model().objects.order_by("role", "pk"))
        if not users:
            self.stdout.write(self.style.WARNING("No users found; skipping --live check."))
            return 0

        failures = 0
        for user in users:
            client = Client(SERVER_NAME="localhost")
            client.force_login(user)
            entries = (
                [("sidebar", i["label"], i["url"]) for i in sidebar_for(user)]
                + [("bottom", i["label"], i["url"]) for i in bottom_nav_for(user)]
                + [("quick", i["label"], i["url"]) for i in quick_actions_for(user)]
            )
            bad = []
            for kind, label, url in entries:
                status = client.get(url, follow=True).status_code
                if status != 200:
                    bad.append((kind, label, url, status))
                    failures += 1
            marker = self.style.SUCCESS("ok") if not bad else self.style.ERROR(f"{len(bad)} broken")
            self.stdout.write(f"  [{user.role:8}] {len(entries):2} links -> {marker}")
            for kind, label, url, status in bad:
                self.stdout.write(self.style.ERROR(f"      - {kind:6} {label:22} {url} -> {status}"))
        return failures
