"""Functional tests for template project generation.

Il template e' opinionato (niente toggle): uv + PostgreSQL + DRF + SimpleJWT,
app `account`/`core`/`dashboard`/`history`/`notifications`/`users`, dashboard
staff. I test verificano la struttura e lo stack garantito dal progetto generato.
"""

import py_compile

import pytest
import yaml


# Basic Project Generation Tests


def test_basic_project_generates(generate):
    """Test that a basic project can be generated."""
    project = generate()
    assert project.exists()
    assert (project / "manage.py").exists()
    assert (project / "config").exists()
    assert (project / "apps").exists()


def test_project_has_valid_python_syntax(generate):
    """Test that all generated Python files have valid syntax."""
    project = generate()

    python_files = list(project.rglob("*.py"))
    assert len(python_files) > 0, "No Python files found"

    for py_file in python_files:
        try:
            py_compile.compile(str(py_file), doraise=True)
        except py_compile.PyCompileError as e:
            pytest.fail(f"Syntax error in {py_file}: {e}")


def test_project_has_valid_yaml_files(generate):
    """Test that all generated YAML files are valid."""
    project = generate()

    yaml_files = [
        project / ".pre-commit-config.yaml",
        project / ".github" / "workflows" / "ci.yml",
    ]

    for yaml_file in yaml_files:
        if yaml_file.exists():
            with open(yaml_file) as f:
                try:
                    yaml.safe_load(f)
                except yaml.YAMLError as e:
                    # Show file content for debugging
                    content = yaml_file.read_text()
                    pytest.fail(
                        f"Invalid YAML in {yaml_file}:\n"
                        f"Error: {e}\n"
                        f"Content preview:\n{content[:500]}"
                    )


def test_project_structure_is_correct(generate):
    """Test that the generated project has the expected structure."""
    project = generate()

    expected_dirs = [
        "config",
        "config/settings",
        "apps",
        "apps/account",
        "apps/core",
        "apps/dashboard",
        "apps/users",
        "static",
        "media",
        "templates",
    ]

    for dir_path in expected_dirs:
        assert (project / dir_path).exists(), f"Missing directory: {dir_path}"

    expected_files = [
        "manage.py",
        "config/__init__.py",
        "config/settings/__init__.py",
        "config/settings/base.py",
        "config/settings/local.py",
        "config/settings/prod.py",
        "config/settings/test.py",
        "config/urls.py",
        "config/wsgi.py",
        "config/asgi.py",
        "apps/core/views.py",
        "apps/users/models.py",
        ".gitignore",
        "README.md",
        "pyproject.toml",
    ]

    for file_path in expected_files:
        assert (project / file_path).exists(), f"Missing file: {file_path}"


def test_project_name_has_validator(template_dir):
    """Test that project_name field has a non-empty validator."""
    copier_yml = template_dir / "copier.yml"

    with open(copier_yml) as f:
        config = yaml.safe_load(f)

    assert "project_name" in config
    assert "validator" in config["project_name"]
    validator = config["project_name"]["validator"]
    assert "project_name" in validator
    assert "empty" in validator.lower() or "not project_name" in validator


def test_project_description_has_validator(template_dir):
    """Test that project_description field has a non-empty validator."""
    copier_yml = template_dir / "copier.yml"

    with open(copier_yml) as f:
        config = yaml.safe_load(f)

    assert "project_description" in config
    assert "validator" in config["project_description"]
    validator = config["project_description"]["validator"]
    assert "project_description" in validator
    assert "empty" in validator.lower() or "not project_description" in validator


# Tech Stack Tests (opinionated, always-on)


def test_uv_pyproject_generated(generate):
    """pyproject.toml e' in formato uv/PEP 621 con le dipendenze base."""
    project = generate()
    pyproject = project / "pyproject.toml"

    assert pyproject.exists()
    content = pyproject.read_text()
    assert "[project]" in content
    assert "dependencies" in content
    assert "django>=" in content
    # stack opinionato: niente poetry
    assert "[tool.poetry]" not in content


def test_drf_and_jwt_configured(generate):
    """DRF + SimpleJWT + spectacular/filters/cors sono sempre configurati."""
    project = generate()
    content = (project / "config/settings/base.py").read_text()

    assert "rest_framework" in content
    assert "rest_framework_simplejwt" in content
    assert "drf_spectacular" in content
    assert "django_filters" in content
    assert "corsheaders" in content
    assert "SIMPLE_JWT" in content


def test_opinionated_stack_excludes_removed_toggles(generate):
    """Lo stack non include le vecchie alternative a toggle (graphql/allauth/channels)."""
    project = generate()
    content = (project / "config/settings/base.py").read_text()

    assert "strawberry" not in content
    assert "allauth" not in content
    assert "channels" not in content
    # l'API vive nelle singole app (apps/<x>/api), non in un'app `api` dedicata
    assert not (project / "apps/api").exists()
