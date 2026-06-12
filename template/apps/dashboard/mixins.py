import json
import logging

import django_tables2 as tables
from crispy_forms.layout import Layout
from dirtyfields import DirtyFieldsMixin
from django import forms
from django.contrib import messages
from django.contrib.admin.utils import model_ngettext
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.contrib.contenttypes.fields import GenericRelation
from django.core import serializers
from django.core.exceptions import ImproperlyConfigured
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.http import (
    Http404,
    HttpResponse,
    HttpResponseBase,
    HttpResponseNotAllowed,
    HttpResponseRedirect,
)
from django.utils.http import url_has_allowed_host_and_scheme
from django.template.response import TemplateResponse
from django.urls import reverse, reverse_lazy
from django.utils.encoding import force_str
from django.views.generic import DeleteView, UpdateView
from django_addanother.views import CreatePopupMixin
from django_filters.views import FilterView
from django_tables2 import SingleTableMixin
from django_tables2.export import ExportMixin
from extra_views import UpdateWithInlinesView

from apps.dashboard.crispy_layout import Card
from apps.dashboard.forms import DashboardFormHelper
from apps.history.models import ObjectHistory

log = logging.getLogger("ri7ette")


class HistoryMixin(DirtyFieldsMixin, models.Model):
    history = GenericRelation(ObjectHistory)

    class Meta:
        abstract = True

    def ordered_history(self):
        return self.history.order_by('-creation_date')


class DashboardPermissionMixin(LoginRequiredMixin):
    """Accesso riservato allo staff. Login condiviso con l'admin Django."""

    login_url = reverse_lazy("admin:login")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.is_staff:
            # In Django 5.x handle_no_permission() per utenti autenticati solleva PermissionDenied (403).
            # Per la dashboard vogliamo invece un redirect al login admin, quindi lo facciamo esplicitamente.
            return redirect_to_login(request.get_full_path(), str(self.login_url))
        return super().dispatch(request, *args, **kwargs)


class SuperuserPermissionMixin(LoginRequiredMixin):
    login_url = reverse_lazy("admin:login")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.is_superuser:
            # Stesso motivo di DashboardPermissionMixin: redirect esplicito invece di PermissionDenied.
            return redirect_to_login(request.get_full_path(), str(self.login_url))
        return super().dispatch(request, *args, **kwargs)


# to protect the select2 autocomplete url
class SuperuserSelect2WidgetMixin:
    def __init__(self, *args, **kwargs):
        kwargs['data_view'] = 'dashboard:select2'
        super().__init__(*args, **kwargs)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["attrs"]["data-minimum-input-length"] = 0
        # context["widget"]["attrs"]["data-width"] = 200
        # context["widget"]["attrs"]["data-close-on-select"] = "false"
        return context


class ListViewMixin(SingleTableMixin, ExportMixin, FilterView):
    template_name = 'dashboard/ui/list.html'
    page_title = None
    export_trigger_param = "download"
    formhelper_class = None
    actions = []
    export_table_class = None
    # add_button = None
    buttons = []

    def post(self, request, *args, **kwargs):
        response = self.get(request, *args, **kwargs)
        action = request.POST.get('action')
        select_across = request.POST.get('select_across', '0')
        allowed_actions = {a["fn"] for a in self.get_actions()}
        if not action or action not in allowed_actions:
            return response
        action_function = getattr(self.__class__, action, None)
        if not action_function:
            return response

        pks = request.POST.getlist('selection')
        if select_across == '1':
            final_object_list = self.object_list
        else:
            final_object_list = self.object_list.filter(pk__in=pks)

        action_response = action_function(self, final_object_list)

        # Actions may return an HttpResponse-like object, which will be
        # used as the response from the POST. If not, we'll be a good
        # little HTTP citizen and redirect back to the changelist page.
        if isinstance(action_response, HttpResponseBase):
            return action_response
        return HttpResponseRedirect(request.get_full_path())

    def get_export_filename(self, export_format):
        return f"list_{self.object_list.model.__name__.lower()}.{export_format}"

    def get_export_table(self):
        return self.export_table_class or self.get_table_class()

    def create_export(self, export_format):
        """Override ExportMixin: usa la export_table_class dedicata sull'object_list filtrato."""
        return self._build_export(self.object_list, export_format)

    def _build_export(self, object_list, export_format, export_table_class=None):
        """Costruisce la risposta xlsx/csv da un queryset e una table class."""
        table_class = export_table_class or self.get_export_table()
        table = table_class(data=object_list, **self.get_table_kwargs())

        exporter = self.export_class(
            export_format=export_format,
            table=table,
            exclude_columns=self.exclude_columns,
            dataset_kwargs=self.get_dataset_kwargs(),
        )
        return exporter.response(filename=self.get_export_filename(export_format))

    def action_download_selected_rows(self, object_list):
        return self._build_export(object_list, "xlsx")

    def action_delete_objects(self, object_list):
        if self.request.POST.get("post"):
            object_list.delete()
            messages.success(self.request, f"{model_ngettext(object_list)} eliminati con successo")
            return None

        return self.get_action_confirmation_template(
            "dashboard/actions/delete_objects.html",
            object_list
        )

    def get_action_confirmation_template(self, template_name, object_list, extra_context=None):
        if extra_context is None:
            extra_context = {}
        context = {
                'object_list': object_list,
                'objects_name': model_ngettext(object_list),
                'action': self.request.POST.get('action'),
                'cancel_url': self.request.get_full_path(),
            }
        context.update(extra_context)
        return TemplateResponse(
            self.request,
            template_name,
            context
        )

    def get_filterset(self, filterset_class):
        kwargs = self.get_filterset_kwargs(filterset_class)
        filterset = filterset_class(**kwargs)
        filterset.form.helper = self.get_formhelper_class()()
        return filterset

    def get_formhelper_class(self):
        return self.formhelper_class or DashboardFormHelper

    def get_page_title(self):
        return self.page_title or f"{self.model._meta.verbose_name.title()} List"

    def get_actions(self):
        return self.actions

    def get_buttons(self):
        return self.buttons

    def get_context_data(self, **kwargs):
        self.object_list_not_paginated = self.object_list

        ctx = super().get_context_data(**kwargs)

        # add the request object to the table
        table = self.get_table(**self.get_table_kwargs())
        table.request = self.request
        ctx[self.get_context_table_name(table)] = table

        ctx['model_name'] = self.model._meta.verbose_name.title()
        ctx['page_title'] = self.get_page_title()
        ctx['actions'] = self.get_actions()
        ctx['buttons'] = self.get_buttons()
        # if hasattr(self, 'resource_class') or hasattr(self, 'get_resource_class'):
        #     ctx['add_download_button'] = True
        return ctx


class CreateUpdateFormMixin(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.user = None
        if 'user' in kwargs:
            self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.set_form_helper()

    def set_form_helper(self):
        self.helper = DashboardFormHelper(self)

        if hasattr(self, 'get_form_layout'):
            self.helper.layout = self.get_form_layout()
        else:
            self.helper.layout = Layout(
                Card(*self.fields)
            )


class CreateUpdateSimpleFormMixin(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_form_helper()

    def set_form_helper(self):
        self.helper = DashboardFormHelper(self)

        if hasattr(self, 'get_form_layout'):
            self.helper.layout = self.get_form_layout()
        else:
            self.helper.layout = Layout(
                Card(*self.fields)
            )


class CommonCreateUpdateMixin:
    success_create_message = None  # Default to None
    success_update_message = None  # Default to None
    back_button_url = None
    back_button_text = None
    edit_url_name = None
    delete_url_name = None
    template_name = 'dashboard/ui/create_update_form.html'
    page_title = None
    page_subtitle = None
    save_history = True
    actions_buttons_inline = True
    show_save_and_continue_button = True
    save_button_label = "Salva"

    def get_object(self, queryset=None):
        """
        Return the object the view is displaying.

        Require `self.queryset` and a `pk` or `slug` argument in the URLconf.
        Subclasses can override this to return any object.
        """
        self.creating = 'pk' not in self.kwargs

        if not hasattr(self.model, 'get_dirty_fields'):
            self.save_history = False

        if self.creating:
            return None  # success

        # Use a custom queryset if provided; this is required for subclasses
        # like DateDetailView
        if queryset is None:
            queryset = self.get_queryset()

        # Next, try looking up by primary key.
        pk = self.kwargs.get(self.pk_url_kwarg)
        slug = self.kwargs.get(self.slug_url_kwarg)
        if pk is not None:
            queryset = queryset.filter(pk=pk)

        # Next, try looking up by slug.
        if slug is not None and (pk is None or self.query_pk_and_slug):
            slug_field = self.get_slug_field()
            queryset = queryset.filter(**{slug_field: slug})

        # If none of those are defined, it's an error.
        if pk is None and slug is None:
            raise AttributeError(
                f"Generic detail view {self.__class__.__name__} must be called with either an object "
                "pk or a slug in the URLconf."
            )

        try:
            # Get the single item from the filtered queryset
            obj = queryset.get()
        except queryset.model.DoesNotExist as exc:
            raise Http404("No objects founds") from exc

        if hasattr(obj, 'can_be_edited') and not obj.can_be_edited(self.request.user):
            raise Http404(f"{obj.__class__.__name__} can't be edited")

        return obj

    def get_queryset(self):
        """
        Return the `QuerySet` that will be used to look up the object.

        This method is called by the default implementation of get_object() and
        may not be called if get_object() is overridden.
        """
        if self.queryset is None:
            if self.model:
                return self.model._default_manager.all()
            else:
                raise ImproperlyConfigured(
                    f"{self.__class__.__name__} is missing a QuerySet. Define "
                    f"{self.__class__.__name__}.model, {self.__class__.__name__}.queryset, or override "
                    f"{self.__class__.__name__}.get_queryset()."
                )
        return self.queryset.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = self.get_page_title()
        context['page_subtitle'] = self.get_page_subtitle()
        context['creating'] = self.creating
        if self.creating:
            context['success_url'] = None
            context['delete_button_url'] = None
        else:
            context['success_url'] = self.get_success_url()
            context['delete_button_url'] = self.get_delete_url()
        context['back_button_url'] = self.get_back_button_url()
        context['back_button_text'] = self.get_back_button_text()
        context['view_on_site_button'] = self.get_view_on_site_url()
        context['actions_buttons_inline'] = self.actions_buttons_inline
        context['show_save_and_continue_button'] = self.show_save_and_continue_button
        context['save_button_label'] = self.save_button_label
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def add_history(self, dirty_fields):
        if self.creating:
            history_message = f"{self.model._meta.verbose_name.title()} {self.object} created"
            ObjectHistory.add_history(self.object, self.request.user, history_message)
            return

        history_message = []
        for key, value in dirty_fields.items():
            field = self.model._meta.get_field(key)
            field_title = field.verbose_name.title()
            if field.choices:
                value_saved = force_str(dict(field.flatchoices).get(value['saved'], value['saved']), strings_only=True)
                value_current = force_str(dict(field.flatchoices).get(value['current'], value['current']),
                                           strings_only=True)
            else:
                value_saved = value['saved'] if not None else ''
                value_current = value['current'] if not None else ''

            history_message.append(f"Field <b>{field_title}</b> changed from {value_saved} to {value_current}")

        if history_message:
            ObjectHistory.add_history(self.object, self.request.user, "<br>".join(history_message))

    def get_form_valid_message(self, var_to_valid):
        """
        Validate that form_valid_message is set and is either a
        unicode or str object.
        """
        if var_to_valid is None:
            raise ImproperlyConfigured(
                f'{self.__class__.__name__}.success_create_message or {self.__class__.__name__}.success_update_message is not set. Define them'

            )
        return var_to_valid

    def get_success_create_message(self):
        verbose_name = self.model._meta.verbose_name.title()
        return self.success_create_message or f'{verbose_name} "{self.object}" creato con successo.'

    def get_success_update_message(self):
        verbose_name = self.model._meta.verbose_name.title()
        return self.success_update_message or f'{verbose_name} "{self.object}" aggiornato con successo.'

    def get_view_on_site_url(self):
        if self.object and self.object.pk and hasattr(self.object, 'get_absolute_url'):
            return self.object.get_absolute_url()
        return None

    def get_back_button_url(self):
        if not self.back_button_url and hasattr(self, 'success_url'):
            return self.success_url
        return self.back_button_url

    def get_back_button_text(self):
        return self.back_button_text or "Torna alla lista"

    def get_edit_url(self):
        if self.edit_url_name:
            return reverse(f"dashboard:{self.edit_url_name}", kwargs={'pk': self.object.pk})
        return None

    def get_delete_url(self):
        if self.delete_url_name:
            return reverse(f"dashboard:{self.delete_url_name}", kwargs={'pk': self.object.pk})
        return None

    def get_page_title(self):
        prefix = 'Modifica'
        if self.creating:
            prefix = 'Aggiungi'
        return self.page_title or f"{prefix} {self.model._meta.verbose_name.title()}"

    def get_page_subtitle(self):
        return self.page_subtitle

    def create_success_messages(self):
        if self.creating:
            messages.success(self.request, self.get_form_valid_message(self.get_success_create_message()))
        else:
            messages.success(self.request, self.get_form_valid_message(self.get_success_update_message()))

    def form_valid(self, form):
        if self.save_history:
            self.object = form.save(commit=False)
            dirty_fields = self.object.get_dirty_fields(verbose=True)
            try:
                self.object.save()
            except Exception as e:
                log.exception(f"[CreateUpdateMixin] self.object: {self.object}. Error during form save: {e}")
                error_messages = f"Qualcosa è andato storto. L'oggetto non è stato salvato. Errore: {e}"
                messages.error(self.request, error_messages)
                return self.form_invalid(form)
            self.add_history(dirty_fields)
            form.save_m2m()
        else:
            try:
                self.object = form.save()
            except Exception as e:
                log.exception(f"[CreateUpdateMixin] self.object: {self.object}. Error during form save: {e}")
                error_messages = f"Qualcosa è andato storto. L'oggetto non è stato salvato. Errore: {e}"
                messages.error(self.request, error_messages)
                return self.form_invalid(form)

        self.create_success_messages()
        if 'save_and_continue' in self.request.POST:
            get_params = self.request.GET.urlencode()

            edit_url = self.get_edit_url()
            if not edit_url:
                edit_url = self.request.META['PATH_INFO']

            if get_params:
                edit_url = edit_url + "?" + get_params
            return HttpResponseRedirect(edit_url)

        return HttpResponseRedirect(self.get_success_url())


class CreateUpdateMixin(CreatePopupMixin, CommonCreateUpdateMixin, UpdateView):
    pass


class CommonFormMixin(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = CommonFormSetHelper()
        self.helper.layout = Layout(
            Card(*self.fields)
        )


class CommonFormSetHelper(DashboardFormHelper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.render_required_fields = True


class InlineModelFormMixin(forms.ModelForm):
    def get_helper(self):
        helper = CommonFormSetHelper()
        if hasattr(self, 'get_form_layout'):
            helper.layout = self.get_form_layout()
        else:
            helper.template = 'tailwind/table_inline_formset.html'
            helper.layout = Layout(
                Card(*self.fields)
            )
        return helper


class CreateUpdateWithInlinesMixin(CommonCreateUpdateMixin, UpdateWithInlinesView):
    def forms_valid(self, form, inlines):
        """
        If the form and formsets are valid, save the associated models.
        """
        response = self.form_valid(form)
        for formset in inlines:
            formset.save()
        return response

    def construct_inlines(self):
        """
        Returns the inline formset instances
        """
        inline_formsets = []
        for inline_class in self.get_inlines():
            inline_instance = inline_class(
                self.model, self.request, self.object, self.kwargs, self
            )
            inline_formset = inline_instance.construct_formset()
            inline_formset.helper = inline_class.form_class().get_helper()
            inline_formset.header_title = inline_class.inline_header_title
            inline_formset.header_subtitle = None
            if hasattr(inline_class, 'inline_header_subtitle'):
                inline_formset.header_subtitle = inline_class.inline_header_subtitle
            inline_formsets.append(inline_formset)
        return inline_formsets


class DeleteMixin(DeleteView):
    """Eliminazione via POST con redirect. La conferma è il dialog client-side;
    il GET non elimina (405): protegge da link forgiati e prefetch del browser."""

    success_delete_message = None
    error_delete_message = None

    def get_success_delete_message(self):
        verbose_name = self.model._meta.verbose_name.title()
        return self.success_delete_message or f'{verbose_name} "{self.object}" eliminato con successo.'

    def get_error_delete_message(self, error_message):
        verbose_name = self.model._meta.verbose_name.title()
        return self.error_delete_message or (
            f'Impossibile eliminare {verbose_name} "{self.object}". Errore: {error_message}'
        )

    def get(self, request, *args, **kwargs):  # noqa: ARG002
        return HttpResponseNotAllowed(["POST"])

    def post(self, request, *args, **kwargs):  # noqa: ARG002
        self.object = self.get_object()

        if hasattr(self.object, "can_be_deleted") and not self.object.can_be_deleted(request.user):
            raise Http404(f"{self.object.__class__.__name__} can't be deleted")

        redirect_url = (
            request.POST.get("redirect_url")
            or request.META.get("HTTP_REFERER")
            or reverse("dashboard:index")
        )
        if not url_has_allowed_host_and_scheme(
            redirect_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            redirect_url = reverse("dashboard:index")

        try:
            self.object.delete()
        except Exception as e:
            messages.error(request, self.get_error_delete_message(e))
        else:
            messages.success(request, self.get_success_delete_message())

        return HttpResponseRedirect(redirect_url)


class TableMultiSelectMixin(tables.Table):
    # Colonna checkbox per la selezione righe (azioni bulk).
    # I gestori sono nel componente Alpine 'tableSelection' (frontend/dashboard/js).
    selection = tables.CheckBoxColumn(
        accessor="pk", orderable=False,
        exclude_from_export=True,
        attrs={
            "th__input": {"autocomplete": "off", "@change": "toggleAll($event.target.checked)"},
            "td__input": {"autocomplete": "off", "@change": "recount()"},
        },
    )


class IframeMixin:
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['IS_IFRAME'] = True
        return ctx


class JSONResponseMixin:
    """
    A mixin that allows you to easily serialize simple data such as a dict or
    Django models.
    """
    content_type = None
    json_dumps_kwargs = None
    json_encoder_class = DjangoJSONEncoder

    def get_content_type(self):
        if self.content_type is not None and not isinstance(self.content_type, str):
            raise ImproperlyConfigured(
                f'{self.__class__.__name__} is missing a content type. Define {self.__class__.__name__}.content_type, '
                f'or override {self.__class__.__name__}.get_content_type().')
        return self.content_type or "application/json"

    def get_json_dumps_kwargs(self):
        if self.json_dumps_kwargs is None:
            self.json_dumps_kwargs = {}
        self.json_dumps_kwargs.setdefault('ensure_ascii', False)
        return self.json_dumps_kwargs

    def render_json_response(self, context_dict, status=200):
        """
        Limited serialization for shipping plain data. Do not use for models
        or other complex or custom objects.
        """
        json_context = json.dumps(
            context_dict,
            cls=self.json_encoder_class,
            **self.get_json_dumps_kwargs()).encode('utf-8')
        return HttpResponse(json_context,
                            content_type=self.get_content_type(),
                            status=status)

    def render_json_object_response(self, objects, **kwargs):
        """
        Serializes objects using Django's builtin JSON serializer. Additional
        kwargs can be used the same way for django.core.serializers.serialize.
        """
        json_data = serializers.serialize("json", objects, **kwargs)
        return HttpResponse(json_data, content_type=self.get_content_type())
