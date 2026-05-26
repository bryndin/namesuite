# patronymic_inference.gpr.py
# ruff: noqa

register(
    TOOL,
    id="east_slavic_name_suite",
    name=_("Process East Slavic Names"),
    category=TOOL_DBPROC,  # Standard database processing category
    description=_("Suite for given name standardization and patronymic inference."),
    version="1.0",
    gramps_target_version="6.0",
    status=STABLE,
    fname="patronymics_tool.py",
    authors=["Dmitry Bryndin"],
    authors_email=["1129396+bryndin@users.noreply.github.com"],
    toolclass="EastSlavicNameTools",
    optionclass="EastSlavicNameToolsOptions",
)

register(
    GRAMPLET,
    id="infer_patronymics_gramplet",
    name=_("Patronymic Suggestion"),
    description=_("Suggests patronymic names in real-time as you navigate."),
    version="1.0",
    gramps_target_version="6.0",
    status=STABLE,
    fname="patronymics_gramplet.py",
    authors=["Dmitry Bryndin"],
    authors_email=["1129396+bryndin@users.noreply.github.com"],
    gramplet="InferPatronymicsGramplet",
    navtypes=["Person", "Relationship"],
    gramplet_title=_("Patronymic Suggestion"),
)
