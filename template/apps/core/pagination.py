from rest_framework.pagination import PageNumberPagination


class CustomPageNumberPagination(PageNumberPagination):
    # Allow clients to set page_size via URL query parameter
    # Example: /api/items/?page_size=25
    page_size_query_param = "page_size"

    # (Recommended) Set a maximum page size that clients can request
    # This prevents users from requesting too much data and causing server performance issues
    max_page_size = 30
