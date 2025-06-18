"""React Agent.

This module defines a custom reasoning and action agent graph.
It invokes tools in a simple loop.
"""

from react_agent.graph import graph
from react_agent.gaia_runner import run_all_gaia_tasks

# V2 System
from react_agent.graph_v2 import tracked_graph
from react_agent.gaia_runner_v2 import CleanGAIARunner
from react_agent.state_v2 import GAIAInputState, GAIAInternalState, GAIAOutputState

# Convenience function for V2
from react_agent.run_gaia_benchmark_v2 import run_gaia_benchmark_v2

__all__ = [
    # V1 System
    "graph",
    "run_all_gaia_tasks",
    # Nuove esportazioni v2
    "tracked_graph",
    "CleanGAIARunner",
    "GAIAInputState",
    "GAIAInternalState",
    "GAIAOutputState",
    "run_gaia_benchmark_v2"
]
