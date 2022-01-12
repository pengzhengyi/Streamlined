from streamlined import Template, TemplateParameter, TemplateParameterDefault


def test_template_with_formatstr_names():
    template = Template(
        {TemplateParameter(name="{language}_name"): TemplateParameter(name="hobby")}
    )

    chinese_result = template.substitute(
        {"hobby": "singing", "chinese_name": "周杰伦"}, name_substitutions={"language": "chinese"}
    )
    assert chinese_result["周杰伦"] == "singing"

    english_result = template.substitute(
        {"hobby": "singing", "english_name": "Jay Chou"},
        name_substitutions={"language": "english"},
    )
    assert english_result["Jay Chou"] == "singing"


def test_template_with_explicit_default():
    template = Template(TemplateParameter(name="profit_for_{thing}s", default=0))
    with_value = template.substitute({"profit_for_toys": 100}, name_substitutions={"thing": "toy"})
    assert with_value == 100
    without_value = template.substitute(name_substitutions={"thing": "toy"})
    assert without_value == 0


def test_template_with_name_as_default():
    template = Template(
        TemplateParameter(name="{thing}s", default=TemplateParameterDefault.USE_NAME)
    )
    value = template.substitute(name_substitutions={"thing": "toy"})
    assert value == "toys"
