from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

import networkx as nx

from .service import Service


class DependencyTracking(Service):
    """
    Track instances that are prerequisites for this instance.

    >>> setup = DependencyTracking.empty()
    >>> running = DependencyTracking(prerequisites=[setup])
    >>> teardown = DependencyTracking(prerequisites=[running])

    >>> setup.are_requirements_satisfied
    True
    >>> setup.notify(running)
    >>> running.are_requirements_satisfied
    True
    >>> teardown.acknowledge(running)
    >>> teardown.are_requirements_satisfied
    True

    >>> G = DependencyTracking.build_dependency_graph([setup, running, teardown], add_source=False, add_sink=False)
    >>> G.number_of_nodes()
    3
    >>> G.number_of_edges()
    2
    """

    _requirements: Dict[DependencyTracking, bool]

    @property
    def prerequisites(self) -> Iterable[DependencyTracking]:
        return self._requirements.keys()

    @property
    def are_requirements_satisfied(self) -> bool:
        return all(self._requirements.values())

    @classmethod
    def empty(cls, *args: Any, **kwargs: Any) -> DependencyTracking:
        return cls(*args, **kwargs)

    def __init__(
        self,
        *args: Any,
        prerequisites: Optional[Iterable[DependencyTracking]] = None,
        **kwargs: Any
    ):
        super().__init__(*args, **kwargs)
        self.__init_requirements(prerequisites)

    def __init_requirements(self, prerequisites: Optional[Iterable[DependencyTracking]]) -> None:
        self._requirements = dict()

        if prerequisites:
            for prerequisite in prerequisites:
                self.require(prerequisite)

    def require(self, prerequisite: DependencyTracking) -> None:
        """Add an instance as a prerequisite."""
        self._requirements[prerequisite] = False

    def acknowledge(self, prerequisite: DependencyTracking) -> None:
        """Acknowledge a prerequisite is satisfied."""
        self._requirements[prerequisite] = True

    def notify(self, dependent: DependencyTracking) -> None:
        """Notify a dependency that this instance as a prerequisite is satisfied."""
        dependent.acknowledge(self)

    @classmethod
    def build_dependency_graph(
        cls,
        dependency_nodes: Iterable[DependencyTracking],
        add_source: bool = True,
        add_sink: bool = True,
    ) -> nx.DiGraph:
        """
        Dependency Graph is a directed acyclic graph with edges from prerequisite to dependent.

        When `add_source` is True, there will be a empty dependency node that is prerequisite for every dependency nodes.
        When `add_sink` is True, there will be a empty dependency node that has every dependency nodes as prerequisite.
        """
        graph = nx.DiGraph()

        if add_source:
            source = cls.empty()
        if add_sink:
            sink = cls.empty()

        for dependency_node in dependency_nodes:
            if add_source:
                graph.add_edge(source, dependency_node)
            if add_sink:
                graph.add_edge(dependency_node, sink)

            for prerequisite in dependency_node.prerequisites:
                graph.add_edge(prerequisite, dependency_node)

        return graph


if __name__ == "__main__":
    import doctest

    doctest.testmod()
