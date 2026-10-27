from level.item_level_base import ItemCollectionLevelBase

class Level1(ItemCollectionLevelBase):
    def __init__(self, screen):
        super().__init__(screen, map_path='map/map_Entities_level1.csv')
        screen.fill("red")
