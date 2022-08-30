from dataclasses import dataclass

from mc_server_interaction.server_manger import game_constants


@dataclass
class WorldGenerationSettings:
    level_seed: str = ""
    level_type: str = game_constants.LevelTypes.DEFAULT
    generate_structures: bool = False
    world_name: str = "worlds/world"

    def __iter__(self):
        return iter([
            ("level-seed", self.level_seed),
            ("level-type", self.level_type),
            ("generate-structures", self.generate_structures),
            ("world-name", self.world_name)
        ])