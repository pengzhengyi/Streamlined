from typing import Any, Dict

from .component import PipelineComponent
from .component.capabilities import RunInNewScope
from .constants import PIPELINE
from .manager import Manager


class Pipeline(RunInNewScope):
    """
    Entry point for pipeline execution.
    """

    def __init__(self, pipeline_config: Dict[str, Any]):
        pipeline = PipelineComponent.of(pipeline_config)
        manager = Manager()
        run_action = lambda: self.__run(pipeline, manager)
        super().__init__(manager, run_action)

    def __run(self, pipeline: PipelineComponent, manager: Manager) -> Any:
        manager.set_magic_value(PIPELINE, value=self)
        return pipeline.execute(manager)
