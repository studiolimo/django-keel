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
