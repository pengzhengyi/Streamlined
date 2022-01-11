from streamlined import Template, TemplateParameter


def test_template_with_formatstr_names():
    template = Template(
        {
            TemplateParameter(name="{language}_name", annotation=str): TemplateParameter(
                name="hobby", annotation=str
            )
        }
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
