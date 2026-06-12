# Dashboard staff

Ogni progetto generato include una dashboard amministrativa su `/dashboard/`
(staff-only, login condiviso con l'admin Django).

## Stack

- **Tailwind 4 + htmx + Alpine** — sorgenti in `frontend/`, build con
  `npm run dashboard:build` (output committato in `static/dashboard/`)
- **CRUD generico** nei mixin di `apps/dashboard/mixins.py`: tabelle
  django-tables2, filtri django-filter, azioni bulk con select-across,
  export xlsx, form crispy-tailwind (`DashboardFormHelper`)
- **Storico modifiche** in `apps/history` (ObjectHistory + dirtyfields)
- Sezione di esempio: **Utenti** (`apps/dashboard/user/`)

## Personalizzazione

- **Colori del brand**: `frontend/shared/tokens.css` (i nomi dei token sono
  usati dai template: cambiare i valori, non i nomi)
- **Menu**: `apps/dashboard/sidebar_menu.py`
- **Logo/favicon**: aggiungere gli asset in `static/images/` e i relativi
  link in `templates/dashboard/base.html` e `sidebar.html`

## Aggiungere una sezione

Copiare il pattern di `apps/dashboard/user/`:

1. `forms.py` — FilterSet + FormHelper (estende `DashboardFormHelper`) + ModelForm
   (estende `CreateUpdateFormMixin`, layout a `Card`)
2. `tables.py` — Table (con `TableMultiSelectMixin` per le azioni bulk) + Table di export
3. `views.py` — List/Update/Delete sui mixin (`ListViewMixin`,
   `CreateUpdateMixin`, `DeleteMixin`, `SuperuserPermissionMixin`)
4. `urls.py` + include in `apps/dashboard/urls.py` + voce in `sidebar_menu.py`
5. test in `tests/dashboard/`

## Regole

- Le **eliminazioni avvengono solo via POST** (il dialog di conferma usa il
  form `#confirm-form` con CSRF); il GET su una delete view risponde 405
- Gli **endpoint htmx ritornano sempre frammenti**, mai pagine intere
- In sviluppo: `npm run dashboard:watch` (CSS) e `npm run dashboard:watch:js` (JS)
