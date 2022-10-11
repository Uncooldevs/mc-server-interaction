from dataclasses import dataclass

from mc_server_interaction.utils import game_constants


@dataclass
class WorldGenerationSettings:
    level_seed: str = ""
    level_type: str = game_constants.LevelTypes.DEFAULT
    generate_structures: bool = False

    def __iter__(self):
        return iter(
            [
                ("level-seed", self.level_seed),
                ("level-type", self.level_type),
                ("generate-structures", self.generate_structures),
            ]
        )
