"""Endpoint JSON generico per gli autocomplete Alpine della dashboard.

Le sottoclassi definiscono `model` + `search_fields` (lookup tipo
`name__icontains`); l'endpoint ritorna una lista `[{"id", "text"}]` filtrata
sul parametro `?q=`. Protetto agli staff via SuperuserPermissionMixin.

Override `extra_data(obj)` per arricchire ogni voce (es. `edit_url`, badge):
mantieni la stessa forma usata da `AutocompleteWidget` cosi' le voci scelte al
volo e quelle gia' salvate si comportano allo stesso modo.
"""

from __future__ import annotations

from django.db import models
from django.db.models import Q
from django.http import JsonResponse
from django.views import View

from apps.dashboard.mixins import SuperuserPermissionMixin


class AutocompleteView(SuperuserPermissionMixin, View):
    model: type[models.Model] | None = None
    search_fields: list[str] = []
    limit = 20

    def get_queryset(self):
        assert self.model is not None
        return self.model._default_manager.all()

    def label(self, obj) -> str:
        return str(obj)

    def extra_data(self, obj) -> dict:  # noqa: ARG002
        """Dati aggiuntivi per ogni voce (oltre a id/text). Override nelle sottoclassi."""
        return {}

    def get(self, request, *args, **kwargs):  # noqa: ARG002
        term = request.GET.get("q", "").strip()
        qs = self.get_queryset()
        if term:
            condition = Q()
            for field in self.search_fields:
                condition |= Q(**{field: term})
            qs = qs.filter(condition)
        results = [
            {"id": obj.pk, "text": self.label(obj), **self.extra_data(obj)}
            for obj in qs[: self.limit]
        ]
        return JsonResponse(results, safe=False)
