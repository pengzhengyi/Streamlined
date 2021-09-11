from dataclasses import dataclass

from streamlined.utils import ConfigurationLoader


@dataclass
class TestConfig(ConfigurationLoader):
    foo: str


def test_configuration_loader(tmp_path):
    config_filepath = tmp_path.joinpath("test.ini")

    config_filepath.write_text(
        """
[DEFAULT]
foo=Hey Jude
"""
    )

    # breakpoint()
    config = TestConfig.from_config_file(config_filepath)
    assert config.foo == "Hey Jude"
