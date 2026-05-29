"""File / folder name construction and sanitisation."""
import re


def format_size(size_bytes: int) -> str:
    """Format the size into readable units."""
    if size_bytes >= 1_073_741_824:
        return f"{size_bytes / 1_073_741_824:.1f} Go"
    elif size_bytes >= 1_048_576:
        return f"{size_bytes / 1_048_576:.1f} Mo"
    return f"{size_bytes / 1_024:.0f} Ko"


def sanitize_filename(name: str) -> str:
    """Linear-time rewrite of the previous polynomial-degree regexes
    (CodeQL py/polynomial-redos #146). ``\\s*X\\s*`` greedy on input
    made of unmatched whitespace was O(n²); ``split``/``join`` is O(n)
    with the same effective output for well-formed inputs. Isolated
    tabs/newlines in filenames — which are anomalous and break shell
    scripts / display — are now normalised to single spaces.
    """
    name = name.replace(',', '')
    name = re.sub(r'[<>"/\\|?*]', '', name)
    if ':' in name:
        name = ' - '.join(part.strip() for part in name.split(':'))
    return ' '.join(name.split())


def build_movie_name(title: str, year: str, quality: str = "", ext: str = "") -> str:
    """Build a movie filename: ``Title (year) [quality].ext``.

    ``year``, ``quality`` and ``ext`` are optional and omitted when empty.
    The result is run through ``sanitize_filename``.
    """
    name = f"{title} ({year})" if year else title
    if quality:
        name += f" [{quality}]"
    if ext:
        name += ext
    return sanitize_filename(name)


def build_series_folder_name(title: str, year: str = "") -> str:
    """Build a series folder name: ``Title (year)`` (year omitted when empty)."""
    name = f"{title} ({year})" if year else title
    return sanitize_filename(name)


def build_season_folder_name(season_number: int) -> str:
    """Build a season folder name: ``Saison NN`` (zero-padded to 2 digits)."""
    return f"Saison {season_number:02d}"


def build_episode_name(series: str, season: int, episode: int, title: str, ext: str = "") -> str:
    """Build an episode filename: ``Series - SssEee - Title.ext``.

    ``season`` and ``episode`` are zero-padded to 2 digits and must be
    non-negative; a negative value raises ``ValueError``. This is defence
    in depth — the HTTP boundary already enforces ``ge=0`` via the Pydantic
    schema, but the helper can also be called from scripts/tests.
    """
    if season < 0 or episode < 0:
        raise ValueError("season and episode must be non-negative")
    name = f"{series} - S{season:02d}E{episode:02d} - {title}"
    if ext:
        name += ext
    return sanitize_filename(name)
