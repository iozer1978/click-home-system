from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password

# תרגום הודעות אימות סיסמה לעברית
PASSWORD_ERROR_MESSAGES = {
    'password_too_short': 'הסיסמה חייבת להכיל לפחות 8 תווים.',
    'password_too_common': 'הסיסמה נפוצה מדי.',
    'password_entirely_numeric': 'הסיסמה לא יכולה להכיל רק ספרות.',
    'password_too_similar': 'הסיסמה דומה מדי לפרטים האישיים.',
}


class ClientRegisterForm(UserCreationForm):
    username = forms.CharField(
        label="שם משתמש",
        max_length=150,
        required=True,
        help_text="נדרש. עד 150 תווים. אותיות, ספרות ו־@/./+/-/_ בלבד.",
        widget=forms.TextInput(attrs={'placeholder': 'בחר שם משתמש', 'autocomplete': 'username'}),
    )
    first_name = forms.CharField(
        label="שם פרטי",
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'השם הפרטי שלך'}),
    )
    last_name = forms.CharField(
        label="שם משפחה",
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'שם המשפחה'}),
    )
    email = forms.EmailField(
        label="אימייל",
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'example@email.com'}),
    )
    phone = forms.CharField(
        label="טלפון נייד",
        max_length=15,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': '050-0000000'}),
    )
    password1 = forms.CharField(
        label="סיסמה",
        strip=False,
        required=True,
        widget=forms.PasswordInput(attrs={'placeholder': 'בחר סיסמה', 'autocomplete': 'new-password'}),
        help_text="לפחות 8 תווים, לא רק ספרות, לא דומה מדי לפרטים האישיים.",
    )
    password2 = forms.CharField(
        label="אימות סיסמה",
        strip=False,
        required=True,
        widget=forms.PasswordInput(attrs={'placeholder': 'הזן שוב את הסיסמה', 'autocomplete': 'new-password'}),
        help_text="הזן את אותה סיסמה שוב לאימות.",
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone', 'password1', 'password2']

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        try:
            validate_password(password, self.instance)
        except ValidationError as e:
            he_messages = []
            for err in e.messages:
                err_lower = err.lower()
                if 'short' in err_lower or '8' in err_lower:
                    he_messages.append(PASSWORD_ERROR_MESSAGES['password_too_short'])
                elif 'common' in err_lower:
                    he_messages.append(PASSWORD_ERROR_MESSAGES['password_too_common'])
                elif 'numeric' in err_lower:
                    he_messages.append(PASSWORD_ERROR_MESSAGES['password_entirely_numeric'])
                elif 'similar' in err_lower:
                    he_messages.append(PASSWORD_ERROR_MESSAGES['password_too_similar'])
                else:
                    he_messages.append(err)
            raise ValidationError(he_messages[0] if len(he_messages) == 1 else he_messages)
        return password

    def save(self, commit=True):
        # שמירת המשתמש הרגיל
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        
        if commit:
            user.save()
            # שמירת הטלפון בתוך הפרופיל
            user.profile.phone = self.cleaned_data['phone']
            user.profile.save()
        return user