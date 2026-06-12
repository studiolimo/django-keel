from typing import Any

from rest_framework import serializers
from rest_framework.fields import empty

from apps.services.models import ServicePresetImage, ServiceTypology
from apps.users.models import SpecialistTypology


class CollectAllErrorsMixin:
    """
    Serializer mixin that collects ALL validation errors — field-level and cross-field — in
    a single response, instead of DRF's default two-phase behavior where validate() is skipped
    when field-level errors exist.

    Works because fields with required=False or a default are always present in attrs even when
    other fields fail, so validate() has enough data to run its cross-field checks.

    Usage:
        class MySerializer(CollectAllErrorsMixin, serializers.ModelSerializer):
            def validate(self, attrs):
                errors = {}
                # collect all cross-field errors into `errors` dict, then:
                if errors:
                    raise serializers.ValidationError(errors)
                return attrs
    """

    def run_validation(self, data=empty):
        field_errors: dict[str, Any] = {}
        attrs: dict[str, Any] = {}

        # 1. Chiamo to_internal_value() e cattura gli errori field-level
        # senza sollevarli
        try:
            attrs = self.to_internal_value(data)  # type: ignore[attr-defined]
        except serializers.ValidationError as exc:
            detail = exc.detail
            field_errors = detail if isinstance(detail, dict) else {"non_field_errors": detail}

        # 2. Chiamo comunque validate() con gli attrs parziali (i campi
        #   required=False/default sono sempre presenti anche se altri campi
        #   falliscono)
        cross_errors: dict[str, Any] = {}
        try:
            self.validate(attrs)  # type: ignore[attr-defined]
        except serializers.ValidationError as exc:
            detail = exc.detail
            cross_errors = detail if isinstance(detail, dict) else {"non_field_errors": detail}

        #   3. Raccoglie entrambi i set di errori e li solleva insieme in
        #   un'unica risposta
        all_errors = {**field_errors, **cross_errors}
        if all_errors:
            raise serializers.ValidationError(all_errors)

        return attrs
