from rest_framework.exceptions import ValidationError


def check_dependencies_before_delete(instance, dependencies_config):
    """
    Check if an instance has dependencies that prevent deletion.

    This helper is used before performing a physical deletion to ensure
    that the object doesn't have any active dependencies. If dependencies
    are found, it raises a ValidationError with detailed information.

    Args:
        instance: The model instance to check
        dependencies_config: Dict with dependency configuration
            {
                'relation_name': {
                    'label': 'human-readable name' (e.g., 'prenotazioni'),
                    'filter': dict for filtering (optional, e.g., {'status__in': ['pending', 'confirmed']})
                }
            }

    Raises:
        ValidationError: If dependencies exist that block deletion

    Example:
        check_dependencies_before_delete(service, {
            'bookings': {
                'label': 'prenotazioni',
                'filter': {'status__in': ['pending', 'confirmed']}
            }
        })
    """
    blocking_deps = []
    total_count = 0

    for relation_name, config in dependencies_config.items():
        # Get the related manager
        if not hasattr(instance, relation_name):
            continue

        related_manager = getattr(instance, relation_name)

        # Apply filters if specified
        queryset = related_manager.all()
        if "filter" in config:
            queryset = queryset.filter(**config["filter"])

        count = queryset.count()
        if count > 0:
            blocking_deps.append(
                {"relation": relation_name, "label": config["label"], "count": count}
            )
            total_count += count

    if blocking_deps:
        # Build detailed message
        deps_details = ", ".join([f"{dep['count']} {dep['label']}" for dep in blocking_deps])

        raise ValidationError(
            {
                "detail": f"Impossibile eliminare. Ci sono dipendenze collegate: {deps_details}. "
                f"Per nascondere l'oggetto, archivialo invece di eliminarlo.",
                "dependencies": blocking_deps,
                "can_delete": False,  # type: ignore[dict-item]
                "suggested_action": "archive",
            }
        )
