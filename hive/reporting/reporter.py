from __future__ import annotations

from typing import Tuple
from abc import ABC, abstractmethod

from hive.state.simulation_state import SimulationState
from hive.dispatcher.instruction import Instruction


class Reporter(ABC):
    """
    A class that generates reports for the simulation.
    """

    @abstractmethod
    def report(self,
               sim_state: SimulationState,
               instructions: Tuple[Instruction, ...],
               reports: Tuple[str, ...]):
        """
        Takes in a simulation state and a tuple of instructions and writes the appropriate information.
        :param reports:
        :param sim_state:
        :param instructions:
        :return:
        """
        pass
