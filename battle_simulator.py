"""
Warhammer 40k Full Battle Simulator
Simulates complete battles with movement, positioning, phases, and strategy
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
from enum import Enum
import copy


# ============================================================================
# ENUMS AND CONSTANTS
# ============================================================================

class Phase(Enum):
    """Battle round phases"""
    COMMAND = "Command"
    MOVEMENT = "Movement"
    SHOOTING = "Shooting"
    CHARGE = "Charge"
    FIGHT = "Fight"


class Terrain(Enum):
    """Terrain types"""
    OPEN = "Open"
    LIGHT_COVER = "Light Cover"
    HEAVY_COVER = "Heavy Cover"
    OBSCURING = "Obscuring"
    IMPASSABLE = "Impassable"


class UnitState(Enum):
    """Unit status"""
    ACTIVE = "Active"
    FALLBACK = "Fall Back"
    BATTLESHOCK = "Battle-shocked"
    DESTROYED = "Destroyed"


# ============================================================================
# BATTLEFIELD AND POSITIONING
# ============================================================================

@dataclass
class Position:
    """2D position on battlefield"""
    x: float
    y: float

    def distance_to(self, other: 'Position') -> float:
        """Calculate distance to another position"""
        return np.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)

    def __add__(self, other: 'Position') -> 'Position':
        return Position(self.x + other.x, self.y + other.y)

    def __sub__(self, other: 'Position') -> 'Position':
        return Position(self.x - other.x, self.y - other.y)


@dataclass
class TerrainFeature:
    """Terrain feature on the battlefield"""
    name: str
    terrain_type: Terrain
    center: Position
    width: float  # Width in inches
    length: float  # Length in inches
    rotation: float = 0  # Rotation in degrees
    height: float = 0  # Height in inches
    provides_cover: bool = True
    blocks_los: bool = False

    @property
    def radius(self) -> float:
        """Approximate radius for backward compatibility"""
        return max(self.width, self.length) / 2


@dataclass
class Objective:
    """Objective marker"""
    name: str
    position: Position
    value: int = 5  # VP value
    controlled_by: Optional[int] = None  # Player ID


class Battlefield:
    """The battlefield with terrain and objectives"""

    def __init__(self, width: float = 44.0, length: float = 60.0):
        """
        Standard 40k battlefield
        width: 44" (default)
        length: 60" (default)
        """
        self.width = width
        self.length = length
        self.terrain: List[TerrainFeature] = []
        self.objectives: List[Objective] = []

    def add_terrain(self, feature: TerrainFeature):
        """Add terrain feature"""
        self.terrain.append(feature)

    def add_objective(self, objective: Objective):
        """Add objective marker"""
        self.objectives.append(objective)

    def get_terrain_at(self, pos: Position) -> Optional[TerrainFeature]:
        """Get terrain at position"""
        for feature in self.terrain:
            if pos.distance_to(feature.center) <= feature.radius:
                return feature
        return None

    def has_line_of_sight(self, from_pos: Position, to_pos: Position) -> bool:
        """Check if there's line of sight between two positions"""
        # Simplified LOS - checks if any obscuring terrain blocks the line
        for feature in self.terrain:
            if not feature.blocks_los:
                continue

            # Check if line intersects terrain
            # Simplified: check if midpoint is within obscuring terrain
            midpoint = Position(
                (from_pos.x + to_pos.x) / 2,
                (from_pos.y + to_pos.y) / 2
            )
            if midpoint.distance_to(feature.center) <= feature.radius:
                return False

        return True

    def is_in_cover(self, pos: Position, from_pos: Position) -> bool:
        """Check if position has cover from attacker"""
        terrain = self.get_terrain_at(pos)
        if terrain and terrain.provides_cover:
            return True
        return False


# ============================================================================
# BATTLE UNITS
# ============================================================================

@dataclass
class BattleUnitStats:
    """Unit stats for battle"""
    movement: int
    toughness: int
    save: int
    wounds: int
    leadership: int
    oc: int  # Objective Control
    invuln_save: Optional[int] = None


@dataclass
class BattleWeapon:
    """Weapon for battle simulation"""
    name: str
    is_ranged: bool
    range: int  # In inches
    attacks: str  # "D6", "2D6+3", etc.
    bs_ws: int
    strength: int
    ap: int
    damage: str
    keywords: List[str] = field(default_factory=list)

    def is_in_range(self, distance: float) -> bool:
        """Check if target is in range"""
        if not self.is_ranged:
            return distance <= 1.0  # Melee range
        return distance <= self.range


@dataclass
class BattleUnit:
    """A unit on the battlefield"""
    id: str
    name: str
    player_id: int  # 0 or 1
    faction: str

    # Stats
    stats: BattleUnitStats
    model_count: int
    wounds_per_model: int
    current_wounds: int  # Total wounds remaining

    # Weapons
    ranged_weapons: List[BattleWeapon] = field(default_factory=list)
    melee_weapons: List[BattleWeapon] = field(default_factory=list)

    # Position and movement
    position: Position = field(default_factory=lambda: Position(0, 0))
    has_moved: bool = False
    has_advanced: bool = False
    has_fallen_back: bool = False

    # Combat state
    has_shot: bool = False
    has_fought: bool = False
    in_melee: bool = False
    state: UnitState = UnitState.ACTIVE

    # Abilities
    abilities: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)

    # Metadata
    is_character: bool = False
    points_cost: int = 0

    def is_destroyed(self) -> bool:
        """Check if unit is destroyed"""
        return self.current_wounds <= 0 or self.state == UnitState.DESTROYED

    def models_remaining(self) -> int:
        """Get number of models remaining"""
        return max(0, int(np.ceil(self.current_wounds / self.wounds_per_model)))

    def take_damage(self, damage: int) -> int:
        """Apply damage and return models killed"""
        models_before = self.models_remaining()
        self.current_wounds = max(0, self.current_wounds - damage)
        models_after = self.models_remaining()

        if self.current_wounds <= 0:
            self.state = UnitState.DESTROYED

        return models_before - models_after

    def distance_to(self, other: 'BattleUnit') -> float:
        """Calculate distance to another unit"""
        return self.position.distance_to(other.position)

    def is_in_engagement_range(self, enemy_units: List['BattleUnit']) -> bool:
        """Check if unit is in engagement range of enemies"""
        for enemy in enemy_units:
            if enemy.is_destroyed():
                continue
            if self.distance_to(enemy) <= 1.0:  # Engagement range
                return True
        return False

    def reset_phase_flags(self):
        """Reset phase-specific flags"""
        self.has_moved = False
        self.has_advanced = False
        self.has_fallen_back = False
        self.has_shot = False
        self.has_fought = False


# ============================================================================
# STRATEGY AND AI
# ============================================================================

class BattleStrategy:
    """AI strategy for battle decisions"""

    @staticmethod
    def select_deployment_zone(units: List[BattleUnit], player_id: int,
                               battlefield: Battlefield,
                               deployment_zone=None) -> List[Tuple[BattleUnit, Position]]:
        """
        Deploy units in deployment zone

        Args:
            units: Units to deploy
            player_id: 0 or 1
            battlefield: Battlefield object
            deployment_zone: Optional DeploymentZone object (from terrain_manager)

        Returns:
            List of (unit, position) tuples
        """
        deployments = []

        # Use custom deployment zone if provided
        if deployment_zone is not None:
            # Import here to avoid circular dependency
            from terrain_manager import DeploymentZone

            for unit in units:
                # Get valid random position within zone
                pos = deployment_zone.is_valid_deployment

                # Attempt to find valid position
                max_attempts = 100
                for _ in range(max_attempts):
                    # Generate random position based on zone shape
                    if deployment_zone.shape == 'rectangle':
                        bounds = deployment_zone.bounds
                        x = np.random.uniform(bounds['x_min'] + 2, bounds['x_max'] - 2)
                        y = np.random.uniform(bounds['y_min'] + 2, bounds['y_max'] - 2)
                        pos = Position(x, y)
                    elif deployment_zone.shape == 'triangle' and 'center' in deployment_zone.bounds:
                        center = deployment_zone.bounds['center']
                        radius = deployment_zone.bounds['radius']
                        angle = np.random.uniform(0, 2 * np.pi)
                        dist = np.random.uniform(0, radius - 2)
                        x = center[0] + dist * np.cos(angle)
                        y = center[1] + dist * np.sin(angle)
                        pos = Position(x, y)
                    elif deployment_zone.shape == 'compound':
                        rectangles = deployment_zone.bounds.get('rectangles', [])
                        if rectangles:
                            rect = np.random.choice(rectangles)
                            x = np.random.uniform(rect['x_min'] + 2, rect['x_max'] - 2)
                            y = np.random.uniform(rect['y_min'] + 2, rect['y_max'] - 2)
                            pos = Position(x, y)
                    else:
                        # Fallback
                        pos = Position(22, 12 if player_id == 0 else 48)

                    if deployment_zone.is_valid_deployment(pos):
                        deployments.append((unit, pos))
                        break
                else:
                    # Couldn't find valid position, use fallback
                    deployments.append((unit, Position(22, 12 if player_id == 0 else 48)))

        else:
            # Default deployment (legacy behavior)
            deployment_y = 12.0 if player_id == 0 else battlefield.length - 12.0

            for i, unit in enumerate(units):
                # Spread units across deployment zone
                spacing = battlefield.width / (len(units) + 1)
                x = spacing * (i + 1)

                # Add some randomness
                x += np.random.uniform(-3, 3)
                y = deployment_y + np.random.uniform(-8, 8)

                # Keep within bounds
                x = np.clip(x, 2, battlefield.width - 2)
                y = np.clip(y, 2 if player_id == 0 else battlefield.length - 24,
                           24 if player_id == 0 else battlefield.length - 2)

                deployments.append((unit, Position(x, y)))

        return deployments

    @staticmethod
    def select_movement(unit: BattleUnit, enemies: List[BattleUnit],
                       friendlies: List[BattleUnit], objectives: List[Objective],
                       battlefield: Battlefield) -> Position:
        """
        Decide where to move unit
        Priority:
        1. If in melee, stay in melee or fall back
        2. If shooty, keep at range
        3. If melee, move toward nearest enemy
        4. Otherwise, move toward nearest objective
        """
        current_pos = unit.position

        # Find nearest enemy
        nearest_enemy = None
        min_enemy_dist = float('inf')
        for enemy in enemies:
            if enemy.is_destroyed():
                continue
            dist = unit.distance_to(enemy)
            if dist < min_enemy_dist:
                min_enemy_dist = dist
                nearest_enemy = enemy

        # If in engagement range, decide fight or fall back
        if unit.is_in_engagement_range(enemies):
            # Check if we're strong in melee
            has_good_melee = len(unit.melee_weapons) > 0 and unit.stats.wounds > 3
            if has_good_melee:
                # Stay and fight
                return current_pos
            else:
                # Fall back toward friendly units
                if friendlies:
                    avg_x = np.mean([f.position.x for f in friendlies])
                    avg_y = np.mean([f.position.y for f in friendlies])
                    target = Position(avg_x, avg_y)
                    return BattleStrategy._move_toward(current_pos, target, unit.stats.movement)
                return current_pos

        # Ranged unit: keep at optimal range
        if unit.ranged_weapons and not unit.melee_weapons:
            if nearest_enemy:
                max_weapon_range = max(w.range for w in unit.ranged_weapons)
                optimal_range = max_weapon_range * 0.75  # 75% of max range

                if min_enemy_dist < optimal_range * 0.5:
                    # Too close, back up
                    direction = current_pos - nearest_enemy.position
                    direction_norm = np.sqrt(direction.x**2 + direction.y**2)
                    if direction_norm > 0:
                        direction.x /= direction_norm
                        direction.y /= direction_norm
                        move_distance = min(unit.stats.movement, optimal_range - min_enemy_dist)
                        return Position(
                            current_pos.x + direction.x * move_distance,
                            current_pos.y + direction.y * move_distance
                        )
                elif min_enemy_dist > optimal_range:
                    # Too far, move closer
                    return BattleStrategy._move_toward(current_pos, nearest_enemy.position,
                                                      unit.stats.movement)

        # Melee unit: charge toward enemy
        if unit.melee_weapons and nearest_enemy:
            # Move toward nearest enemy
            return BattleStrategy._move_toward(current_pos, nearest_enemy.position,
                                              unit.stats.movement)

        # Default: move toward nearest objective
        if objectives:
            nearest_obj = min(objectives, key=lambda obj: current_pos.distance_to(obj.position))
            return BattleStrategy._move_toward(current_pos, nearest_obj.position,
                                              unit.stats.movement)

        return current_pos

    @staticmethod
    def _move_toward(from_pos: Position, to_pos: Position, max_distance: float) -> Position:
        """Move from position toward target, up to max distance"""
        direction = to_pos - from_pos
        distance = np.sqrt(direction.x**2 + direction.y**2)

        if distance == 0:
            return from_pos

        # Normalize and scale
        move_distance = min(distance, max_distance)
        direction.x = (direction.x / distance) * move_distance
        direction.y = (direction.y / distance) * move_distance

        return from_pos + direction

    @staticmethod
    def select_shooting_target(unit: BattleUnit, enemies: List[BattleUnit],
                               battlefield: Battlefield) -> Optional[BattleUnit]:
        """
        Select best shooting target
        Priority:
        1. In range and LOS
        2. Most damaged (finish kills)
        3. Highest threat (characters, heavy weapons)
        4. Closest
        """
        valid_targets = []

        for enemy in enemies:
            if enemy.is_destroyed():
                continue

            # Check if any weapon is in range
            distance = unit.distance_to(enemy)
            has_range = any(w.is_in_range(distance) for w in unit.ranged_weapons)

            if not has_range:
                continue

            # Check LOS
            if not battlefield.has_line_of_sight(unit.position, enemy.position):
                continue

            # Calculate target priority score
            score = 0

            # Prefer damaged units (finish kills)
            wound_percentage = enemy.current_wounds / (enemy.model_count * enemy.wounds_per_model)
            if wound_percentage < 0.5:
                score += 50

            # Prefer characters
            if enemy.is_character:
                score += 30

            # Prefer closer targets
            score += max(0, 30 - distance)

            valid_targets.append((enemy, score))

        if not valid_targets:
            return None

        # Select highest priority target
        valid_targets.sort(key=lambda x: x[1], reverse=True)
        return valid_targets[0][0]

    @staticmethod
    def select_charge_target(unit: BattleUnit, enemies: List[BattleUnit]) -> Optional[BattleUnit]:
        """Select best charge target"""
        valid_targets = []

        for enemy in enemies:
            if enemy.is_destroyed():
                continue

            distance = unit.distance_to(enemy)

            # Must be within 12" to declare charge
            if distance > 12.0:
                continue

            # Calculate priority
            score = 0

            # Prefer damaged units
            wound_percentage = enemy.current_wounds / (enemy.model_count * enemy.wounds_per_model)
            if wound_percentage < 0.5:
                score += 50

            # Prefer characters
            if enemy.is_character:
                score += 30

            # Prefer closer
            score += max(0, 30 - distance * 2)

            valid_targets.append((enemy, score))

        if not valid_targets:
            return None

        valid_targets.sort(key=lambda x: x[1], reverse=True)
        return valid_targets[0][0]


# ============================================================================
# BATTLE SIMULATOR
# ============================================================================

@dataclass
class BattleState:
    """Current state of the battle"""
    turn: int = 1
    active_player: int = 0
    phase: Phase = Phase.COMMAND
    player_1_vp: int = 0
    player_2_vp: int = 0


@dataclass
class BattleEvent:
    """An event that occurred during battle"""
    turn: int
    phase: Phase
    player: int
    event_type: str  # 'movement', 'shooting', 'charge', 'melee', 'objective_scored'
    description: str
    damage_dealt: int = 0
    models_killed: int = 0


class BattleSimulator:
    """Full Warhammer 40k battle simulator"""

    def __init__(self, battlefield: Battlefield):
        self.battlefield = battlefield
        self.state = BattleState()

        self.player_1_units: List[BattleUnit] = []
        self.player_2_units: List[BattleUnit] = []

        self.battle_log: List[BattleEvent] = []

    def add_unit(self, unit: BattleUnit):
        """Add unit to battle"""
        if unit.player_id == 0:
            self.player_1_units.append(unit)
        else:
            self.player_2_units.append(unit)

    def deploy_armies(self, p1_deployment_zone=None, p2_deployment_zone=None):
        """
        Deploy both armies

        Args:
            p1_deployment_zone: Optional DeploymentZone for player 1
            p2_deployment_zone: Optional DeploymentZone for player 2
        """
        # Deploy player 1
        deployments_p1 = BattleStrategy.select_deployment_zone(
            self.player_1_units, 0, self.battlefield, p1_deployment_zone
        )
        for unit, pos in deployments_p1:
            unit.position = pos

        # Deploy player 2
        deployments_p2 = BattleStrategy.select_deployment_zone(
            self.player_2_units, 1, self.battlefield, p2_deployment_zone
        )
        for unit, pos in deployments_p2:
            unit.position = pos

        deployment_msg = "Armies deployed"
        if p1_deployment_zone:
            deployment_msg += f" ({p1_deployment_zone.name.split('-')[0].strip()})"

        self._log_event("deployment", deployment_msg)

    def simulate_battle(self, max_turns: int = 5, p1_deployment_zone=None, p2_deployment_zone=None,
                        p1_army_name: str = "Player 1", p2_army_name: str = "Player 2") -> Dict:
        """
        Simulate a full battle

        Args:
            max_turns: Maximum number of turns to play
            p1_deployment_zone: Optional DeploymentZone for player 1
            p2_deployment_zone: Optional DeploymentZone for player 2
            p1_army_name: Name of player 1's army
            p2_army_name: Name of player 2's army

        Returns:
            Battle results dictionary
        """
        # Store army names for winner determination
        self.p1_army_name = p1_army_name
        self.p2_army_name = p2_army_name

        self.deploy_armies(p1_deployment_zone, p2_deployment_zone)

        for turn in range(1, max_turns + 1):
            self.state.turn = turn

            # Player 1 turn
            self._simulate_player_turn(0)

            # Player 2 turn
            self._simulate_player_turn(1)

            # Score objectives at end of turn
            self._score_objectives()

            # Check if battle is over
            if self._check_battle_end():
                break

        return self._generate_battle_report()

    def _simulate_player_turn(self, player_id: int):
        """Simulate one player's turn"""
        self.state.active_player = player_id
        active_units = self.player_1_units if player_id == 0 else self.player_2_units
        enemy_units = self.player_2_units if player_id == 0 else self.player_1_units

        # Reset phase flags
        for unit in active_units:
            unit.reset_phase_flags()

        # COMMAND PHASE
        self.state.phase = Phase.COMMAND
        self._command_phase(active_units)

        # MOVEMENT PHASE
        self.state.phase = Phase.MOVEMENT
        self._movement_phase(active_units, enemy_units)

        # SHOOTING PHASE
        self.state.phase = Phase.SHOOTING
        self._shooting_phase(active_units, enemy_units)

        # CHARGE PHASE
        self.state.phase = Phase.CHARGE
        self._charge_phase(active_units, enemy_units)

        # FIGHT PHASE
        self.state.phase = Phase.FIGHT
        self._fight_phase(active_units, enemy_units)

    def _command_phase(self, units: List[BattleUnit]):
        """Command phase - battle-shock tests, CP generation, etc."""
        # Battle-shock tests for damaged units
        for unit in units:
            if unit.is_destroyed():
                continue

            # Test if below half strength
            if unit.models_remaining() <= unit.model_count / 2:
                # Roll battle-shock test (simplified)
                roll = np.random.randint(1, 7) + np.random.randint(1, 7)
                if roll > unit.stats.leadership:
                    unit.state = UnitState.BATTLESHOCK
                    self._log_event("battle-shock", f"{unit.name} is battle-shocked!")

    def _movement_phase(self, units: List[BattleUnit], enemies: List[BattleUnit]):
        """Movement phase"""
        for unit in units:
            if unit.is_destroyed() or unit.state == UnitState.BATTLESHOCK:
                continue

            # Determine new position
            new_pos = BattleStrategy.select_movement(
                unit, enemies, units, self.battlefield.objectives, self.battlefield
            )

            # Check if falling back
            if unit.is_in_engagement_range(enemies):
                distance_moved = unit.position.distance_to(new_pos)
                if distance_moved > 0:
                    unit.has_fallen_back = True
                    unit.state = UnitState.FALLBACK
                    self._log_event("movement", f"{unit.name} falls back")

            # Apply movement
            old_pos = unit.position
            unit.position = new_pos
            distance_moved = old_pos.distance_to(new_pos)

            if distance_moved > unit.stats.movement:
                unit.has_advanced = True

            if distance_moved > 0.5:  # Moved significantly
                unit.has_moved = True
                self._log_event("movement",
                              f"{unit.name} moves {distance_moved:.1f}\" to ({new_pos.x:.1f}, {new_pos.y:.1f})")

    def _shooting_phase(self, units: List[BattleUnit], enemies: List[BattleUnit]):
        """Shooting phase"""
        for unit in units:
            if unit.is_destroyed() or not unit.ranged_weapons:
                continue

            # Cannot shoot if fell back (unless specific ability)
            if unit.has_fallen_back:
                continue

            # Select target
            target = BattleStrategy.select_shooting_target(unit, enemies, self.battlefield)
            if not target:
                continue

            # Shoot with all ranged weapons
            total_damage = 0
            total_kills = 0

            for weapon in unit.ranged_weapons:
                damage, kills = self._resolve_shooting(unit, weapon, target)
                total_damage += damage
                total_kills += kills

            unit.has_shot = True

            if total_damage > 0:
                self._log_event(
                    "shooting",
                    f"{unit.name} shoots {target.name} for {total_damage} damage ({total_kills} models killed)",
                    damage_dealt=total_damage,
                    models_killed=total_kills
                )

    def _resolve_shooting(self, attacker: BattleUnit, weapon: BattleWeapon,
                         defender: BattleUnit) -> Tuple[int, int]:
        """
        Resolve shooting attack (simplified)
        Returns (damage_dealt, models_killed)
        """
        # Simplified attack resolution - would use full combat_simulator logic
        distance = attacker.distance_to(defender)

        if not weapon.is_in_range(distance):
            return 0, 0

        # Parse attacks
        num_attacks = self._parse_dice_notation(weapon.attacks)
        num_attacks *= attacker.models_remaining()  # All models shoot

        # Hit rolls
        to_hit = weapon.bs_ws
        if attacker.has_advanced:
            to_hit += 1  # -1 to hit when advancing

        hit_rolls = np.random.randint(1, 7, num_attacks)
        hits = np.sum(hit_rolls >= to_hit)

        if hits == 0:
            return 0, 0

        # Wound rolls (simplified S vs T)
        to_wound = self._calculate_wound_roll(weapon.strength, defender.stats.toughness)
        wound_rolls = np.random.randint(1, 7, hits)
        wounds = np.sum(wound_rolls >= to_wound)

        if wounds == 0:
            return 0, 0

        # Save rolls
        save_value = defender.stats.save - weapon.ap
        if defender.stats.invuln_save and defender.stats.invuln_save < save_value:
            save_value = defender.stats.invuln_save

        # Check cover
        if self.battlefield.is_in_cover(defender.position, attacker.position):
            save_value -= 1  # +1 to save

        if save_value >= 7:
            failed_saves = wounds  # Cannot save
        else:
            save_rolls = np.random.randint(1, 7, wounds)
            failed_saves = np.sum(save_rolls < save_value)

        # Damage
        damage_per_wound = self._parse_dice_notation(weapon.damage)
        total_damage = failed_saves * damage_per_wound

        # Apply damage
        models_killed = defender.take_damage(total_damage)

        return total_damage, models_killed

    def _charge_phase(self, units: List[BattleUnit], enemies: List[BattleUnit]):
        """Charge phase"""
        for unit in units:
            if unit.is_destroyed() or unit.has_fallen_back:
                continue

            # Only charge if we have melee weapons
            if not unit.melee_weapons:
                continue

            # Select charge target
            target = BattleStrategy.select_charge_target(unit, enemies)
            if not target:
                continue

            # Roll charge distance (2D6)
            charge_roll = np.random.randint(1, 7) + np.random.randint(1, 7)
            distance = unit.distance_to(target)

            if charge_roll >= distance:
                # Successful charge - move into engagement range
                direction = target.position - unit.position
                dist_norm = np.sqrt(direction.x**2 + direction.y**2)
                direction.x = (direction.x / dist_norm) * (distance - 0.5)  # Stop 0.5" away
                direction.y = (direction.y / dist_norm) * (distance - 0.5)

                unit.position = unit.position + direction
                unit.in_melee = True
                target.in_melee = True

                self._log_event("charge",
                              f"{unit.name} charges {target.name} (rolled {charge_roll}, needed {distance:.1f})")

    def _fight_phase(self, units: List[BattleUnit], enemies: List[BattleUnit]):
        """Fight phase"""
        # Collect all units in melee
        melee_units = [(u, u.player_id) for u in units + enemies if u.in_melee and not u.is_destroyed()]

        # Sort by initiative (simplified - could use full 40k rules)
        melee_units.sort(key=lambda x: -x[0].stats.movement)  # Higher M fights first

        for unit, player_id in melee_units:
            if unit.is_destroyed() or unit.has_fought:
                continue

            # Find enemy in engagement range
            enemy_list = enemies if player_id == self.state.active_player else units
            target = None
            for enemy in enemy_list:
                if enemy.is_destroyed():
                    continue
                if unit.distance_to(enemy) <= 1.0:
                    target = enemy
                    break

            if not target:
                continue

            # Fight with all melee weapons
            total_damage = 0
            total_kills = 0

            for weapon in unit.melee_weapons:
                damage, kills = self._resolve_melee(unit, weapon, target)
                total_damage += damage
                total_kills += kills

            unit.has_fought = True

            if total_damage > 0:
                self._log_event(
                    "melee",
                    f"{unit.name} fights {target.name} for {total_damage} damage ({total_kills} models killed)",
                    damage_dealt=total_damage,
                    models_killed=total_kills
                )

    def _resolve_melee(self, attacker: BattleUnit, weapon: BattleWeapon,
                      defender: BattleUnit) -> Tuple[int, int]:
        """Resolve melee attack (simplified)"""
        # Similar to shooting but uses WS and no range check
        num_attacks = self._parse_dice_notation(weapon.attacks)
        num_attacks *= attacker.models_remaining()

        # Hit rolls
        hit_rolls = np.random.randint(1, 7, num_attacks)
        hits = np.sum(hit_rolls >= weapon.bs_ws)

        if hits == 0:
            return 0, 0

        # Wound rolls
        to_wound = self._calculate_wound_roll(weapon.strength, defender.stats.toughness)
        wound_rolls = np.random.randint(1, 7, hits)
        wounds = np.sum(wound_rolls >= to_wound)

        if wounds == 0:
            return 0, 0

        # Saves (no cover in melee)
        save_value = defender.stats.save - weapon.ap
        if defender.stats.invuln_save and defender.stats.invuln_save < save_value:
            save_value = defender.stats.invuln_save

        if save_value >= 7:
            failed_saves = wounds
        else:
            save_rolls = np.random.randint(1, 7, wounds)
            failed_saves = np.sum(save_rolls < save_value)

        # Damage
        damage_per_wound = self._parse_dice_notation(weapon.damage)
        total_damage = failed_saves * damage_per_wound

        models_killed = defender.take_damage(total_damage)

        return total_damage, models_killed

    def _score_objectives(self):
        """Score objectives at end of turn"""
        for obj in self.battlefield.objectives:
            # Find closest unit to objective
            p1_control = 0
            p2_control = 0

            for unit in self.player_1_units:
                if unit.is_destroyed():
                    continue
                if unit.position.distance_to(obj.position) <= 3.0:  # Within 3" of objective
                    p1_control += unit.stats.oc * unit.models_remaining()

            for unit in self.player_2_units:
                if unit.is_destroyed():
                    continue
                if unit.position.distance_to(obj.position) <= 3.0:
                    p2_control += unit.stats.oc * unit.models_remaining()

            # Award objective
            if p1_control > p2_control:
                self.state.player_1_vp += obj.value
                obj.controlled_by = 0
                self._log_event("objective", f"Player 1 scores {obj.name} (+{obj.value} VP)")
            elif p2_control > p1_control:
                self.state.player_2_vp += obj.value
                obj.controlled_by = 1
                self._log_event("objective", f"Player 2 scores {obj.name} (+{obj.value} VP)")

    def _check_battle_end(self) -> bool:
        """Check if battle should end"""
        # Battle ends if one side is tabled
        p1_alive = any(not u.is_destroyed() for u in self.player_1_units)
        p2_alive = any(not u.is_destroyed() for u in self.player_2_units)

        if not p1_alive or not p2_alive:
            return True

        return False

    def _generate_battle_report(self) -> Dict:
        """Generate final battle report"""
        p1_alive = [u for u in self.player_1_units if not u.is_destroyed()]
        p2_alive = [u for u in self.player_2_units if not u.is_destroyed()]

        p1_points_remaining = sum(u.points_cost for u in p1_alive)
        p2_points_remaining = sum(u.points_cost for u in p2_alive)

        return {
            'turns_played': self.state.turn,
            'player_1_vp': self.state.player_1_vp,
            'player_2_vp': self.state.player_2_vp,
            'player_1_units_alive': len(p1_alive),
            'player_2_units_alive': len(p2_alive),
            'player_1_points_remaining': p1_points_remaining,
            'player_2_points_remaining': p2_points_remaining,
            'battle_log': self.battle_log,
            'winner': self._determine_winner()
        }

    def _determine_winner(self) -> str:
        """Determine battle winner"""
        p1_name = getattr(self, 'p1_army_name', 'Player 1')
        p2_name = getattr(self, 'p2_army_name', 'Player 2')

        if self.state.player_1_vp > self.state.player_2_vp:
            return p1_name
        elif self.state.player_2_vp > self.state.player_1_vp:
            return p2_name
        else:
            # Tie-breaker: most points remaining
            p1_pts = sum(u.points_cost for u in self.player_1_units if not u.is_destroyed())
            p2_pts = sum(u.points_cost for u in self.player_2_units if not u.is_destroyed())

            if p1_pts > p2_pts:
                return p1_name
            elif p2_pts > p1_pts:
                return p2_name
            else:
                return "Draw"

    def _log_event(self, event_type: str, description: str,
                   damage_dealt: int = 0, models_killed: int = 0):
        """Log a battle event"""
        event = BattleEvent(
            turn=self.state.turn,
            phase=self.state.phase,
            player=self.state.active_player,
            event_type=event_type,
            description=description,
            damage_dealt=damage_dealt,
            models_killed=models_killed
        )
        self.battle_log.append(event)

    @staticmethod
    def _parse_dice_notation(notation: str) -> int:
        """Parse dice notation like 'D6', '2D6+3' and return average"""
        # Simplified - returns average value
        notation = notation.upper().strip()

        if 'D' not in notation:
            return int(notation)

        parts = notation.replace('+', ' +').replace('-', ' -').split()
        total = 0

        for part in parts:
            if 'D6' in part:
                num_dice = int(part.split('D')[0]) if part.split('D')[0] else 1
                total += num_dice * 3.5  # Average of D6
            elif 'D3' in part:
                num_dice = int(part.split('D')[0]) if part.split('D')[0] else 1
                total += num_dice * 2  # Average of D3
            elif part.startswith('+'):
                total += int(part[1:])
            elif part.startswith('-'):
                total -= int(part[1:])

        return max(1, int(total))

    @staticmethod
    def _calculate_wound_roll(strength: int, toughness: int) -> int:
        """Calculate required wound roll"""
        if strength >= toughness * 2:
            return 2
        elif strength > toughness:
            return 3
        elif strength == toughness:
            return 4
        elif strength * 2 > toughness:
            return 5
        else:
            return 6
