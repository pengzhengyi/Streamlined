from streamlined import Pipeline
from streamlined.component import (
    ExecutionComponent,
    PipelineComponent,
    RunstagesComponent,
    RunstepsComponent,
)
from streamlined.component.runstage_component import RunstageComponent
from streamlined.component.runstep_component import RunstepComponent


def test_simple_pipeline_component(minimum_manager):
    config = {
        PipelineComponent.NAME_KEYNAME: "basic arithmetic pipeline",
        RunstagesComponent.KEY_NAME: [
            {
                RunstageComponent.NAME_KEYNAME: "arithmetic",
                RunstepsComponent.KEY_NAME: [
                    {
                        RunstepComponent.NAME_KEYNAME: "1+1",
                        ExecutionComponent.KEY_NAME: lambda: 1 + 1,
                    }
                ],
            }
        ],
    }
    pipeline = Pipeline(config)
    result = pipeline.run()
    assert result == [[2]]
