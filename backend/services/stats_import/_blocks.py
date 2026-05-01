"""Extraction helper: Jellystats backup may be a dict or a wrapped list."""


def _extract_blocks(data, key: str) -> list:
    """Return entries for a given key (jf_libraries, jf_library_items, ...)."""
    if isinstance(data, list):
        items: list = []
        for block in data:
            if isinstance(block, dict):
                items.extend(block.get(key, []))
        return items
    if isinstance(data, dict):
        return data.get(key, [])
    return []
