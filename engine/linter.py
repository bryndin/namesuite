# -*- coding: utf-8 -*-
"""
engine/linter.py

Implementation of Phase 3 Quality & Consistency Auditing (The Linter) for Gramps.
Provides a validation engine, context models, dynamic rule registry, and
the standard linter ruleset.
"""

import re
import difflib
import functools
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Set, Tuple, List, Dict, Any, Callable

# Gramps dependency stubs/constants mapped from core or safely fallback
try:
    from gramps.gen.lib import Person
except ImportError:
    class Person:
        MALE = 0
        FEMALE = 1
        UNKNOWN = 2

from engine.morphology import (
    generate_east_slavic_patronymic,
    normalize_to_modern,
    apply_pre_reform_orthography
)

# Cyrillic and Latin Unicode blocks to detect homoglyph mixing
CYRILLIC_PATTERN = re.compile(r"[\u0400-\u04FF]")
LATIN_PATTERN = re.compile(r"[a-zA-Z]")

# Common Cyrillic-Latin homoglyph mapping dictionary
HOMOGLYPHS: Dict[str, str] = {
    'a': 'а', 'A': 'А',
    'c': 'с', 'C': 'С',
    'e': 'е', 'E': 'Е',
    'o': 'о', 'O': 'О',
    'p': 'р', 'P': 'Р',
    'x': 'х', 'X': 'Х',
    'y': 'у', 'Y': 'У',
    'H': 'Н', 'K': 'К',
    'M': 'М', 'T': 'Т',
    'B': 'В',
}


def pango_escape(text: str) -> str:
    """Escapes XML special characters to prevent GTK Pango parsing crashes."""
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def generate_pango_diff(old_str: str, new_str: str) -> str:
    """
    Generates a Pango markup diff showing additions in green and deletions in red.
    Example: Ивано<span foreground='red'><s>чи</s></span><span foreground='green'>на</span>
    """
    old_esc = pango_escape(old_str)
    new_esc = pango_escape(new_str)
    
    if not old_esc:
        return f"<span foreground='green'>{new_esc}</span>" if new_esc else ""
    if not new_esc:
        return f"<span foreground='red'><s>{old_esc}</s></span>" if old_esc else ""

    matcher = difflib.SequenceMatcher(None, old_str, new_str)
    markup_parts = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            markup_parts.append(pango_escape(old_str[i1:i2]))
        elif tag == 'replace':
            markup_parts.append(f"<span foreground='red'><s>{pango_escape(old_str[i1:i2])}</s></span>")
            markup_parts.append(f"<span foreground='green'>{pango_escape(new_str[j1:j2])}</span>")
        elif tag == 'delete':
            markup_parts.append(f"<span foreground='red'><s>{pango_escape(old_str[i1:i2])}</s></span>")
        elif tag == 'insert':
            markup_parts.append(f"<span foreground='green'>{pango_escape(new_str[j1:j2])}</span>")
            
    return "".join(markup_parts)


def swap_patronymic_gender(patronymic: str, to_male: bool, pre_reform: bool = False) -> str:
    """Swaps the grammatical gender of an existing patronymic suffix."""
    if not patronymic:
        return patronymic

    if to_male:
        # Female to Male
        if patronymic.endswith("инична"):
            return patronymic[:-6] + "ич"
        elif patronymic.endswith("ична"):
            return patronymic[:-4] + "ич"
        elif patronymic.endswith("овна"):
            return patronymic[:-4] + "ович"
        elif patronymic.endswith("евна"):
            return patronymic[:-4] + "евич"
        elif patronymic.endswith("ова"):
            return patronymic[:-3] + ("овъ" if pre_reform else "ов")
        elif patronymic.endswith("ева"):
            return patronymic[:-3] + ("евъ" if pre_reform else "ев")
        elif patronymic.endswith("ина"):
            return patronymic[:-3] + ("инъ" if pre_reform else "ин")
    else:
        # Male to Female
        if patronymic.endswith("ович"):
            return patronymic[:-4] + "овна"
        elif patronymic.endswith("евич"):
            return patronymic[:-4] + "евна"
        elif patronymic.endswith("ич"):
            # Check soft contracted stem (Илья -> Ильинична)
            base = patronymic[:-2]
            if base.endswith("ь") or base.lower() in ("иль", "кузьм", "фом"):
                return base + "инична"
            return base + "ична"
        elif patronymic.endswith("овъ"):
            return patronymic[:-3] + "ова"
        elif patronymic.endswith("евъ"):
            return patronymic[:-3] + "ева"
        elif patronymic.endswith("инъ"):
            return patronymic[:-3] + "ина"
        elif patronymic.endswith("ов"):
            return patronymic[:-2] + "ова"
        elif patronymic.endswith("ев"):
            return patronymic[:-2] + "ева"
        elif patronymic.endswith("ин"):
            return patronymic[:-2] + "ина"
            
    return patronymic


def modern_to_archaic(patronymic: str, is_male: bool, pre_reform: bool = False) -> str:
    """Converts a modern formal patronymic to an archaic possessive genitive."""
    if not patronymic:
        return patronymic

    if is_male:
        if patronymic.endswith("ович"):
            return patronymic[:-4] + ("овъ" if pre_reform else "ов")
        elif patronymic.endswith("евич"):
            return patronymic[:-4] + ("евъ" if pre_reform else "ев")
        elif patronymic.endswith("ич"):
            return patronymic[:-2] + ("инъ" if pre_reform else "ин")
    else:
        if patronymic.endswith("овна"):
            return patronymic[:-4] + "ова"
        elif patronymic.endswith("евна"):
            return patronymic[:-4] + "ева"
        elif patronymic.endswith("ична"):
            return patronymic[:-4] + "ина"
        elif patronymic.endswith("инична"):
            return patronymic[:-6] + "ина"
            
    return patronymic


def archaic_to_modern(patronymic: str, is_male: bool) -> str:
    """Converts an archaic possessive genitive to a modern formal patronymic."""
    if not patronymic:
        return patronymic

    # Strip terminal hard sign ъ
    pat = normalize_to_modern(patronymic)
    if is_male:
        if pat.endswith("ов"):
            return pat[:-2] + "ович"
        elif pat.endswith("ев"):
            return pat[:-2] + "евич"
        elif pat.endswith("ин"):
            return pat[:-2] + "ич"
    else:
        if pat.endswith("ова"):
            return pat[:-3] + "овна"
        elif pat.endswith("ева"):
            return pat[:-3] + "евна"
        elif pat.endswith("ина"):
            return pat[:-3] + "ична"
            
    return patronymic


class PlaceCache:
    """Session-scoped place cache. Instantiate per batch run to avoid memory leaks."""
    def __init__(self, db: Any):
        self.db = db

        @functools.lru_cache(maxsize=1024)
        def _get_places(person_handle: str) -> List[str]:
            places = []
            if not self.db or not person_handle:
                return places
            try:
                person = self.db.get_person_from_handle(person_handle)
                if person:
                    for event_ref in person.get_event_ref_list():
                        event = self.db.get_event_from_handle(event_ref.ref)
                        if event:
                            place_handle = event.get_place_handle()
                            if place_handle:
                                place = self.db.get_place_from_handle(place_handle)
                                if place:
                                    title = ""
                                    if hasattr(place, "get_title"):
                                        title = place.get_title()
                                    elif hasattr(place, "title"):
                                        title = place.title
                                    if title:
                                        places.append(title)
            except Exception:
                pass
            return places

        self.get_places = _get_places


@dataclass(frozen=True)
class RuleContext:
    """Frozen evaluation context for linter validation rules."""
    person_id: str
    current_patronymic: str
    father_given_name: str
    gramps_gender: int
    reference_year: int
    locale: str
    _place_resolver: Optional[Callable[[str], List[str]]] = None

    @property
    def place_context(self) -> List[str]:
        """Lazy-evaluated place list using the session-scoped cache."""
        if self._place_resolver:
            return self._place_resolver(self.person_id)
        return []


@dataclass
class ProposedChange:
    """Holds structural feedback and suggestions from the validation rule."""
    explanation: str
    suggested_string: str
    diff_markup: str


class BaseRule(ABC):
    """Abstract Base Class for all linter consistency rules."""
    
    @property
    @abstractmethod
    def rule_id(self) -> str:
        """Unique rule identifier (e.g. ERR_GENDER_MISMATCH)."""
        pass

    @property
    @abstractmethod
    def severity(self) -> str:
        """Rule severity: 'ERROR', 'WARNING', or 'INFO'."""
        pass

    @property
    @abstractmethod
    def supported_locales(self) -> Set[str]:
        """Set of supported locale ISO codes (e.g. {'ru', 'uk'} or {'*'} for universal)."""
        pass

    @property
    @abstractmethod
    def active_era(self) -> Tuple[Optional[int], Optional[int]]:
        """Active chronological window (start_year, end_year) this rule applies to."""
        pass

    @abstractmethod
    def evaluate(self, ctx: RuleContext) -> Optional[ProposedChange]:
        """
        Evaluates context. Returns None if rule passes, or a ProposedChange
        if consistency issues are detected.
        """
        pass


# =========================================================================
# Linter Ruleset Implementation
# =========================================================================

class ErrGenderMismatch(BaseRule):
    """Flags if the grammatical gender of the patronymic suffix conflicts with person's gender."""
    
    @property
    def rule_id(self) -> str:
        return "ERR_GENDER_MISMATCH"

    @property
    def severity(self) -> str:
        return "ERROR"

    @property
    def supported_locales(self) -> Set[str]:
        return {"ru", "uk", "be", "*"}

    @property
    def active_era(self) -> Tuple[Optional[int], Optional[int]]:
        return (None, None)

    def evaluate(self, ctx: RuleContext) -> Optional[ProposedChange]:
        if ctx.gramps_gender not in (Person.MALE, Person.FEMALE) or not ctx.current_patronymic:
            return None

        is_male = (ctx.gramps_gender == Person.MALE)
        
        # 1. Evaluate with father's name if present
        if ctx.father_given_name:
            pre_reform = (ctx.locale == 'ru' and ctx.reference_year < 1918)
            expected = generate_east_slavic_patronymic(
                ctx.father_given_name, is_male=is_male, year=ctx.reference_year, pre_reform_script=pre_reform
            )
            opposite = generate_east_slavic_patronymic(
                ctx.father_given_name, is_male=not is_male, year=ctx.reference_year, pre_reform_script=pre_reform
            )
            if ctx.current_patronymic == opposite and opposite != expected:
                return ProposedChange(
                    explanation=f"Linguistic gender mismatch: Patronymic is grammatically {'female' if is_male else 'male'} for a {'male' if is_male else 'female'} individual.",
                    suggested_string=expected,
                    diff_markup=generate_pango_diff(ctx.current_patronymic, expected)
                )

        # 2. Universal fallback using suffix endings
        female_endings = ("овна", "евна", "ична", "инична", "ова", "ева", "ина")
        male_endings = ("ович", "евич", "ич", "ов", "ев", "ин", "овъ", "евъ", "инъ")
        
        if is_male:
            if ctx.current_patronymic.endswith(female_endings):
                pre_reform = (ctx.locale == 'ru' and ctx.reference_year < 1918)
                suggested = swap_patronymic_gender(ctx.current_patronymic, to_male=True, pre_reform=pre_reform)
                return ProposedChange(
                    explanation="Linguistic gender mismatch: Suffix is grammatically female for a male individual.",
                    suggested_string=suggested,
                    diff_markup=generate_pango_diff(ctx.current_patronymic, suggested)
                )
        else:
            if ctx.current_patronymic.endswith(male_endings):
                suggested = swap_patronymic_gender(ctx.current_patronymic, to_male=False)
                return ProposedChange(
                    explanation="Linguistic gender mismatch: Suffix is grammatically male for a female individual.",
                    suggested_string=suggested,
                    diff_markup=generate_pango_diff(ctx.current_patronymic, suggested)
                )

        return None


class ErrLineageMismatch(BaseRule):
    """Flags if the patronymic base/root does not match the linked biological father's name."""
    
    @property
    def rule_id(self) -> str:
        return "ERR_LINEAGE_MISMATCH"

    @property
    def severity(self) -> str:
        return "ERROR"

    @property
    def supported_locales(self) -> Set[str]:
        return {"ru", "uk", "be", "*"}

    @property
    def active_era(self) -> Tuple[Optional[int], Optional[int]]:
        return (None, None)

    def evaluate(self, ctx: RuleContext) -> Optional[ProposedChange]:
        if not ctx.father_given_name or not ctx.current_patronymic:
            return None

        is_male = (ctx.gramps_gender == Person.MALE)
        pre_reform = (ctx.locale == 'ru' and ctx.reference_year < 1918)
        
        # Resolve target expected patronymic for active context
        expected = generate_east_slavic_patronymic(
            ctx.father_given_name, is_male=is_male, year=ctx.reference_year, pre_reform_script=pre_reform
        )

        if not expected or ctx.current_patronymic == expected:
            return None

        # Cross-reference pre-1918 and post-1918 variant states to avoid flagging anachronisms as lineage mismatch
        expected_modern = generate_east_slavic_patronymic(ctx.father_given_name, is_male=is_male, year=1950, pre_reform_script=False)
        expected_archaic = generate_east_slavic_patronymic(ctx.father_given_name, is_male=is_male, year=1850, pre_reform_script=(ctx.locale == 'ru'))
        
        opposite_modern = generate_east_slavic_patronymic(ctx.father_given_name, is_male=not is_male, year=1950, pre_reform_script=False)
        opposite_archaic = generate_east_slavic_patronymic(ctx.father_given_name, is_male=not is_male, year=1850, pre_reform_script=(ctx.locale == 'ru'))

        # If it matches the opposite gender expected base, route it to ERR_GENDER_MISMATCH instead
        if ctx.current_patronymic in (opposite_modern, opposite_archaic):
            return None

        # If the patronymic is already matches one of our expected era variants, skip (let the era warning handle it)
        if ctx.current_patronymic in (expected_modern, expected_archaic):
            return None

        return ProposedChange(
            explanation=f"Lineage mismatch: The patronymic does not match father's given name '{ctx.father_given_name}'.",
            suggested_string=expected,
            diff_markup=generate_pango_diff(ctx.current_patronymic, expected)
        )


class WarnModernSuffixArchaicEra(BaseRule):
    """Flags pre-1918 records using modern formal endings and suggests possessive genitives."""
    
    @property
    def rule_id(self) -> str:
        return "WARN_MODERN_SUFFIX_ARCHAIC_ERA"

    @property
    def severity(self) -> str:
        return "WARNING"

    @property
    def supported_locales(self) -> Set[str]:
        return {"ru", "uk", "be", "*"}

    @property
    def active_era(self) -> Tuple[Optional[int], Optional[int]]:
        return (None, 1917)

    def evaluate(self, ctx: RuleContext) -> Optional[ProposedChange]:
        if not ctx.current_patronymic or ctx.reference_year >= 1918:
            return None

        modern_suffixes = ("ович", "евич", "ич", "овна", "евна", "ична", "инична")
        
        if any(ctx.current_patronymic.endswith(s) for s in modern_suffixes):
            is_male = (ctx.gramps_gender == Person.MALE)
            pre_reform = (ctx.locale == 'ru')
            
            if ctx.father_given_name:
                suggested = generate_east_slavic_patronymic(
                    ctx.father_given_name, is_male=is_male, year=1850, pre_reform_script=pre_reform
                )
            else:
                suggested = modern_to_archaic(ctx.current_patronymic, is_male=is_male, pre_reform=pre_reform)

            if suggested and suggested != ctx.current_patronymic:
                return ProposedChange(
                    explanation=f"Historical anachronism: Modern patronymic suffix in pre-1918 era ({ctx.reference_year}).",
                    suggested_string=suggested,
                    diff_markup=generate_pango_diff(ctx.current_patronymic, suggested)
                )

        return None


class WarnArchaicSuffixModernEra(BaseRule):
    """Flags post-1918 records using archaic/informal possessive endings."""
    
    @property
    def rule_id(self) -> str:
        return "WARN_ARCHAIC_SUFFIX_MODERN_ERA"

    @property
    def severity(self) -> str:
        return "WARNING"

    @property
    def supported_locales(self) -> Set[str]:
        return {"ru", "uk", "be", "*"}

    @property
    def active_era(self) -> Tuple[Optional[int], Optional[int]]:
        return (1918, None)

    def evaluate(self, ctx: RuleContext) -> Optional[ProposedChange]:
        if not ctx.current_patronymic or ctx.reference_year < 1918:
            return None

        # Archaic endings (including pre-reform orthographic variants)
        archaic_suffixes = ("ов", "ев", "ин", "ова", "ева", "ина", "овъ", "евъ", "инъ")
        
        if any(ctx.current_patronymic.endswith(s) for s in archaic_suffixes):
            is_male = (ctx.gramps_gender == Person.MALE)
            
            if ctx.father_given_name:
                suggested = generate_east_slavic_patronymic(
                    ctx.father_given_name, is_male=is_male, year=1950, pre_reform_script=False
                )
            else:
                suggested = archaic_to_modern(ctx.current_patronymic, is_male=is_male)

            if suggested and suggested != ctx.current_patronymic:
                return ProposedChange(
                    explanation=f"Historical anachronism: Archaic genitive suffix in post-1918 era ({ctx.reference_year}).",
                    suggested_string=suggested,
                    diff_markup=generate_pango_diff(ctx.current_patronymic, suggested)
                )

        return None


class ErrMixedScripts(BaseRule):
    """Detects and corrects mixed Cyrillic and Latin homoglyphs in patronymic strings."""
    
    @property
    def rule_id(self) -> str:
        return "ERR_MIXED_SCRIPTS"

    @property
    def severity(self) -> str:
        return "ERROR"

    @property
    def supported_locales(self) -> Set[str]:
        return {"*"}

    @property
    def active_era(self) -> Tuple[Optional[int], Optional[int]]:
        return (None, None)

    def evaluate(self, ctx: RuleContext) -> Optional[ProposedChange]:
        if not ctx.current_patronymic:
            return None

        has_cyr = bool(CYRILLIC_PATTERN.search(ctx.current_patronymic))
        has_lat = bool(LATIN_PATTERN.search(ctx.current_patronymic))
        
        if has_cyr and has_lat:
            # Map Latin characters to Cyrillic homoglyphs
            chars = []
            for char in ctx.current_patronymic:
                chars.append(HOMOGLYPHS.get(char, char))
            suggested = "".join(chars)
            
            if suggested != ctx.current_patronymic:
                return ProposedChange(
                    explanation="Typographical error: Contains a mixture of Cyrillic and Latin homoglyph Unicode characters.",
                    suggested_string=suggested,
                    diff_markup=generate_pango_diff(ctx.current_patronymic, suggested)
                )

        return None


class WarnMorphologicalTypo(BaseRule):
    """Detects invalid consecutive duplicate characters at joint boundaries (e.g. Андрееевич)."""
    
    @property
    def rule_id(self) -> str:
        return "WARN_MORPHOLOGICAL_TYPO"

    @property
    def severity(self) -> str:
        return "WARNING"

    @property
    def supported_locales(self) -> Set[str]:
        return {"ru", "uk", "be", "*"}

    @property
    def active_era(self) -> Tuple[Optional[int], Optional[int]]:
        return (None, None)

    def evaluate(self, ctx: RuleContext) -> Optional[ProposedChange]:
        if not ctx.current_patronymic:
            return None

        # 1. Typo checks on raw string (e.g. 3 consecutive identical letters like "еее")
        if re.search(r"(.)\1\1+", ctx.current_patronymic):
            # Compress consecutive duplicates to help suggest correction
            suggested = re.sub(r"(.)\1\1+", r"\1", ctx.current_patronymic)
            # Re-generate from father's name if present for maximum accuracy
            if ctx.father_given_name:
                is_male = (ctx.gramps_gender == Person.MALE)
                pre_reform = (ctx.locale == 'ru' and ctx.reference_year < 1918)
                gen_expected = generate_east_slavic_patronymic(
                    ctx.father_given_name, is_male=is_male, year=ctx.reference_year, pre_reform_script=pre_reform
                )
                if gen_expected:
                    suggested = gen_expected

            if suggested != ctx.current_patronymic:
                return ProposedChange(
                    explanation="Spelling anomaly: Contains invalid duplicate letter repetitions at morphological boundaries.",
                    suggested_string=suggested,
                    diff_markup=generate_pango_diff(ctx.current_patronymic, suggested)
                )

        # 2. Check if a duplicate letter differs only from morphological standard
        if ctx.father_given_name:
            is_male = (ctx.gramps_gender == Person.MALE)
            pre_reform = (ctx.locale == 'ru' and ctx.reference_year < 1918)
            expected = generate_east_slavic_patronymic(
                ctx.father_given_name, is_male=is_male, year=ctx.reference_year, pre_reform_script=pre_reform
            )
            if expected and ctx.current_patronymic != expected:
                # Check if they are identical after stripping consecutive repeats
                def compress(s: str) -> str:
                    return re.sub(r"(.)\1+", r"\1", s)
                
                if compress(ctx.current_patronymic) == compress(expected):
                    return ProposedChange(
                        explanation="Spelling anomaly: Joint spelling differs from standard naming morphology.",
                        suggested_string=expected,
                        diff_markup=generate_pango_diff(ctx.current_patronymic, expected)
                    )

        return None


class WarnMissingHardSign(BaseRule):
    """Flags pre-1918 Russian names missing a terminal orthographic hard sign 'ъ'."""
    
    @property
    def rule_id(self) -> str:
        return "WARN_MISSING_HARD_SIGN"

    @property
    def severity(self) -> str:
        return "WARNING"

    @property
    def supported_locales(self) -> Set[str]:
        return {"ru"}

    @property
    def active_era(self) -> Tuple[Optional[int], Optional[int]]:
        return (None, 1917)

    def evaluate(self, ctx: RuleContext) -> Optional[ProposedChange]:
        if not ctx.current_patronymic or ctx.reference_year >= 1918 or ctx.locale != 'ru':
            return None

        # Re-apply pre-reform orthography mapping on the current value
        reformed = apply_pre_reform_orthography(ctx.current_patronymic)
        
        if reformed != ctx.current_patronymic:
            return ProposedChange(
                explanation="Orthographical anomaly: Missing historical pre-revolutionary terminal hard signs (ъ) or decimal (і).",
                suggested_string=reformed,
                diff_markup=generate_pango_diff(ctx.current_patronymic, reformed)
            )

        return None


# =========================================================================
# The Dispatcher Engine
# =========================================================================

class RuleEngine:
    """Dispatches evaluation rules dynamically over target person records."""
    
    def __init__(self, rules: Optional[List[BaseRule]] = None):
        """Indexes registered rules."""
        if rules is None:
            # Dynamically discover and load all subclasses of BaseRule
            self.rules = [
                ErrGenderMismatch(),
                ErrLineageMismatch(),
                WarnModernSuffixArchaicEra(),
                WarnArchaicSuffixModernEra(),
                ErrMixedScripts(),
                WarnMorphologicalTypo(),
                WarnMissingHardSign(),
            ]
        else:
            self.rules = rules

    def evaluate_person(self, ctx: RuleContext, enabled_rules: Optional[Set[str]] = None) -> List[Tuple[BaseRule, ProposedChange]]:
        """
        Evaluates a single Person context against all applicable rules.
        Includes graceful degradation to ensure that single-rule failures
        do not crash the process.
        """
        triggered = []
        for rule in self.rules:
            # 1. Check if the rule is enabled
            if enabled_rules is not None and rule.rule_id not in enabled_rules:
                continue

            # 2. Match locale
            if rule.supported_locales != {"*"} and ctx.locale not in rule.supported_locales:
                continue

            # 3. Match era bounds
            start, end = rule.active_era
            if start is not None and ctx.reference_year < start:
                continue
            if end is not None and ctx.reference_year > end:
                continue

            # 4. Evaluate with safe crash protection
            try:
                change = rule.evaluate(ctx)
                if change:
                    triggered.append((rule, change))
            except Exception as e:
                # Log or print the issue to ensure graceful continuation
                print(f"[Linter Error] Rule '{rule.rule_id}' failed on '{ctx.person_id}': {e}")
                
        return triggered
