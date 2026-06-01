# patronymic_inference.gpr.py
# ruff: noqa

register(
    TOOL,
    id="name_standardization_tool",
    name=_("Standardize Names"),
    category=TOOL_DBPROC,  # Standard database processing category
    description=_(
        "Suite for given name standardization and patronymic name inference."
    ),
    version="1.0",
    gramps_target_version="6.0",
    status=STABLE,
    fname="names_tool.py",
    authors=["Dmitry Bryndin"],
    authors_email=["1129396+bryndin@users.noreply.github.com"],
    toolclass="NamesTool",
    optionclass="NamesToolOptions",
)

register(
    GRAMPLET,
    id="patronymic_suggestion_gramplet",
    name=_("Patronymic Suggestion"),
    description=_("Suggests patronymic names in real-time as you navigate."),
    version="1.0",
    gramps_target_version="6.0",
    status=STABLE,
    fname="patronymics_gramplet.py",
    authors=["Dmitry Bryndin"],
    authors_email=["1129396+bryndin@users.noreply.github.com"],
    gramplet="PatronymicSuggestionGramplet",
    navtypes=["Person", "Relationship"],
    gramplet_title=_("Patronymic Suggestion"),
)
