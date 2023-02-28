# explanations.py

"""Format localized explanations for erroneous acts found classified as such by reasoner"""

from collections import defaultdict
from configparser import ConfigParser, Interpolation
from pathlib import Path
import re

from common_helpers import camelcase_to_snakecase


# from owlready2 import *

from trace_gen.json2alg2tr import get_target_lang
from onto_helpers import get_relation_object, get_relation_subject


MESSAGES_FILE = "jena/control-flow-statements-domain-messages.txt"

PROPERTIES_LOCALIZATION_FILES = {
    'en': r'../locales/control-flow-messages_en.properties',
    'ru': r'../locales/control-flow-messages_ru.properties',
}
PROPERTIES_COMMON_PREFIX = 'ctrlflow_'
# LOCALE_KEY_MARK = "!{locale:"
LOCALE_KEY_RE = re.compile("!{locale:(.+?)}")


class LocalizationProvider:
    """Java Spring-like translations provider that loads compatible .properties files with localizations
    (interpolation is not supported)"""

    def __init__(self, prop_file_paths=()):
        self.loc2path = dict(prop_file_paths)
        self.loaded = {}

    def get(self, key: str, lang: str, default=None):
        if lang not in self.loaded:
            self.load_lang(lang)
        # return self.loaded[lang].get(key, default)
        return self.loaded[lang][key.lower()]

    def load_lang(self, lang):
        if lang not in self.loc2path:
            raise KeyError('Cannot load language with code "%s"' % lang)
        path = self.loc2path[lang]
        data = read_properties_file(path, cut_key_prefix=PROPERTIES_COMMON_PREFIX)

        self.loaded[lang] = data


locale = LocalizationProvider(PROPERTIES_LOCALIZATION_FILES)


def tr(key: str, lang: str = None, default=None):
    """Get translation for current locale"""
    return locale.get(key, lang or get_target_lang(), default)


def get_executes(act, *_):
    """Follow two relations: `act` -> `executes` -> `boundary_of` -> a `statement` and return the `statement`."""
    onto = act.namespace
    boundary = get_relation_object(act, onto.executes)
    return get_relation_object(boundary, onto.boundary_of)


def get_base_classes(classes) -> set:
    """Find subset of given `classes` that have no ancestors"""
    return {sup for cl in classes for sup in cl.is_a}


def get_leaf_classes(classes) -> set:
    """Find subset of given `classes` that have no children"""
    return set(classes) - get_base_classes(classes)


def class_name_to_readable(s):
    """Convert CamelCase words to hyphen-separated capitalized collocations."""
    sep = " "
    res = s.replace("-", sep)
    if res == s:
        res = camelcase_to_snakecase(s, sep).capitalize()
    return res


def format_explanation(current_onto, act_instance, _auto_register=True) -> list:
    """Format explanations about any error types attached to the act_instance
    by extracting required info from the ontology and filling in the template.
    """

    onto = current_onto

    error_classes = set(act_instance.is_a) & set(onto.Erroneous.descendants())
    error_classes = get_leaf_classes(error_classes)
    result = []

    for error_class in error_classes:
        class_name = error_class.name
        format_str = locale.get(class_name, get_target_lang(), None) or locale.get(class_name, "en", '__')
        if format_str:
            params = named_fields_param_provider(act_instance)
            expl = format_by_spec(
                format_str,
                **params
            )
            class_name_readable = class_name_to_readable(class_name)
            explanation = {
                "names": class_name_readable,
                "explanation": expl,
            }
            result.append(explanation)
            ###
            print("++ done: explanation for: ", class_name)
        else:
            print("<> !! Skipping explanation for: <>", class_name, "<>")


    return result

def capitalize_first_letter(s: str) -> str:
    """Bring first letter (skipping leading spaces and punctuation) to upper case"""
    # replace first letter ever if 's' starts with quote ('"')
    return re.subn(r'\w', lambda m:m[0].upper(), s, count=1)[0]  # take [0] from (str, count_replaced)


def format_by_spec(format_str: str, **params: dict):
    """Simple replace with `str.format` & add closing dot if needed"""
    format_str = format_str.format(**params)

    if not format_str.endswith('.') and not format_str.endswith('?'):
        format_str += '.'

    return capitalize_first_letter(format_str)


def named_fields_param_provider(a: 'act_instance', **options):
    """extract ALL field_* facts, no matter what law they belong to."""

    onto = a.namespace
    # for lookup
    begin_of = onto.begin_of
    end_of   = onto.end_of
    halt_of  = onto.halt_of
    atom_action = onto.atom_action

    lang = options.get("lang", None)

    placeholders = defaultdict(dict)  # {fieldname -> {value_to_quote -> prefix}} ; prefix is the phase: `begin of` / `end of`

    def add2placeholders(fieldName, to_quote, prefix):
        to_quote = replaceLocaleMarks(to_quote, lang)
        old_prefix = placeholders[fieldName].get(to_quote, None)
        # replace empty values only
        if old_prefix is None or prefix > old_prefix:    ### replace and
            placeholders[fieldName][to_quote] = prefix

    for prop in a.get_properties():
        verb = prop.python_name
        if verb.startswith("field_"):  # признак того, что это специальное свойство [act >> str] или [act >> bound]
            to_quote = None
            prefix = ''
            fieldName = verb.replace("field_", "")
            if fieldName.endswith("_bound"):
                # process bound instances ...
                # if 'phase' not in options:
                #   continue
                fieldName = fieldName[:-len("_bound")]
                for bound in prop[a]:
                    # extract phase to prepend to action name
                    phase_str = ''
                    # action class has 'atom_action' annotation = true
                    if not any(atom_action[cls] for cls in bound.boundary_of.is_a):
                    # if not (atom_action[action_class] or all(atom_action[action_class])):
                        # complex action, determine phase_str
                        if begin_of[bound]:
                            phase_str = tr("phase.begin_of", lang=lang) + " "
                        elif end_of[bound] or halt_of[bound]:
                            phase_str = tr("phase.end_of", lang=lang) + " "

                    name = bound.boundary_of.stmt_name
                    # add2placeholders(fieldName, to_quote=name, prefix=phase_str, replace=False)
                    # add 'phased-' version of placeholder
                    add2placeholders('phased-' + fieldName, to_quote=name, prefix=phase_str)
            else:
                # process literals ...
                for value in prop[a]:
                    # convert to str
                    value = {
                        True: 'true',
                        False: 'false',
                    }.get(value, str(value))
                    add2placeholders(fieldName, to_quote=value, prefix='')


    # convert sub-dicts to normal strings
    placeholders = {
        fieldName: ", ".join("«" + prefix + to_quote + "»" for to_quote, prefix in subd.items())
        for fieldName, subd in placeholders.items()
    }

    return placeholders


def replaceLocaleMarks(s, lang):
    """Replace all "!{locale:SOMEKEY}" fragments with result of passing 'SOMEKEY' into `tr` for given language """
    replace_lambda = lambda m: tr(m[1], lang, m[1])
    return LOCALE_KEY_RE.sub(replace_lambda, s)


def read_properties_file(file_path, delimiters='=', cut_key_prefix=None, replacements={r'\:': ':', '${': '{'}):
    """ use INI files reader to parse Java properties files.
    All keys will be forced lowercase (I guess it cannot be configured in ConfigParser)
    """
    p = Path(file_path)
    section_name = p.name
    with open(p) as f:
        # insert absent [ini section] required for parser; use file name to make error message more informative
        config_string = f'[{section_name}]\n' + f.read()

    for needle, replacement in replacements.items():
        config_string = config_string.replace(needle, replacement)

    config = ConfigParser(delimiters=delimiters, interpolation=Interpolation())
    config.read_string(config_string)
    data = dict(config[section_name])
    if cut_key_prefix and isinstance(cut_key_prefix, str):
        L = len(cut_key_prefix)
        data = {(k[L:] if k.startswith(cut_key_prefix) else k): v for k, v in data.items()}

    return data

