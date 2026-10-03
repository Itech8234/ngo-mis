"""CMS forms."""
from django import forms

from .models import CarouselSlide, Event, ImpactStat, MediaItem, NewsArticle, Page, PageSection, TeamMember


class PageForm(forms.ModelForm):
    class Meta:
        model = Page
        fields = [
            "title", "slug", "page_type", "featured_image", "summary", "content", "status",
            "publish_at", "author", "is_featured", "show_in_nav", "nav_order",
            "seo_title", "seo_description", "seo_keywords",
        ]
        widgets = {
            "publish_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "summary": forms.Textarea(attrs={"rows": 3}),
            "content": forms.Textarea(attrs={"rows": 10}),
        }


class PageSectionForm(forms.ModelForm):
    class Meta:
        model = PageSection
        fields = ["heading", "body", "image", "sort_order"]
        widgets = {
            "heading": forms.TextInput(attrs={"class": "form-input"}),
            "body": forms.Textarea(attrs={"rows": 4, "class": "form-input"}),
            "image": forms.ClearableFileInput(attrs={"class": "form-input"}),
            "sort_order": forms.NumberInput(attrs={"class": "form-input"}),
        }


class NewsArticleForm(forms.ModelForm):
    class Meta:
        model = NewsArticle
        fields = [
            "title", "slug", "category", "featured_image", "video_url", "video_caption",
            "summary", "content",
            "author", "publish_at", "tags", "status", "is_featured",
            "seo_title", "seo_description",
        ]
        widgets = {
            "content": forms.Textarea(attrs={"rows": 8}),
            "summary": forms.Textarea(attrs={"rows": 3}),
            "publish_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "video_url": forms.URLInput(attrs={"placeholder": "https://www.youtube.com/watch?v=… or https://vimeo.com/…"}),
        }


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ["name", "slug", "description", "date", "start_time", "end_time", "venue", "city", "registration_link", "image", "organizer", "status", "is_featured"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "date": forms.DateInput(attrs={"type": "date"}),
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
        }


class MediaItemForm(forms.ModelForm):
    class Meta:
        model = MediaItem
        fields = ["title", "file", "media_type", "category", "tags", "alt_text", "description"]


class ImpactStatForm(forms.ModelForm):
    class Meta:
        model = ImpactStat
        fields = ["label", "value", "suffix", "icon", "order", "is_active"]


class TeamMemberForm(forms.ModelForm):
    class Meta:
        model = TeamMember
        fields = ["name", "role", "category", "bio", "photo", "email", "order"]
        widgets = {"bio": forms.Textarea(attrs={"rows": 3})}


class CarouselSlideForm(forms.ModelForm):
    class Meta:
        model = CarouselSlide
        fields = [
            "eyebrow", "title", "title_highlight", "subtitle", "image", "image_alt",
            "cta_label", "cta_url", "secondary_label", "secondary_url", "order", "is_active",
        ]
        widgets = {"subtitle": forms.Textarea(attrs={"rows": 3})}

    def clean_cta_url(self):
        return self._clean_safe_url("cta_url")

    def clean_secondary_url(self):
        return self._clean_safe_url("secondary_url")

    def _clean_safe_url(self, field_name):
        value = self.cleaned_data.get(field_name, "").strip()
        if value and not (value.startswith("/") and not value.startswith("//") or value.startswith("https://")):
            raise forms.ValidationError("Enter an internal path beginning with / or a secure HTTPS URL.")
        return value
