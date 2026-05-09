from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Profile


class BootstrapMixin:
    """
    Centralizes Bootstrap widget styling without repeating boilerplate in templates.
    """

    def _bootstrap(self):
        for name, field in self.fields.items():
            widget = field.widget
            css = widget.attrs.get("class", "")
            if isinstance(widget, (forms.TextInput, forms.EmailInput, forms.NumberInput, forms.PasswordInput)):
                widget.attrs["class"] = (css + " form-control").strip()
            elif isinstance(widget, forms.Textarea):
                widget.attrs["class"] = (css + " form-control").strip()
                widget.attrs.setdefault("rows", 4)
            elif isinstance(widget, forms.Select):
                widget.attrs["class"] = (css + " form-select").strip()
            elif isinstance(widget, forms.ClearableFileInput):
                widget.attrs["class"] = (css + " form-control").strip()


class SignupForm(UserCreationForm, BootstrapMixin):
    class Meta:
        model = User
        fields = ("username", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._bootstrap()


class UserUpdateForm(forms.ModelForm, BootstrapMixin):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._bootstrap()


class ProfileForm(forms.ModelForm, BootstrapMixin):
    class Meta:
        model = Profile
        fields = ("photo", "bio", "phone")
        widgets = {
            "bio": forms.Textarea(attrs={"placeholder": "Tell recruiters a bit about you…"}),
            "phone": forms.TextInput(attrs={"placeholder": "+91 …"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._bootstrap()

