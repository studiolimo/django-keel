# Dashboard staff Tailwind nel template django-keel

**Data**: 2026-06-12
**Stato**: approvata

## Contesto e motivazione

In ri7_backend (progetto generato da keel) è stata costruita una dashboard
amministrativa staff-only in Tailwind 4 + htmx + Alpine, con CRUD generico su
mixin (django-tables2 + django-filter + crispy-tailwind), sezione pilota Utenti
e test pytest (branch `feat/dashboard-tailwind`, 15+ commit, review completa).
Questo sotto-progetto la porta nel boilerplate, così ogni progetto generato
parte con la dashboard pronta.

Decisioni prese in brainstorming:

- **Sempre inclusa**: nessun flag copier `include_dashboard`. Meno condizionali
  jinja, template più robusto; chi non la vuole cancella le cartelle.
- **Struttura frontend completa**: `frontend/{shared,dashboard,site}` come in
  ri7ette (token condivisi + tema sito predisposto vuoto).
- **Porting file-per-file** (no pacchetto pip, no script di sync): il codice
  appartiene al progetto generato, in linea con la filosofia del boiler.
- **Nessuna nuova variabile copier**: si usano solo quelle esistenti
  (`project_name`, `project_slug`); la palette non è una domanda del questionario.

## Sorgente del porting

Branch `feat/dashboard-tailwind` di
`~/Lavoro/siti/ri7ette_project/ri7_backend` (HEAD = commit
"fix(dashboard): redirect post-delete, whitelist azioni bulk, ..."). È la
versione passata da review finale: delete solo via POST con CSRF e whitelist
azioni, dialog conferma con focus trap, copy italiana nei mixin.

## Cosa si porta in `template/`

```
apps/dashboard/            # mixins, forms (DashboardFormHelper), crispy_layout,
                           # templatetags, sidebar_menu, index/, user/ (pilota)
apps/history/              # ObjectHistory + migrazione (dipendenza dei mixins)
templates/dashboard/       # base, base_iframe, ui/ (shell + list + form + actions)
templates/django_tables2/tailwind.html
templates/crispy_layout/{card,image}.html
templates/tailwind/table_inline_formset.html
frontend/shared/tokens.css           # palette NEUTRA di default
frontend/dashboard/{styles.css,js/dashboard.js}
frontend/site/{styles.css,js/site.js}
tests/dashboard/           # conftest + test permessi/shell/forms/user_views
```

File che diventano `.jinja` (serve una variabile) — tutti gli altri restano
file normali:

| File | Variabili usate |
|---|---|
| `templates/dashboard/base.html` | `{{ project_name }}` in `<title>` e footer © |
| `templates/dashboard/base_iframe.html` | `{{ project_name }}` in `<title>` |
| `templates/dashboard/ui/components/sidebar.html` | brand testuale `{{ project_name }}` |
| `templates/dashboard/index/index.html` | testo di benvenuto col nome progetto |
| `package.json.jinja` (esistente) | aggiunta script `dashboard:*`/`site:*` e deps |
| `pyproject.toml.jinja` (esistente) | aggiunta dipendenze dashboard |
| `config/settings/base.py(.jinja)` | aggiunta app e config crispy/tables2 |
| `README.md.jinja` (esistente) | step post-generazione npm |

ATTENZIONE conflitto jinja/django: i template Django contengono `{{ }}`/`{% %}`
che copier interpreterebbe. Nei file `.jinja` della tabella sopra i delimitatori
Django vanno protetti con `{% raw %}...{% endraw %}` (o si tengono fuori dal
`.jinja` le parti Django pure). Regola pratica: rinominare in `.jinja` SOLO i
file elencati e proteggere tutto il contenuto Django con raw, lasciando fuori
dal raw solo gli inserti copier.

## Adattamenti rispetto a ri7ette

1. **Palette neutra** in `tokens.css`: scala sobria (slate/blu) con lo stesso
   set di nomi token (`brand`, `brand-edge`, `brand-soft`, `ink*`, `paper`,
   `line*`, `danger*`, `warn*`) e commento in testa "personalizza qui col brand
   del progetto". Stessi nomi = i template funzionano senza modifiche.
2. **Sezione Utenti senza membership**: il `User` di keel non ha
   `membership`/`force_premium`. Tabella: selection/email/username/nome/
   email_verified/date_joined; filtro: `q` + `email_verified`; form: email
   (read-only/disabled), username, first/last name, email_verified,
   profile_complete, marketing_consent, is_active. Niente badge membership.
3. **Sidebar senza logo immagine**: brand testuale `{{ project_name }}` (il
   boiler non ha asset grafici); i favicon citati in base.html vanno
   condizionati all'esistenza o sostituiti con il set che keel già fornisce
   (verificare in `template/static/`).
4. **Login admin**: keel usa unfold per l'admin — il login condiviso
   `admin:login` funziona invariato. Verificare che `CRISPY_TEMPLATE_PACK`
   resti il default di keel e si aggiunga solo "tailwind" agli allowed.

## Output di build: NON committati nel template

A differenza dei progetti generati (che committano `static/dashboard/`), il
template non versiona output minificati. Il `README.md.jinja` generato include
negli step post-generazione:

```bash
npm install
npm run dashboard:build
```

## Dipendenze da aggiungere a `pyproject.toml.jinja`

`django-tables2`, `tablib[xlsx]`, `django-filter` (se non già presente),
`django-crispy-forms` (se non già presente), `crispy-tailwind`,
`django-extra-views`, `django-addanother`, `django-dirtyfields`,
`python-slugify`. In fase di piano si verifica cosa keel ha già e si aggiunge
solo il delta. NON si portano: rolepermissions, six, crispy-bootstrap5,
django-select2 (non usato dalla dashboard ripulita — verificare che i mixins
portati non lo importino).

## Verifica (il test vero di un template è generare un progetto)

Smoke test end-to-end, da eseguire a mano o come script in `tests/` di keel
secondo il pattern esistente (da verificare in fase di piano):

1. `copier copy . /tmp/keel-smoke --data project_name=... --defaults --trust`
2. nel progetto generato: `uv sync`, `npm install && npm run dashboard:build`,
   `manage.py migrate`, `manage.py check`
3. `pytest tests/dashboard/` → tutti verdi
4. grep che nessun file generato contenga residui jinja (`{{ project_` non
   risolti) o riferimenti a ri7ette/Vivace/narae

## Documentazione

- Nuova pagina `docs/features/dashboard.md` in keel: architettura, pattern
  per aggiungere sezioni (fotocopia di `apps/dashboard/user/`), build asset,
  regole (delete via POST, htmx solo frammenti, token brand).
- `mkdocs.yml`: voce di menu per la pagina.
- README generato: sezione breve sulla dashboard + step npm post-generazione.

## Fuori scope

- Flag copier per escludere la dashboard
- Logo/asset grafici nel boiler
- Variabili copier per la palette
- Backport in ri7_backend di eventuali migliorie fatte durante il porting
  (si annotano e si valutano dopo)

## Vincoli e rischi

- **WIP in corso su keel**: `copier.yml` e altri file hanno modifiche non
  committate dell'autore (refactor variabili in corso: nomi file citano
  `frontend`, `background_tasks`, `deployment_targets`). Il porting si basa
  SOLO sulle variabili oggi definite in copier.yml (`project_name`,
  `project_slug`, ...) e non tocca i file del WIP; i commit del porting
  includono esclusivamente i file della dashboard.
- **Conflitto delimitatori jinja/django**: mitigato con la regola raw sopra;
  lo smoke test (grep residui) lo verifica.
- **Drift keel ↔ ri7ette**: accettato; il boiler è uno snapshot, non un fork
  sincronizzato.
