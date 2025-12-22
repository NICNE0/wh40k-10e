"""
Terrain and Deployment Manager
Loads official 40k terrain layouts and deployment maps
"""

import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from battle_simulator import TerrainFeature, Terrain, Position, Objective


@dataclass
class DeploymentZone:
    """Deployment zone boundaries"""
    name: str
    shape: str  # 'rectangle', 'triangle', 'compound'
    bounds: Dict
    description: str

    def is_valid_deployment(self, pos: Position) -> bool:
        """Check if position is within deployment zone"""
        if self.shape == 'rectangle':
            bounds = self.bounds
            return (bounds['x_min'] <= pos.x <= bounds['x_max'] and
                    bounds['y_min'] <= pos.y <= bounds['y_max'])

        elif self.shape == 'triangle':
            # Simplified: use radius from center point
            if 'center' in self.bounds and 'radius' in self.bounds:
                center = Position(self.bounds['center'][0], self.bounds['center'][1])
                return pos.distance_to(center) <= self.bounds['radius']
            return False

        elif self.shape == 'compound':
            # Check if in any of the rectangles
            for rect in self.bounds.get('rectangles', []):
                if (rect['x_min'] <= pos.x <= rect['x_max'] and
                    rect['y_min'] <= pos.y <= rect['y_max']):
                    return True
            return False

        return False


class TerrainManager:
    """Manages terrain layouts and deployment maps"""

    def __init__(self, base_path: Optional[Path] = None):
        if base_path is None:
            base_path = Path(__file__).parent

        self.base_path = base_path
        self.terrain_layouts = self._load_terrain_layouts()
        self.deployment_maps = self._load_deployment_maps()

    def _load_terrain_layouts(self) -> Dict:
        """Load terrain layouts from JSON"""
        terrain_file = self.base_path / "terrain_layouts.json"
        with open(terrain_file, 'r') as f:
            return json.load(f)

    def _load_deployment_maps(self) -> Dict:
        """Load deployment maps from JSON"""
        deploy_file = self.base_path / "deployment_maps.json"
        with open(deploy_file, 'r') as f:
            return json.load(f)

    def get_terrain_layout(self, layout_name: str) -> List[TerrainFeature]:
        """
        Get terrain features for a specific layout

        Args:
            layout_name: e.g. 'layout_1', 'layout_2', etc.

        Returns:
            List of TerrainFeature objects
        """
        if layout_name not in self.terrain_layouts['layouts']:
            raise ValueError(f"Unknown terrain layout: {layout_name}")

        layout_data = self.terrain_layouts['layouts'][layout_name]
        terrain_pieces = []

        for piece_data in layout_data['pieces']:
            # Get piece dimensions
            piece_type = piece_data['type']
            dimensions = self.terrain_layouts['terrain_piece_types'][piece_type]

            # Map terrain type to Terrain enum
            terrain_type_map = {
                'ruins': Terrain.HEAVY_COVER if piece_data.get('obscuring', False) else Terrain.LIGHT_COVER,
                'craters': Terrain.LIGHT_COVER,
                'woods': Terrain.LIGHT_COVER
            }

            terrain_enum = terrain_type_map.get(piece_data['terrain_type'], Terrain.LIGHT_COVER)

            # Determine if obscuring (blocks LOS)
            blocks_los = piece_data.get('obscuring', False)

            # Create terrain feature with rectangle dimensions
            feature = TerrainFeature(
                name=f"{piece_data['terrain_type'].title()}-{len(terrain_pieces)+1}",
                terrain_type=terrain_enum,
                center=Position(piece_data['position'][0], piece_data['position'][1]),
                width=dimensions['width'],
                length=dimensions['length'],
                rotation=piece_data.get('rotation', 0),
                height=piece_data.get('height', dimensions.get('typical_height', 0)),
                provides_cover=terrain_enum in [Terrain.LIGHT_COVER, Terrain.HEAVY_COVER],
                blocks_los=blocks_los
            )

            terrain_pieces.append(feature)

        return terrain_pieces

    def get_deployment_map(self, map_name: str) -> Tuple[DeploymentZone, DeploymentZone]:
        """
        Get deployment zones for a specific map

        Args:
            map_name: e.g. 'hammer_and_anvil', 'dawn_of_war', etc.

        Returns:
            Tuple of (player_1_zone, player_2_zone)
        """
        if map_name not in self.deployment_maps['deployment_maps']:
            raise ValueError(f"Unknown deployment map: {map_name}")

        map_data = self.deployment_maps['deployment_maps'][map_name]

        p1_data = map_data['player_1_zone']
        p2_data = map_data['player_2_zone']

        # Handle simplified bounds for diagonal deployments
        if 'simplified_bounds' in map_data:
            p1_bounds = map_data['simplified_bounds']['player_1']
            p2_bounds = map_data['simplified_bounds']['player_2']

            p1_zone = DeploymentZone(
                name=f"{map_data['name']} - Player 1",
                shape='triangle',
                bounds=p1_bounds,
                description=p1_data['description']
            )

            p2_zone = DeploymentZone(
                name=f"{map_data['name']} - Player 2",
                shape='triangle',
                bounds=p2_bounds,
                description=p2_data['description']
            )
        else:
            p1_zone = DeploymentZone(
                name=f"{map_data['name']} - Player 1",
                shape=p1_data['shape'],
                bounds=p1_data['bounds'],
                description=p1_data['description']
            )

            p2_zone = DeploymentZone(
                name=f"{map_data['name']} - Player 2",
                shape=p2_data['shape'],
                bounds=p2_data['bounds'],
                description=p2_data['description']
            )

        return p1_zone, p2_zone

    def get_objectives(self, objective_set: str) -> List[Objective]:
        """
        Get objective markers for a specific placement pattern

        Args:
            objective_set: e.g. 'standard_5_objectives', 'diagonal_5_objectives', etc.

        Returns:
            List of Objective objects
        """
        if objective_set not in self.deployment_maps['objective_placements']:
            raise ValueError(f"Unknown objective set: {objective_set}")

        obj_data = self.deployment_maps['objective_placements'][objective_set]
        objectives = []

        for obj in obj_data['objectives']:
            objectives.append(Objective(
                name=obj.get('id', f"Obj-{len(objectives)+1}"),
                position=Position(obj['position'][0], obj['position'][1]),
                value=obj.get('value', 5),
                controlled_by=None
            ))

        return objectives

    def get_random_valid_deployment_position(self, zone: DeploymentZone,
                                            avoid_terrain: List[TerrainFeature] = None) -> Position:
        """
        Get a random valid position within a deployment zone

        Args:
            zone: DeploymentZone to deploy in
            avoid_terrain: Optional list of terrain to avoid

        Returns:
            Valid Position within the zone
        """
        import numpy as np

        max_attempts = 100
        for _ in range(max_attempts):
            if zone.shape == 'rectangle':
                bounds = zone.bounds
                x = np.random.uniform(bounds['x_min'] + 1, bounds['x_max'] - 1)
                y = np.random.uniform(bounds['y_min'] + 1, bounds['y_max'] - 1)
                pos = Position(x, y)

            elif zone.shape == 'triangle' and 'center' in zone.bounds:
                # Random position within radius of center
                center = zone.bounds['center']
                radius = zone.bounds['radius']
                angle = np.random.uniform(0, 2 * np.pi)
                dist = np.random.uniform(0, radius - 2)
                x = center[0] + dist * np.cos(angle)
                y = center[1] + dist * np.sin(angle)
                pos = Position(x, y)

            elif zone.shape == 'compound':
                # Pick random rectangle from compound shape
                rectangles = zone.bounds.get('rectangles', [])
                if not rectangles:
                    continue
                rect = np.random.choice(rectangles)
                x = np.random.uniform(rect['x_min'] + 1, rect['x_max'] - 1)
                y = np.random.uniform(rect['y_min'] + 1, rect['y_max'] - 1)
                pos = Position(x, y)

            else:
                continue

            # Check if valid and not in terrain
            if not zone.is_valid_deployment(pos):
                continue

            # Check terrain avoidance
            if avoid_terrain:
                too_close = False
                for terrain in avoid_terrain:
                    if pos.distance_to(terrain.center) < terrain.radius + 2:
                        too_close = True
                        break
                if too_close:
                    continue

            return pos

        # Fallback: return center of deployment zone
        if zone.shape == 'rectangle':
            bounds = zone.bounds
            return Position(
                (bounds['x_min'] + bounds['x_max']) / 2,
                (bounds['y_min'] + bounds['y_max']) / 2
            )
        elif 'center' in zone.bounds:
            return Position(zone.bounds['center'][0], zone.bounds['center'][1])
        else:
            return Position(22, 15)  # Default fallback

    def list_available_layouts(self) -> List[str]:
        """Get list of available terrain layouts"""
        return list(self.terrain_layouts['layouts'].keys())

    def list_available_deployments(self) -> List[str]:
        """Get list of available deployment maps"""
        return list(self.deployment_maps['deployment_maps'].keys())

    def list_available_objectives(self) -> List[str]:
        """Get list of available objective placements"""
        return list(self.deployment_maps['objective_placements'].keys())

    def get_layout_description(self, layout_name: str) -> str:
        """Get human-readable description of terrain layout"""
        if layout_name not in self.terrain_layouts['layouts']:
            return "Unknown layout"
        return self.terrain_layouts['layouts'][layout_name].get('name', layout_name)

    def get_deployment_description(self, map_name: str) -> str:
        """Get human-readable description of deployment map"""
        if map_name not in self.deployment_maps['deployment_maps']:
            return "Unknown deployment"
        map_data = self.deployment_maps['deployment_maps'][map_name]
        return f"{map_data['name']}: {map_data['description']}"


# Example usage
if __name__ == "__main__":
    manager = TerrainManager()

    print("=== Available Terrain Layouts ===")
    for layout in manager.list_available_layouts():
        print(f"  {layout}: {manager.get_layout_description(layout)}")

    print("\n=== Available Deployment Maps ===")
    for deployment in manager.list_available_deployments():
        print(f"  {deployment}: {manager.get_deployment_description(deployment)}")

    print("\n=== Available Objective Sets ===")
    for obj_set in manager.list_available_objectives():
        data = manager.deployment_maps['objective_placements'][obj_set]
        print(f"  {obj_set}: {data['name']} ({len(data['objectives'])} objectives)")

    # Test loading
    print("\n=== Testing Layout 1 ===")
    terrain = manager.get_terrain_layout('layout_1')
    print(f"Loaded {len(terrain)} terrain pieces")

    print("\n=== Testing Hammer and Anvil ===")
    p1_zone, p2_zone = manager.get_deployment_map('hammer_and_anvil')
    print(f"Player 1: {p1_zone.description}")
    print(f"Player 2: {p2_zone.description}")

    # Test deployment validation
    test_pos_p1 = Position(6, 30)  # Should be in P1 zone
    test_pos_p2 = Position(38, 30)  # Should be in P2 zone
    test_pos_neutral = Position(22, 30)  # Should be in neither

    print(f"\nPosition (6, 30) in P1 zone: {p1_zone.is_valid_deployment(test_pos_p1)}")
    print(f"Position (38, 30) in P2 zone: {p2_zone.is_valid_deployment(test_pos_p2)}")
    print(f"Position (22, 30) in P1 zone: {p1_zone.is_valid_deployment(test_pos_neutral)}")
