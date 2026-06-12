from django import template
from django.urls import reverse

from apps.dashboard.sidebar_menu import DASHBOARD_MENU

register = template.Library()


@register.inclusion_tag('dashboard/ui/components/menu.html', takes_context=True)
def render_dashboard_menu(context):
    request = context['request']
    user = request.user

    def check_menu_item_roles(item):
        # Dashboard solo staff: superuser vede tutto, staff vede tutto
        # tranne le voci marcate hide_to_superuser (legacy, nessuna oggi).
        if item.get("hide_to_superuser", False) and user.is_superuser:
            return False
        return user.is_staff

    def get_base_path(url):
        parts = url.strip('/').split('/')
        return f"/{parts[1]}/" if len(parts) > 1 else "/"

    def get_section_parts(url):
        """
        Restituisce tutte le parti del path dopo il base path.
        Es: /dashboard/promotions/coupons/list/ -> ['coupons', 'list']
        """
        parts = url.strip('/').split('/')
        return parts[2:] if len(parts) > 2 else []

    def normalize_section(parts):
        """
        Normalizza le parti del path rimuovendo 'list' e gestendo singolare/plurale
        Es: ['coupons', 'list'] -> 'coupon'
        """
        if not parts:
            return ''

        # Rimuove 'list' se è l'ultima parte
        normalized_parts = [p for p in parts if p != 'list']
        if not normalized_parts:
            return ''

        # Prende la prima parte e la converte al singolare se è plurale
        first_part = normalized_parts[0]
        if first_part.endswith('s'):
            return first_part[:-1]
        return first_part

    def sections_match(current_parts, menu_parts):
        """
        Verifica se le sezioni corrispondono dopo la normalizzazione
        """
        if not current_parts or not menu_parts:
            return False

        # Normalizza entrambe le sezioni
        current_section = normalize_section(current_parts)
        menu_section = normalize_section(menu_parts)

        return current_section and menu_section and current_section == menu_section

    def process_menu_items(items):
        processed_items = []
        for item in items:
            if not check_menu_item_roles(item):
                continue

            processed_item = item.copy()
            current_path = request.path.rstrip('/')
            current_parts = get_section_parts(current_path)

            # Gestione menu con sottovoci
            if 'children' in item:
                processed_item['children'] = process_menu_items(item['children'])
                if not processed_item['children']:
                    continue

                # Raccoglie i path e le sezioni di tutti i figli
                child_paths = set()
                child_sections = []  # Lista di parti di sezioni
                for child in processed_item['children']:
                    if 'url' in child:
                        child_path = child['url'].rstrip('/')
                        child_paths.add(child_path)
                        child_sections.append(get_section_parts(child_path))

                    if 'children' in child:
                        for subchild in child['children']:
                            if 'url' in subchild:
                                subchild_path = subchild['url'].rstrip('/')
                                child_paths.add(subchild_path)
                                child_sections.append(get_section_parts(subchild_path))

                # Il menu è aperto se:
                # 1. Il path corrente corrisponde a uno dei path dei figli
                # 2. Le sezioni normalizzate corrispondono
                processed_item['is_open'] = (
                    current_path in child_paths or
                    any(sections_match(current_parts, child_parts)
                        for child_parts in child_sections)
                )

            # Gestione link diretti
            if 'url_name' in item:
                url = reverse(item['url_name'])
                processed_item['url'] = url
                menu_parts = get_section_parts(url)

                # Il link è attivo se:
                # 1. Il path corrente corrisponde esattamente all'URL del menu
                # 2. Le sezioni normalizzate corrispondono
                processed_item['is_active'] = (
                    current_path == url.rstrip('/') or
                    sections_match(current_parts, menu_parts)
                )

            processed_items.append(processed_item)

        return processed_items

    menu_items = process_menu_items(DASHBOARD_MENU)

    return {
        'menu_items': menu_items,
        'request': request
    }
