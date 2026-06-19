"""Widget di autocomplete (Alpine + endpoint JSON), tema Tailwind della dashboard.

`AutocompleteWidget` -> selezione singola (FK), look "select clearable".
`MultiAutocompleteWidget` -> selezione multipla a "chip" (M2M / multiple).

I label delle voci gia' selezionate si ricavano dal queryset del campo
(`self.choices.queryset`), cosi' NON renderizziamo tutte le opzioni come farebbe
un <select> normale: solo quelle selezionate.

Uso tipico::

    class FooAutocompleteView(AutocompleteView):
        model = Foo
        search_fields = ["name__icontains"]

    # forms.py
    widgets = {
        "foo": AutocompleteWidget(
            search_url="dashboard:foo_autocomplete",
            placeholder="Cerca un foo…",
            edit_url_name="dashboard:foo_edit",  # opzionale: voce cliccabile
        ),
    }
"""

from __future__ import annotations

import json
from typing import cast

from django import forms
from django.urls import reverse
from django.utils.safestring import mark_safe


class _AutocompleteMixin:
    def __init__(
        self,
        *args,
        search_url,
        search_url_kwargs=None,
        label_from_instance=None,
        placeholder="",
        edit_url_name=None,
        item_extra=None,
        **kwargs,
    ):
        self.search_url = search_url  # nome url da risolvere con reverse()
        self.search_url_kwargs = search_url_kwargs  # es. {"pk": ...} per endpoint scoped
        self.label_from_instance = label_from_instance or str
        self.placeholder = placeholder
        # `edit_url_name`: rende la voce selezionata un link all'edit dell'oggetto.
        # `item_extra(obj) -> dict`: dati extra per la voce (es. badge/metadati).
        # Devono produrre la stessa forma dell'endpoint JSON, cosi' le voci gia'
        # salvate e quelle scelte al volo si comportano allo stesso modo.
        self.edit_url_name = edit_url_name
        self.item_extra = item_extra
        super().__init__(*args, **kwargs)

    def _selected_items(self, value):
        raw = value if isinstance(value, (list, tuple)) else [value]
        values = [str(v) for v in raw if v not in (None, "")]
        queryset = getattr(getattr(self, "choices", None), "queryset", None)
        if not values or queryset is None:
            return []
        by_pk = {str(obj.pk): obj for obj in queryset.filter(pk__in=values)}
        items = []
        for v in values:
            obj = by_pk.get(v)
            if obj is None:
                continue
            item = {"id": obj.pk, "text": self.label_from_instance(obj)}
            if self.edit_url_name:
                item["edit_url"] = reverse(self.edit_url_name, kwargs={"pk": obj.pk})
            if self.item_extra:
                item.update(self.item_extra(obj))
            items.append(item)
        return items

    def get_context(self, name, value, attrs):
        # Bypassa la build degli optgroups di Select: renderizziamo solo i selezionati.
        context = forms.Widget.get_context(cast(forms.Widget, self), name, value, attrs)
        items = self._selected_items(value)
        context["widget"]["selected_items"] = items
        context["widget"]["selected_json"] = mark_safe(json.dumps(items))
        context["widget"]["search_url"] = reverse(
            self.search_url, kwargs=self.search_url_kwargs or None
        )
        context["widget"]["placeholder"] = self.placeholder
        return context


class AutocompleteWidget(_AutocompleteMixin, forms.Select):
    template_name = "dashboard/widgets/autocomplete_single.html"


class MultiAutocompleteWidget(_AutocompleteMixin, forms.SelectMultiple):
    template_name = "dashboard/widgets/autocomplete_multi.html"
