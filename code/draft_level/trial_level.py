from level.item_level_base import ItemCollectionLevelBase

class TrialLevel(ItemCollectionLevelBase):
    def __init__(self, screen):
        # super().__init__(screen, map_path='map/map_Entities_trial.csv')
        screen.fill("blue")  # Clear the screen for the trial level
