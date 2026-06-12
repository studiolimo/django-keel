# Dashboard Tailwind nel template django-keel — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Portare la dashboard staff Tailwind (da ri7_backend, branch `feat/dashboard-tailwind`) nel template copier django-keel, con `{{ project_name }}`/`{{ project_slug }}` dove servono valori di progetto.

**Architecture:** Porting file-per-file dentro `template/`: i file Python e la maggior parte dei template HTML restano file normali; diventano `.jinja` solo i 4 template con il nome progetto e i file di configurazione già templati (package.json, pyproject, settings, urls, README). I delimitatori Django nei `.jinja` sono protetti con `{% raw %}`. Output di build non versionati: il README generato istruisce `npm install && npm run dashboard:build`.

**Tech Stack:** copier 9 (suffisso `.jinja`), Tailwind 4 CLI, esbuild, htmx 2, Alpine 3, django-tables2/filter/crispy-tailwind/extra-views/addanother/dirtyfields.

**Spec:** `docs/superpowers/specs/2026-06-12-dashboard-template-design.md`

**Sorgente:** `~/Lavoro/siti/ri7ette_project/ri7_backend` checked-out sul branch `feat/dashboard-tailwind` (NON cambiare branch a quel repo). D'ora in poi: `$RI7`.

**Vincolo critico:** il repo keel ha modifiche WIP non committate dell'autore (copier.yml e altri). NON committarle mai: ogni `git add` è per path espliciti della dashboard. NON modificare copier.yml.

---

## File Structure (tutto sotto `django-keel/template/` salvo dove indicato)

```
apps/dashboard/                          # COPIA da $RI7 + adattamenti (logger, no select2, user senza membership)
apps/history/                            # COPIA da $RI7 (inclusa migrazione)
templates/dashboard/**                   # COPIA; 4 file diventano .jinja
templates/django_tables2/tailwind.html   # COPIA
templates/crispy_layout/{card,image}.html
templates/tailwind/table_inline_formset.html
frontend/shared/tokens.css               # NUOVO contenuto (palette neutra)
frontend/dashboard/{styles.css,js/dashboard.js}   # COPIA
frontend/site/{styles.css,js/site.js}    # COPIA
tests/dashboard/                         # COPIA + adattamenti (no membership)
package.json.jinja                       # MODIFICA (script + deps)
pyproject.toml.jinja                     # MODIFICA (deps)
config/settings/base.py.jinja            # MODIFICA (apps + crispy + tables2)
config/settings/test.py.jinja            # MODIFICA (storage statici test)
config/urls.py.jinja                     # MODIFICA (route dashboard)
README.md.jinja                          # MODIFICA (step npm post-gen)
docs/features/dashboard.md               # NUOVO (repo keel, non template)
mkdocs.yml                               # MODIFICA (repo keel)
CHANGELOG.md                             # MODIFICA (repo keel)
tests/test_dashboard_generation.py       # NUOVO (repo keel, test template-level)
```

---

### Task 1: Branch di lavoro e copia grezza dei file

**Files:** branch `feat/dashboard-template` in django-keel; copia di apps/templates/frontend/tests.

- [ ] **Step 1: Branch (senza toccare il WIP)**

```bash
cd /Users/marcominutoli/Lavoro/django-packages/django-keel
git checkout -b feat/dashboard-template
git status --short | head   # il WIP dell'autore resta unstaged: NON committarlo mai
```

- [ ] **Step 2: Copia i file Python e i template da ri7**

```bash
RI7=/Users/marcominutoli/Lavoro/siti/ri7ette_project/ri7_backend
T=/Users/marcominutoli/Lavoro/django-packages/django-keel/template

# verifica che ri7 sia sul branch giusto (NON cambiarglielo)
git -C "$RI7" rev-parse --abbrev-ref HEAD   # atteso: feat/dashboard-tailwind

cp -R "$RI7/apps/dashboard" "$T/apps/dashboard"
cp -R "$RI7/apps/history" "$T/apps/history"
mkdir -p "$T/templates"
cp -R "$RI7/templates/dashboard" "$T/templates/dashboard"
cp -R "$RI7/templates/django_tables2" "$T/templates/django_tables2"
cp -R "$RI7/templates/crispy_layout" "$T/templates/crispy_layout"
cp -R "$RI7/templates/tailwind" "$T/templates/tailwind"
mkdir -p "$T/frontend"
cp -R "$RI7/frontend/shared" "$T/frontend/shared"
cp -R "$RI7/frontend/dashboard" "$T/frontend/dashboard"
cp -R "$RI7/frontend/site" "$T/frontend/site"
cp -R "$RI7/tests/dashboard" "$T/tests/dashboard"
find "$T/apps/dashboard" -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null
find "$T" -name "*.pyc" -delete
```

- [ ] **Step 3: Inventario dei riferimenti da neutralizzare**

```bash
grep -rn "ri7\|ri7ette\|Vivace\|narae\|webpack" "$T/apps/dashboard" "$T/apps/history" "$T/templates/dashboard" "$T/templates/django_tables2" "$T/templates/crispy_layout" "$T/templates/tailwind" "$T/frontend" "$T/tests/dashboard"
```

Annota l'output: ogni occorrenza viene risolta nei Task 2-4. Attesi almeno: logger "ri7ette" in mixins.py, titolo/footer in base.html, sidebar logo, testo benvenuto index, commento palette in tokens.css.

- [ ] **Step 4: Commit della copia grezza** (così i task successivi hanno diff leggibili)

```bash
cd /Users/marcominutoli/Lavoro/django-packages/django-keel
git add template/apps/dashboard template/apps/history template/templates/dashboard \
        template/templates/django_tables2 template/templates/crispy_layout \
        template/templates/tailwind template/frontend template/tests/dashboard
git commit -m "feat(dashboard): copia grezza della dashboard Tailwind da ri7_backend"
```

---

### Task 2: Adattamenti ai file Python

**Files:**
- Modify: `template/apps/dashboard/mixins.py`, `template/apps/dashboard/index/views.py`, `template/apps/dashboard/user/{forms,tables,views}.py`, `template/tests/dashboard/test_user_views.py`

- [ ] **Step 1: Logger generico** — in `template/apps/dashboard/mixins.py` sostituisci:

```python
log = logging.getLogger("ri7ette")
```

con:

```python
log = logging.getLogger(__name__)
```

- [ ] **Step 2: Via django-select2** (non è una dipendenza di keel) — in `template/apps/dashboard/index/views.py` elimina l'import `from django_select2.views import AutoResponseView` e la classe `SuperuserSelect2View`. Il file resta:

```python
from django.views.generic import TemplateView

from apps.dashboard.mixins import SuperuserPermissionMixin


class DashboardIndexView(SuperuserPermissionMixin, TemplateView):
    template_name = "dashboard/index/index.html"
```

Verifica con grep che nessun altro file portato citi select2: `grep -rn "select2" template/apps/dashboard template/templates/dashboard` — se compare altrove (es. mixins `SuperuserSelect2WidgetMixin`), elimina anche quello e segnala nel report.

- [ ] **Step 3: Sezione Utenti senza membership** — il `User` di keel non ha `membership`/`force_premium`.

In `template/apps/dashboard/user/forms.py`:
- `UserFilterFormHelper.layout`: la Row diventa due colonne:

```python
    layout = Layout(
        Row(
            Column(Field("q")),
            Column(Field("email_verified")),
            css_class="grid gap-4 sm:grid-cols-2",
        ),
        Submit("submit", "Applica filtri", css_class="mt-3"),
    )
```

- `UserFilter.Meta.fields = ["email_verified"]` (resta il declared filter `q` e il metodo `filtra_testo` invariato)
- `UserUpdateForm.Meta.fields`: rimuovi `"force_premium"`; la Card "Stato account" diventa:

```python
            Card(
                "email_verified", "profile_complete", "marketing_consent",
                "is_active",
                title="Stato account",
            ),
```

In `template/apps/dashboard/user/tables.py`:
- in `UserTable`: rimuovi la colonna dichiarata `membership` e il metodo `render_membership`; in `Meta.fields` e `Meta.sequence` rimuovi `"membership"`
- in `UserTableExport.Meta.fields`: rimuovi `"membership"`

`template/apps/dashboard/user/views.py`: nessuna modifica (non cita membership) — verifica con grep.

- [ ] **Step 4: Test allineati** — in `template/tests/dashboard/test_user_views.py` rimuovi il test `test_filtro_per_membership` (il campo non esiste). Gli altri test non citano membership — verifica: `grep -n "membership\|force_premium" template/tests/dashboard/*.py` deve restituire zero righe dopo la modifica.

- [ ] **Step 5: Compila tutto per sicurezza**

```bash
cd /Users/marcominutoli/Lavoro/django-packages/django-keel
uv run python -m py_compile $(find template/apps/dashboard template/apps/history -name "*.py")
```

Expected: nessun output (exit 0). (Se `uv run` non ha un venv qui, usa `python3 -m py_compile ...`.)

- [ ] **Step 6: Commit**

```bash
git add template/apps/dashboard template/tests/dashboard
git commit -m "feat(dashboard): adatta i file Python al template (logger, no select2, User senza membership)"
```

---

### Task 3: Template HTML — i 4 file `.jinja` con `{{ project_name }}`

**Files:**
- Rename+Modify: `template/templates/dashboard/base.html` → `base.html.jinja`, `base_iframe.html` → `base_iframe.html.jinja`, `ui/components/sidebar.html` → `sidebar.html.jinja`, `index/index.html` → `index.html.jinja`

Tecnica anti-conflitto delimitatori: l'INTERO file viene avvolto in `{% raw %}` (prima riga) ... `{% endraw %}` (ultima riga); ogni inserto copier "buca" il raw con `{% endraw %}{{ project_name }}{% raw %}`. Copier processa solo i file `.jinja` e rimuove il suffisso in output.

- [ ] **Step 1: base.html.jinja**

```bash
cd /Users/marcominutoli/Lavoro/django-packages/django-keel/template/templates/dashboard
git mv base.html base.html.jinja
```

Poi applica queste modifiche esatte:

a) Prima riga del file: aggiungi `{% raw %}` (da sola, sopra `{% load static %}`). Ultima riga: aggiungi `{% endraw %}` (da sola, sotto `</html>`).

b) Sostituisci la riga del title:

```html
  <title>{% block title %}Dashboard{% endblock title %} | ri7ette</title>
```

con:

```html
  <title>{% block title %}Dashboard{% endblock title %} | {% endraw %}{{ project_name }}{% raw %}</title>
```

c) ELIMINA le tre righe dei favicon (il boiler non ha quegli asset; con il manifest storage in prod un asset mancante è un errore):

```html
  <link rel="icon" type="image/png" sizes="96x96" href="{% static 'images/favicons/favicon-96x96.png' %}">
  <link rel="icon" type="image/svg+xml" href="{% static 'images/favicons/favicon.svg' %}">
  <link rel="shortcut icon" href="{% static 'images/favicons/favicon.ico' %}">
```

e al loro posto lascia il commento Django:

```html
  {# Favicon: aggiungi qui i link quando il progetto ha i suoi asset in static/images/ #}
```

d) Sostituisci la riga del footer:

```html
    <footer class="px-6 py-3 text-xs text-ink-faint">{% now "Y" %} © ri7ette</footer>
```

con:

```html
    <footer class="px-6 py-3 text-xs text-ink-faint">{% now "Y" %} © {% endraw %}{{ project_name }}{% raw %}</footer>
```

- [ ] **Step 2: base_iframe.html.jinja** — `git mv base_iframe.html base_iframe.html.jinja`; avvolgi il file in `{% raw %}`/`{% endraw %}` come sopra; sostituisci nel title `| ri7ette` con `| {% endraw %}{{ project_name }}{% raw %}`.

- [ ] **Step 3: sidebar.html.jinja** — `git mv ui/components/sidebar.html ui/components/sidebar.html.jinja`; avvolgi in raw; sostituisci il blocco brand:

```html
    <img src="{% static 'images/logo-light.png' %}" alt="ri7ette" class="h-7">
    <span class="text-sm font-semibold tracking-wide text-ink-soft">admin</span>
```

con (niente logo immagine nel boiler):

```html
    <span class="text-base font-bold text-brand-edge">{% endraw %}{{ project_name }}{% raw %}</span>
    <span class="text-sm font-semibold tracking-wide text-ink-soft">admin</span>
```

Se il `{% load static %}` in testa resta inutilizzato dopo la rimozione dell'img, lascia `{% load dashboard_tags %}` e togli `static`.

- [ ] **Step 4: index.html.jinja** — `git mv index/index.html index/index.html.jinja`; avvolgi in raw; sostituisci:

```html
      Benvenuto nella dashboard di amministrazione di ri7ette.
```

con:

```html
      Benvenuto nella dashboard di amministrazione di {% endraw %}{{ project_name }}{% raw %}.
```

- [ ] **Step 5: Verifica residui nei template**

```bash
grep -rn "ri7" /Users/marcominutoli/Lavoro/django-packages/django-keel/template/templates/
```

Expected: zero risultati.

- [ ] **Step 6: Commit**

```bash
cd /Users/marcominutoli/Lavoro/django-packages/django-keel
git add template/templates/dashboard
git commit -m "feat(dashboard): template shell con project_name via copier (raw-guard sui tag django)"
```

---

### Task 4: Palette neutra, configurazioni e dipendenze

**Files:**
- Rewrite: `template/frontend/shared/tokens.css`
- Modify: `template/package.json.jinja`, `template/pyproject.toml.jinja`, `template/config/settings/base.py.jinja`, `template/config/settings/test.py.jinja`, `template/config/urls.py.jinja`, `template/README.md.jinja`

- [ ] **Step 1: tokens.css neutra** — sostituisci l'intero contenuto con:

```css
/* Token brand del progetto — condivisi tra i temi (dashboard, sito).
   PERSONALIZZA QUI: sostituisci questa palette neutra con i colori del brand.
   I nomi dei token sono usati dai template della dashboard: non rinominarli. */
@theme {
  --color-brand: #3b82f6;        /* azione primaria */
  --color-brand-edge: #2563eb;   /* hover/bordi */
  --color-brand-soft: #dbeafe;   /* sfondi attivi */
  --color-ink: #1e293b;          /* testo principale */
  --color-ink-soft: #475569;     /* testo secondario */
  --color-ink-faint: #94a3b8;    /* placeholder/disabled */
  --color-paper: #f8fafc;        /* sfondo pagina */
  --color-line: #e2e8f0;         /* bordi */
  --color-line-strong: #cbd5e1;
  --color-danger: #dc2626;
  --color-danger-soft: #fee2e2;
  --color-warn: #d97706;
  --color-warn-soft: #fef3c7;
  --font-sans: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
}
```

(Stessi nomi token di ri7ette, inclusa `--color-warn-soft`: i template li usano tutti.)

- [ ] **Step 2: package.json.jinja** — aggiungi nella sezione `scripts` (lasciando i `tailwind:*` esistenti):

```json
    "dashboard:css": "npx @tailwindcss/cli -i frontend/dashboard/styles.css -o static/dashboard/css/dashboard.css --minify",
    "dashboard:js": "esbuild frontend/dashboard/js/dashboard.js --bundle --minify --outfile=static/dashboard/js/dashboard.js",
    "dashboard:fonts": "mkdir -p static/fonts && cp node_modules/remixicon/fonts/remixicon.css node_modules/remixicon/fonts/remixicon.woff2 static/fonts/",
    "dashboard:build": "npm run dashboard:css && npm run dashboard:js && npm run dashboard:fonts",
    "dashboard:watch": "npx @tailwindcss/cli -i frontend/dashboard/styles.css -o static/dashboard/css/dashboard.css --watch",
    "dashboard:watch:js": "esbuild frontend/dashboard/js/dashboard.js --bundle --outfile=static/dashboard/js/dashboard.js --watch",
    "site:css": "npx @tailwindcss/cli -i frontend/site/styles.css -o static/site/css/site.css --minify",
    "site:js": "esbuild frontend/site/js/site.js --bundle --minify --outfile=static/site/js/site.js",
    "site:build": "npm run site:css && npm run site:js"
```

e le dipendenze:

```json
  "dependencies": {
    "@alpinejs/collapse": "^3.15.0",
    "@alpinejs/focus": "^3.15.0",
    "alpinejs": "^3.15.0",
    "htmx.org": "^2.0.0",
    "remixicon": "^4.5.0"
  }
```

(in devDependencies aggiungi `"esbuild": "^0.25.0"` accanto a tailwind). Mantieni il JSON valido: virgole e ordine.

- [ ] **Step 3: pyproject.toml.jinja** — nella lista `dependencies` aggiungi (in ordine alfabetico tra le django-*):

```toml
    "crispy-tailwind>=1.0.3",
    "django-addanother>=2.2.2",
    "django-dirtyfields>=1.9.9",
    "django-extra-views>=0.16.0",
    "django-tables2>=3.0.0",
    "python-slugify>=8.0.4",
    "tablib[xlsx]>=3.9.0",
```

(`django-filter` e `django-crispy-forms` ci sono già — verifica e non duplicare.)

- [ ] **Step 4: settings base.py.jinja** —

a) in `THIRD_PARTY_APPS` aggiungi (dove stanno le app simili):

```python
    "crispy_forms",
    "crispy_tailwind",
    "django_tables2",
    "extra_views",
    "django_addanother",
```

ATTENZIONE: verifica prima se `crispy_forms` è già presente (la dep c'è per unfold ma l'app potrebbe non essere installata) — aggiungi solo le mancanti.

b) in `LOCAL_APPS` aggiungi:

```python
    "apps.dashboard",
    "apps.history",
]
```

c) vicino a CRISPY_TEMPLATE_PACK (riga ~393):

```python
CRISPY_TEMPLATE_PACK = "unfold_crispy"
CRISPY_ALLOWED_TEMPLATE_PACKS = ["unfold_crispy", "tailwind"]

# Template di default per le tabelle django-tables2 (dashboard)
DJANGO_TABLES2_TEMPLATE = "django_tables2/tailwind.html"
```

- [ ] **Step 5: settings test.py.jinja** — in fondo aggiungi (fix imparato in ri7):

```python
# Storage statici semplice nei test: il manifest di WhiteNoise richiederebbe collectstatic
STORAGES["staticfiles"]["BACKEND"] = "django.contrib.staticfiles.storage.StaticFilesStorage"  # noqa: F405
```

(Verifica che test.py.jinja importi con star da base; se STORAGES non è importabile così, adatta al pattern del file.)

- [ ] **Step 6: urls.py.jinja** — accanto alle altre route non-API (vicino ad admin):

```python
    path("dashboard/", include("apps.dashboard.urls", namespace="dashboard")),
```

(Il file ha già `include` importato — verifica.)

- [ ] **Step 7: README.md.jinja** — nella sezione di setup post-generazione (individua quella esistente con i primi comandi; se non esiste, aggiungi una sezione "## Setup" dopo l'intro) aggiungi:

```markdown
### Frontend della dashboard

```bash
npm install
npm run dashboard:build   # CSS+JS della dashboard staff (output in static/dashboard/)
```

La dashboard è su `/dashboard/` (staff-only, login condiviso con l'admin).
Personalizza i colori del brand in `frontend/shared/tokens.css`.
```

- [ ] **Step 8: Commit**

```bash
git add template/frontend template/package.json.jinja template/pyproject.toml.jinja \
        template/config/settings/base.py.jinja template/config/settings/test.py.jinja \
        template/config/urls.py.jinja template/README.md.jinja
git commit -m "feat(dashboard): palette neutra, settings, dipendenze e script di build nel template"
```

---

### Task 5: Smoke test end-to-end del progetto generato

**Files:** nessun file nuovo nel repo (verifica); eventuali fix nei file dei Task 1-4.

- [ ] **Step 1: Genera il progetto di prova**

```bash
cd /Users/marcominutoli/Lavoro/django-packages/django-keel
rm -rf /tmp/keel-dash-smoke
uvx copier copy . /tmp/keel-dash-smoke \
  --data project_name="Dash Smoke" --data project_description="smoke" \
  --data author_name="Test" --data author_email="t@t.it" \
  --defaults --trust
```

Expected: generazione senza errori.

- [ ] **Step 2: Grep residui nel generato**

```bash
grep -rn "{{ project_\|{% raw %}\|{% endraw %}\|ri7\|Vivace\|narae" /tmp/keel-dash-smoke/templates /tmp/keel-dash-smoke/apps/dashboard /tmp/keel-dash-smoke/frontend || echo "PULITO"
grep -n "Dash Smoke" /tmp/keel-dash-smoke/templates/dashboard/base.html /tmp/keel-dash-smoke/templates/dashboard/ui/components/sidebar.html
```

Expected: "PULITO" e poi le occorrenze di "Dash Smoke" nel title/footer/sidebar (e niente suffisso .jinja sui file generati).

- [ ] **Step 3: Build frontend nel generato**

```bash
cd /tmp/keel-dash-smoke
npm install && npm run dashboard:build
ls -la static/dashboard/css/dashboard.css static/dashboard/js/dashboard.js static/fonts/remixicon.woff2
grep -c "bg-brand-soft\|w-60" static/dashboard/css/dashboard.css
```

Expected: file presenti; il grep > 0 (il CSS ha raccolto le classi dei template).

- [ ] **Step 4: Dipendenze Python e check**

```bash
cd /tmp/keel-dash-smoke
uv sync --all-extras
uv run python manage.py check
```

Expected: check 0 errori. Se mancano import (es. crispy_tailwind non installato perché la dep non è stata aggiunta bene), torna al Task 4 e correggi.

- [ ] **Step 5: Test del progetto generato (serve postgres)**

Il DB di default è postgres (vedi `.env` generato: porta 8432 via docker compose). In ordine di preferenza:

```bash
cd /tmp/keel-dash-smoke
docker compose up -d db 2>/dev/null && sleep 5 && uv run pytest tests/dashboard/ -v
```

Se docker non è disponibile sulla macchina: usa il postgres locale (quello dei progetti ri7) creando un DB di test e sovrascrivendo `DATABASE_URL` nel `.env` del progetto generato, poi rilancia pytest. Se nessun postgres è raggiungibile: status BLOCKED con il dettaglio — NON convertire il progetto a sqlite per aggirare (psqlextra/postgres-specific nel template).

Expected: tutti i test `tests/dashboard/` verdi (21: i 22 di ri7 meno `test_filtro_per_membership`).

- [ ] **Step 6: Pulizia**

```bash
docker compose -f /tmp/keel-dash-smoke/docker-compose.yml down -v 2>/dev/null
rm -rf /tmp/keel-dash-smoke /tmp/keel-baseline
```

- [ ] **Step 7: Commit di eventuali fix emersi**

```bash
cd /Users/marcominutoli/Lavoro/django-packages/django-keel
git add template/   # SOLO se ci sono fix; sempre per path della dashboard
git commit -m "fix(dashboard): correzioni emerse dallo smoke test del progetto generato"
```

(Se non ci sono fix, salta il commit.)

---

### Task 6: Test template-level in keel

**Files:**
- Create: `tests/test_dashboard_generation.py` (nel repo keel, non in template/)

- [ ] **Step 1: Scrivi il test**

Segui il pattern di `tests/test_generation.py` (fixture `generate` dal conftest di keel):

```python
"""Test di generazione per la dashboard staff inclusa nel template."""


def test_dashboard_files_generated(generate):
    """Il progetto generato contiene la dashboard completa."""
    project = generate()
    assert (project / "apps" / "dashboard" / "mixins.py").exists()
    assert (project / "apps" / "history" / "models.py").exists()
    assert (project / "templates" / "dashboard" / "base.html").exists()
    assert (project / "templates" / "django_tables2" / "tailwind.html").exists()
    assert (project / "frontend" / "shared" / "tokens.css").exists()
    assert (project / "frontend" / "dashboard" / "js" / "dashboard.js").exists()
    assert (project / "tests" / "dashboard" / "test_user_views.py").exists()


def test_dashboard_templates_have_project_name(generate):
    """project_name è interpolato nei template della shell, senza residui jinja."""
    project = generate()
    base = (project / "templates" / "dashboard" / "base.html").read_text()
    sidebar = (project / "templates" / "dashboard" / "ui" / "components" / "sidebar.html").read_text()
    assert "Test Project" in base          # title/footer
    assert "Test Project" in sidebar       # brand
    for content in (base, sidebar):
        assert "{{ project_name" not in content
        assert "{% raw %}" not in content
        assert "ri7" not in content


def test_dashboard_settings_wired(generate):
    """Settings e urls del generato includono la dashboard."""
    project = generate()
    settings = (project / "config" / "settings" / "base.py").read_text()
    urls = (project / "config" / "urls.py").read_text()
    assert '"apps.dashboard"' in settings
    assert '"crispy_tailwind"' in settings
    assert "DJANGO_TABLES2_TEMPLATE" in settings
    assert "apps.dashboard.urls" in urls
```

- [ ] **Step 2: Esegui il nuovo test**

```bash
cd /Users/marcominutoli/Lavoro/django-packages/django-keel
uv run pytest tests/test_dashboard_generation.py -v
```

Expected: PASS. ATTENZIONE: il conftest di keel (`copier_answers`) elenca variabili che il copier.yml WIP non definisce più (frontend, background_tasks, ...): copier ignora le risposte in eccesso, quindi dovrebbe funzionare. Se invece la fixture `generate` fallisce per il WIP del copier.yml: NON sistemare il WIP — status BLOCKED e si chiede all'autore.

- [ ] **Step 3: Lancia anche la suite esistente di keel per capire lo stato**

```bash
uv run pytest tests/ -q 2>&1 | tail -5
```

Se ci sono fallimenti PRE-ESISTENTI (legati al WIP, non alla dashboard), segnalali nel report senza correggerli. I test nuovi devono essere verdi.

- [ ] **Step 4: Commit**

```bash
git add tests/test_dashboard_generation.py
git commit -m "test(dashboard): generazione della dashboard verificata a livello template"
```

---

### Task 7: Documentazione keel

**Files:**
- Create: `docs/features/dashboard.md`
- Modify: `mkdocs.yml` (voce nav), `CHANGELOG.md`

- [ ] **Step 1: Crea `docs/features/dashboard.md`**

```markdown
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
```

- [ ] **Step 2: mkdocs.yml** — aggiungi la voce nella sezione nav delle features (rispetta l'indentazione esistente):

```yaml
      - Dashboard staff: features/dashboard.md
```

- [ ] **Step 3: CHANGELOG.md** — aggiungi in cima, sotto l'eventuale "Unreleased":

```markdown
### Added
- Dashboard staff Tailwind inclusa in ogni progetto generato: shell (sidebar/topbar),
  CRUD generico (django-tables2 + django-filter + crispy-tailwind), sezione Utenti
  di esempio, app `history`, test pytest, build asset con Tailwind CLI + esbuild.
```

- [ ] **Step 4: Verifica mkdocs e commit**

```bash
cd /Users/marcominutoli/Lavoro/django-packages/django-keel
uvx --with mkdocs-material mkdocs build --strict 2>&1 | tail -3   # se il progetto ha già un modo suo (requirements docs), usa quello
git add docs/features/dashboard.md mkdocs.yml CHANGELOG.md
git commit -m "docs(dashboard): pagina feature, nav e changelog"
```

(Se `mkdocs build --strict` fallisce per problemi PRE-ESISTENTI non legati alla pagina nuova, segnala senza correggere.)

---

## Note per l'esecutore

- **MAI committare il WIP dell'autore** (copier.yml, LICENSE, Dockerfile.jinja, ecc.): `git add` sempre per path espliciti. Mai `git add -A` né `git add .`.
- **MAI modificare copier.yml**: la dashboard non introduce variabili nuove.
- **ri7_backend non si tocca**: è la sorgente in sola lettura (`git -C $RI7 ...` solo comandi read-only).
- I task 1→4 preparano, il 5 è la verifica vera (progetto generato), 6-7 chiudono. Se lo smoke test del Task 5 trova errori nei file portati, i fix si fanno nei file di `template/` e si riverifica rigenerando.
- Convenzioni: commenti/UI in italiano, nomi tecnici in inglese (come ri7ette e come il codice portato).
