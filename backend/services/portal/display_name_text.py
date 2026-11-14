"""How a display name reads: its skeleton, its comparison key, the characters
that hide text, and the characters a reader counts. Pure text, no database."""
import unicodedata

from constants import display_name as dn

# Letters of other scripts drawn like a Latin one, by code point. NFKD then folds
# accents, full-width and ligature forms; case and the rest are dropped after.
_LOOKALIKES = str.maketrans({
    # Cyrillic capitals: A B E K M H O P C T Y X I J S
    0x0410: "a", 0x0412: "b", 0x0415: "e", 0x041A: "k", 0x041C: "m",
    0x041D: "h", 0x041E: "o", 0x0420: "p", 0x0421: "c", 0x0422: "t",
    0x0423: "y", 0x0425: "x", 0x0406: "i", 0x0408: "j", 0x0405: "s",
    # Cyrillic small: a b e k m h o p c t y x i j s d h q w l
    0x0430: "a", 0x0432: "b", 0x0435: "e", 0x043A: "k", 0x043C: "m",
    0x043D: "h", 0x043E: "o", 0x0440: "p", 0x0441: "c", 0x0442: "t",
    0x0443: "y", 0x0445: "x", 0x0456: "i", 0x0458: "j", 0x0455: "s",
    0x0501: "d", 0x04BB: "h", 0x051B: "q", 0x051D: "w", 0x04CF: "l",
    # Greek capitals: A B E Z H I K M N O P T Y X
    0x0391: "a", 0x0392: "b", 0x0395: "e", 0x0396: "z", 0x0397: "h",
    0x0399: "i", 0x039A: "k", 0x039C: "m", 0x039D: "n", 0x039F: "o",
    0x03A1: "p", 0x03A4: "t", 0x03A5: "y", 0x03A7: "x",
    # Greek small: a i k v o p u x
    0x03B1: "a", 0x03B9: "i", 0x03BA: "k", 0x03BD: "v", 0x03BF: "o",
    0x03C1: "p", 0x03C5: "u", 0x03C7: "x",
    # Latin dotless i, alpha and script g
    0x0131: "i", 0x0251: "a", 0x0261: "g",
})
_SAME_SHAPE = str.maketrans({"l": "i", "1": "i", "0": "o"})

# Blank fillers with no ink of their own (the null notehead is drawn empty): a name
# could hide behind them.
_BLANKS = frozenset({0x034F, 0x115F, 0x1160, 0x2800, 0x3164, 0xFFA0, 0x1D159})
# Default_Ignorable marks (variation selectors, Mongolian and Khmer ones), drawn as
# nothing; format characters (Cf) are ignorable too.
_IGNORABLE_MARKS = ((0x17B4, 0x17B5), (0x180B, 0x180F), (0xFE00, 0xFE0F), (0xE0100, 0xE01EF))
_ZWNJ, _ZWJ, _EMOJI_STYLE = 0x200C, 0x200D, 0xFE0F
_KEYCAP = chr(0x20E3)
_VIRAMA_CLASS = 9
_SKIN_TONES = range(0x1F3FB, 0x1F400)
_FLAG, _CANCEL_TAG = 0x1F3F4, 0xE007F
_TAG_LETTERS = range(0xE0020, 0xE007F)
# Chinese ideographs and Korean syllables: each character is a whole syllable (the
# iteration mark repeats the ideograph before it).
_SYLLABIC = (
    "CJK UNIFIED IDEOGRAPH", "CJK COMPATIBILITY IDEOGRAPH", "HANGUL SYLLABLE",
    "IDEOGRAPHIC ITERATION MARK",
)
# Scripts that write their vowels as signs on a letter: such a sign counts as a
# character. Anywhere else a mark is an accent, which does not.
_VOWEL_SIGN_SCRIPTS = (
    "DEVANAGARI", "BENGALI", "GURMUKHI", "GUJARATI", "ORIYA", "TAMIL", "TELUGU",
    "KANNADA", "MALAYALAM", "SINHALA", "THAI", "LAO", "TIBETAN", "MYANMAR", "KHMER",
    "BALINESE", "JAVANESE", "SUNDANESE",
)


def display_name_skeleton(name: str) -> str:
    """What a name reads as: look-alike letters, accents, width, case, invisible
    characters and punctuation folded away, only ``a-z`` and ``0-9`` kept. The
    table runs before NFKD, between NFKD and casefold (the capitals NFKD brings out
    of mathematical or accented letters are still capitals there), and after
    casefold (decomposed letters such as Cyrillic yi, the capital palochka)."""
    folded = unicodedata.normalize("NFKD", (name or "").translate(_LOOKALIKES))
    folded = folded.translate(_LOOKALIKES).casefold().translate(_LOOKALIKES)
    kept = "".join(ch for ch in folded if "a" <= ch <= "z" or "0" <= ch <= "9")
    # Latin shapes a reader mixes up: I, l and 1 (once casefolded: i, l, 1), O and 0,
    # « rn » and « m ».
    return kept.replace("rn", "m").translate(_SAME_SHAPE)


def _visible(ch: str) -> bool:
    return unicodedata.category(ch) not in ("Mn", "Me", "Cf") and ord(ch) not in _BLANKS


def _ignorable(ch: str) -> bool:
    cp = ord(ch)
    return unicodedata.category(ch) == "Cf" or any(lo <= cp <= hi for lo, hi in _IGNORABLE_MARKS)


def display_name_key(name: str) -> str:
    """The same name whatever its case, width, composition or invisible marks."""
    return "".join(
        ch for ch in unicodedata.normalize("NFKC", name or "").casefold()
        if not _ignorable(ch) and ord(ch) not in _BLANKS
    )


def _emoji_ends_at(name: str, i: int) -> bool:
    """An emoji (So or Sk) ends at ``i``, past its style selector and skin tone."""
    while i >= 0 and (ord(name[i]) == _EMOJI_STYLE or ord(name[i]) in _SKIN_TONES):
        i -= 1
    return i >= 0 and unicodedata.category(name[i]) in ("So", "Sk")


def _shapes_text(name: str, i: int) -> bool:
    """An invisible character at ``i`` that changes the drawing: a joiner after a
    virama (RFC 5892, Indic half-forms), ZWNJ between two Arabic letters, ZWJ
    between two emoji, and the emoji style selector after an emoji or a keycap."""
    cp = ord(name[i])
    before = name[i - 1] if i else ""
    after = name[i + 1] if i + 1 < len(name) else ""
    if cp == _EMOJI_STYLE:
        keycap = bool(before) and before in "0123456789#*" and after == _KEYCAP
        return keycap or (bool(before) and _emoji_ends_at(name, i - 1))
    if cp not in (_ZWNJ, _ZWJ) or not before:
        return False
    if unicodedata.combining(before) == _VIRAMA_CLASS:
        return True
    if not after:
        return False
    if cp == _ZWNJ:
        return unicodedata.bidirectional(before) == unicodedata.bidirectional(after) == "AL"
    return _emoji_ends_at(name, i - 1) and unicodedata.category(after) in ("So", "Sk")


def _flag_tags(name: str) -> set[int]:
    """Positions of the tag letters and cancel tag of each subdivision flag
    (Scotland, England, Wales): black flag, tag letters, cancel tag."""
    allowed: set[int] = set()
    for start, ch in enumerate(name):
        if ord(ch) != _FLAG:
            continue
        end = start + 1
        while end < len(name) and ord(name[end]) in _TAG_LETTERS:
            end += 1
        if end > start + 1 and end < len(name) and ord(name[end]) == _CANCEL_TAG:
            allowed.update(range(start + 1, end + 1))
    return allowed


def hides_text(name: str) -> bool:
    """Characters that can make a name blank or show it as another one: controls,
    private-use and unassigned code points, line breaks, blank fillers, and every
    character Unicode draws as nothing (format characters, variation selectors),
    save where ``_shapes_text`` finds it shapes the text and in a subdivision flag."""
    flag_tags = _flag_tags(name)
    for i, ch in enumerate(name):
        if unicodedata.category(ch) in ("Cc", "Co", "Cn", "Zl", "Zp") or ord(ch) in _BLANKS:
            return True
        if _ignorable(ch) and i not in flag_tags and not _shapes_text(name, i):
            return True
    return False


def has_ink(name: str) -> bool:
    """At least one letter, digit or symbol to see."""
    return any(unicodedata.category(ch)[0] in "LNS" for ch in name if _visible(ch))


def _counts_its_marks(base: str) -> bool:
    return (
        bool(base) and unicodedata.category(base)[0] == "L"
        and unicodedata.name(base, "").startswith(_VOWEL_SIGN_SCRIPTS)
    )


def visible_length(name: str) -> int:
    """Characters a reader counts: letters, digits and symbols, plus one vowel sign
    per letter of a script that writes vowels as signs (Indic, Thai…). Spaces,
    punctuation, invisible characters and accents do not count."""
    count, base, marked = 0, "", False
    for ch in unicodedata.normalize("NFC", name):
        category = unicodedata.category(ch)
        if category[0] in "LNS" and _visible(ch):
            count, base, marked = count + 1, ch, False
        elif category in ("Mn", "Mc"):
            if not marked and _counts_its_marks(base) and not _ignorable(ch):
                count, marked = count + 1, True
        else:
            base = ""
    return count


def min_length(name: str) -> int:
    """Two characters for a name written in Chinese ideographs or Korean
    syllables, three otherwise."""
    composed = unicodedata.normalize("NFC", name)
    letters = [ch for ch in composed if unicodedata.category(ch)[0] == "L"]
    if letters and all(unicodedata.name(ch, "").startswith(_SYLLABIC) for ch in letters):
        return dn.MIN_LENGTH_SYLLABIC
    return dn.MIN_LENGTH
