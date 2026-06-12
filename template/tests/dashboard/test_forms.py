from django import forms

from apps.dashboard.forms import DashboardFormHelper


class _SampleForm(forms.Form):
    nome = forms.CharField()


def test_dashboard_form_helper_usa_template_pack_tailwind():
    helper = DashboardFormHelper(_SampleForm())
    assert helper.template_pack == "tailwind"
    assert helper.form_tag is False
    assert helper.include_media is False
    assert helper.attrs.get("novalidate") == ""
