from crispy_forms.bootstrap import Tab
from crispy_forms.layout import Div, LayoutObject
from crispy_forms.utils import TEMPLATE_PACK, flatatt
from django.template.loader import render_to_string
from slugify import slugify


class Card(Div):
    template = "crispy_layout/card.html"

    def __init__(self, *fields, title=None, subtitle=None, css_id=None, css_class=None, template=None, **kwargs):
        super().__init__(*fields, css_id=css_id, css_class=css_class, template=template, **kwargs)
        self.title = title
        self.subtitle = subtitle


class Image(LayoutObject):
    template = "crispy_layout/image.html"
    css_class = None

    def __init__(self, *fields, css_id=None, css_class=None, template=None, **kwargs):
        self.fields = list(fields)
        if self.css_class and css_class:
            self.css_class += f" {css_class}"
        elif css_class:
            self.css_class = css_class

        self.css_id = css_id
        self.template = template or self.template
        self.flat_attrs = flatatt(kwargs)

    def render(self, form, context, template_pack=TEMPLATE_PACK, **kwargs):
        fields = self.get_rendered_fields(form, context, template_pack, **kwargs)

        cover_instance = None
        if form.instance:
            cover_instance = getattr(form.instance, self.fields[0])

        template = self.get_template_name(template_pack)
        return render_to_string(template, {
            "cover_instance": cover_instance,
            "image": self,
            "image_field": fields,
            "form": form
        })


class InlineTab(Tab):
    def render(self, form, context, template_pack=TEMPLATE_PACK, **kwargs):  # noqa: ARG002
        # I had to redefine the original TAB to pass the forloop counter to all tabs
        self.css_id = slugify(f"{self.name}", allow_unicode=True) + f"_{context['forloop'].counter}"
        return super().render(form, context, template_pack)
