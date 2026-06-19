"""Behavioral tests for the opinionated, always-on stack.

Il template non ha piu' feature a toggle: le funzionalita' sotto sono sempre
presenti nel progetto generato. I test verificano il loro cablaggio.
"""

import py_compile


# Cache (Redis) — sempre attiva


def test_redis_cache_configured(generate):
    """Redis e' la cache di default (django_redis)."""
    project = generate()
    content = (project / "config/settings/base.py").read_text()

    assert "django_redis" in content
    assert "RedisCache" in content
    assert "CACHES" in content


# Background tasks (Celery) — sempre configurati


def test_celery_configured(generate):
    """Celery (beat + results) e' configurato nelle settings."""
    project = generate()
    content = (project / "config/settings/base.py").read_text()

    assert "django_celery_beat" in content
    assert "django_celery_results" in content
    assert "CELERY_BROKER_URL" in content


# i18n / traduzioni — sempre attive


def test_i18n_and_modeltranslation_enabled(generate):
    """USE_I18N attivo, modeltranslation in INSTALLED_APPS, LANGUAGES definite."""
    project = generate()
    content = (project / "config/settings/base.py").read_text()

    assert "USE_I18N = True" in content
    assert "modeltranslation" in content
    assert "LANGUAGES" in content


# Media / static storage — Whitenoise


def test_whitenoise_storage_configured(generate):
    """Whitenoise serve gli static (middleware + storage)."""
    project = generate()
    content = (project / "config/settings/base.py").read_text()

    assert "whitenoise.middleware.WhiteNoiseMiddleware" in content
    assert "whitenoise" in content.lower()


# Billing / Stripe — dipendenze sempre presenti


def test_stripe_dependency_present(generate):
    """Stripe e' tra le dipendenze del progetto generato."""
    project = generate()
    pyproject = (project / "pyproject.toml").read_text()

    assert "stripe>=" in pyproject


# Deploy — solo compose (dev/prod) + nginx


def test_compose_deploy_files_generated(generate):
    """Il deploy e' via docker compose (dev + prod), senza target k8s/render/fly."""
    project = generate()

    compose = project / "deploy" / "compose"
    assert (compose / "docker-compose.dev.yml").exists()
    assert (compose / "docker-compose.prod.yml").exists()

    # nessun target a toggle rimasto
    assert not (project / "render.yaml").exists()
    assert not (project / "fly.toml").exists()
    assert not (project / "deploy" / "k8s").exists()
    assert not (project / "deploy" / "ansible").exists()


# Sanity: l'intero progetto compila


def test_generated_project_compiles(generate):
    """Tutti i file Python del progetto generato hanno sintassi valida."""
    project = generate()
    for py_file in project.rglob("*.py"):
        py_compile.compile(str(py_file), doraise=True)
