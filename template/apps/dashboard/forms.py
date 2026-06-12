from crispy_forms.helper import FormHelper


class DashboardFormHelper(FormHelper):
    """FormHelper base della dashboard: template pack Tailwind, niente <form> tag
    (il tag lo mette il template, con csrf e bottoni)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.template_pack = "tailwind"
        self.form_tag = False
        self.include_media = False
        self.attrs = {"novalidate": ""}
