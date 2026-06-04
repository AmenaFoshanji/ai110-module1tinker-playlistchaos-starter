from typing import Dict, List, Optional, Tuple

Song = Dict[str, object]
PlaylistMap = Dict[str, List[Song]]

DEFAULT_PROFILE = {
    "name": "Default",
    "hype_min_energy": 7,
    "chill_max_energy": 3,
    "favorite_genre": "rock",
    "include_mixed": True,
}


def normalize_title(title: str) -> str:
    """Normalize a song title for comparisons."""
    if not isinstance(title, str):
        return ""
    return title.strip()


def normalize_artist(artist: str) -> str:
    """Normalize an artist name for comparisons."""
    if not artist:
        return ""
    return artist.strip().lower()


def normalize_genre(genre: str) -> str:
    """Normalize a genre name for comparisons."""
    return genre.lower().strip()


def normalize_song(raw: Song) -> Song:
    """Return a normalized song dict with expected keys."""
    title = normalize_title(str(raw.get("title", "")))
    artist = normalize_artist(str(raw.get("artist", "")))
    genre = normalize_genre(str(raw.get("genre", "")))
    energy = raw.get("energy", 5)

    # Convert energy to int and ensure it's within valid bounds (1-10)
    if isinstance(energy, str):
        try:
            energy = int(energy)
        except ValueError:
            energy = 5
    else:
        try:
            energy = int(energy)
        except (TypeError, ValueError):
            energy = 5

    # Clamp energy to valid range [1, 10]
    energy = max(1, min(10, energy))

    tags = raw.get("tags", [])
    if isinstance(tags, str):
        tags = [tags]
    elif not isinstance(tags, list):
        tags = []

    return {
        "title": title,
        "artist": artist,
        "genre": genre,
        "energy": energy,
        "tags": tags,
    }


def classify_song(song: Song, profile: Dict[str, object]) -> str:
    """Return a mood label given a song and user profile.
    
    Classification priority (to avoid ambiguity):
    1. Check if explicitly chill (low energy or chill genre)
    2. Check if explicitly hype (high energy or hype genre or favorite genre)
    3. Otherwise Mixed
    """
    energy = song.get("energy", 5)
    genre = song.get("genre", "").lower().strip()

    hype_min_energy = int(profile.get("hype_min_energy", 7))
    chill_max_energy = int(profile.get("chill_max_energy", 3))
    favorite_genre = str(profile.get("favorite_genre", "")).lower().strip()

    # Ensure valid bounds
    hype_min_energy = max(1, min(10, hype_min_energy))
    chill_max_energy = max(1, min(10, chill_max_energy))

    hype_keywords = ["rock", "punk", "party", "metal", "dance", "pop"]
    chill_keywords = ["lofi", "ambient", "sleep", "relax", "calm"]

    is_hype_genre = any(k in genre for k in hype_keywords)
    is_chill_genre = any(k in genre for k in chill_keywords)

    # Priority: Chill check first (most specific)
    if energy <= chill_max_energy or is_chill_genre:
        return "Chill"

    # Hype check second
    if energy >= hype_min_energy or is_hype_genre or genre == favorite_genre:
        return "Hype"

    # Default to Mixed if in the middle range
    return "Mixed"


def build_playlists(songs: List[Song], profile: Dict[str, object]) -> PlaylistMap:
    """Group songs into playlists based on mood and profile.
    
    Handles invalid inputs gracefully.
    """
    playlists: PlaylistMap = {
        "Hype": [],
        "Chill": [],
        "Mixed": [],
    }

    if not isinstance(songs, list):
        return playlists

    if not isinstance(profile, dict):
        profile = {}

    for song in songs:
        if not isinstance(song, dict):
            continue
        try:
            normalized = normalize_song(song)
            mood = classify_song(normalized, profile)
            normalized["mood"] = mood
            playlists[mood].append(normalized)
        except Exception:
            # Skip any songs that fail to process
            continue

    return playlists


def merge_playlists(a: PlaylistMap, b: PlaylistMap) -> PlaylistMap:
    """Merge two playlist maps into a new map.
    
    Combines songs from both maps. Handles None or invalid inputs gracefully.
    """
    if not isinstance(a, dict):
        a = {}
    if not isinstance(b, dict):
        b = {}

    merged: PlaylistMap = {}
    for key in set(list(a.keys()) + list(b.keys())):
        songs_a = a.get(key, [])
        songs_b = b.get(key, [])
        if not isinstance(songs_a, list):
            songs_a = []
        if not isinstance(songs_b, list):
            songs_b = []
        merged[key] = songs_a[:] + songs_b[:]

    return merged


def compute_playlist_stats(playlists: PlaylistMap) -> Dict[str, object]:
    """Compute statistics across all playlists.
    
    Handles edge cases like empty playlists gracefully.
    """
    all_songs: List[Song] = []
    for songs in playlists.values():
        if isinstance(songs, list):
            all_songs.extend(songs)

    hype = playlists.get("Hype", [])
    chill = playlists.get("Chill", [])
    mixed = playlists.get("Mixed", [])

    if not isinstance(hype, list):
        hype = []
    if not isinstance(chill, list):
        chill = []
    if not isinstance(mixed, list):
        mixed = []

    total_songs = len(all_songs)
    hype_ratio = len(hype) / total_songs if total_songs > 0 else 0.0

    avg_energy = 0.0
    if total_songs > 0:
        energies = []
        for song in all_songs:
            if isinstance(song, dict):
                energy = song.get("energy", 5)
                try:
                    energies.append(int(energy))
                except (TypeError, ValueError):
                    energies.append(5)
        if energies:
            avg_energy = sum(energies) / len(energies)

    top_artist, top_count = most_common_artist(all_songs)

    return {
        "total_songs": len(all_songs),
        "hype_count": len(hype),
        "chill_count": len(chill),
        "mixed_count": len(mixed),
        "hype_ratio": hype_ratio,
        "avg_energy": avg_energy,
        "top_artist": top_artist,
        "top_artist_count": top_count,
    }


def most_common_artist(songs: List[Song]) -> Tuple[str, int]:
    """Return the most common artist and count.
    
    In case of tie, returns the first one alphabetically (deterministic).
    """
    counts: Dict[str, int] = {}
    for song in songs:
        if not isinstance(song, dict):
            continue
        artist = str(song.get("artist", "")).strip()
        if not artist:
            continue
        counts[artist] = counts.get(artist, 0) + 1

    if not counts:
        return "", 0

    # Sort by count (descending), then by name (ascending) for deterministic results
    items = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return items[0]


def search_songs(
    songs: List[Song],
    query: str,
    field: str = "artist",
) -> List[Song]:
    """Return songs matching the query on a given field.
    
    Returns all songs if query is empty. Search is case-insensitive.
    """
    if not songs:
        return []

    if not query or not isinstance(query, str):
        return songs

    q = query.lower().strip()
    if not q:
        return songs

    filtered: List[Song] = []

    for song in songs:
        if not isinstance(song, dict):
            continue
        value = str(song.get(field, "")).lower().strip()
        if value and q in value:
            filtered.append(song)

    return filtered


def lucky_pick(
    playlists: PlaylistMap,
    mode: str = "any",
) -> Optional[Song]:
    """Pick a song from the playlists according to mode."""
    if mode == "hype":
        songs = playlists.get("Hype", [])
    elif mode == "chill":
        songs = playlists.get("Chill", [])
    else:
        songs = (
            playlists.get("Hype", [])
            + playlists.get("Chill", [])
            + playlists.get("Mixed", [])
        )

    return random_choice_or_none(songs)


def random_choice_or_none(songs: List[Song]) -> Optional[Song]:
    """Return a random song or None if list is empty or invalid."""
    import random

    if not isinstance(songs, list):
        return None
    if not songs:
        return None
    return random.choice(songs)


def history_summary(history: List[Song]) -> Dict[str, int]:
    """Return a summary of moods seen in the history.
    
    Ensures all moods are tracked, with invalid moods counted as 'Mixed'.
    """
    counts = {"Hype": 0, "Chill": 0, "Mixed": 0}
    valid_moods = {"Hype", "Chill", "Mixed"}

    for song in history:
        if not isinstance(song, dict):
            continue
        mood = str(song.get("mood", "Mixed")).strip()
        if mood in valid_moods:
            counts[mood] += 1
        else:
            counts["Mixed"] += 1

    return counts
