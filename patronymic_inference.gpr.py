# patronymic_inference.gpr.py

register(TOOL,
    id='infer_patronymics_tool',
    name=_("Infer East Slavic Patronymics..."),
    category=TOOL_DBPROC,  # Standard database processing category
    description=_("Automatically infers patronymic names from fathers' names."),
    version='1.0',
    gramps_target_version='6.0',
    status=STABLE,
    fname='patronymics_tool.py',
    authors=["Your Name"],
    authors_email=["your.email@example.com"],
    toolclass='InferPatronymicsTool',
    optionclass='InferPatronymicsOptions'
)

register(GRAMPLET,
    id='infer_patronymics_gramplet',
    name=_("Patronymic Suggestion"),
    description=_("Suggests patronymic names in real-time as you navigate."),
    version='1.0',
    gramps_target_version='6.0',
    status=STABLE,
    fname='patronymics_gramplet.py',
    gramplet='InferPatronymicsGramplet',
    navtypes=["Person", "Relationship"],
    gramplet_title=_("Patronymic Suggestion")
)