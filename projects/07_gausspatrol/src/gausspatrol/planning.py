"""A* global planner with terrain cost and dynamic occupancy support."""

from __future__ import annotations

import heapq
import math

from .models import Pose2D
from .world import GridCell, PatrolWorld


class PlanningError(RuntimeError):
    pass


def _heuristic(a: GridCell, b: GridCell) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


class AStarPlanner:
    def __init__(self, world: PatrolWorld):
        self.world = world

    def plan(self, start: Pose2D, goal: Pose2D, *, step: int, include_dynamic: bool = True) -> list[Pose2D]:
        start_cell = self.world.to_cell(start.x_m, start.y_m)
        goal_cell = self.world.to_cell(goal.x_m, goal.y_m)
        dynamic = self.world.dynamic_blocked_cells(step) if include_dynamic else set()
        dynamic.discard(start_cell)
        dynamic.discard(goal_cell)
        if self.world.is_static_occupied(start_cell) or self.world.is_static_occupied(goal_cell):
            raise PlanningError("start or goal is occupied")

        frontier: list[tuple[float, int, GridCell]] = [(0.0, 0, start_cell)]
        came_from: dict[GridCell, GridCell | None] = {start_cell: None}
        costs: dict[GridCell, float] = {start_cell: 0.0}
        serial = 0
        while frontier:
            _, _, current = heapq.heappop(frontier)
            if current == goal_cell:
                break
            for nxt, move_cost in self.world.neighbors(current, dynamic):
                terrain = self.world.terrain_at(self.world.to_pose(nxt))
                new_cost = costs[current] + move_cost / max(0.1, terrain.speed_scale)
                if nxt not in costs or new_cost < costs[nxt]:
                    costs[nxt] = new_cost
                    serial += 1
                    heapq.heappush(frontier, (new_cost + _heuristic(nxt, goal_cell), serial, nxt))
                    came_from[nxt] = current
        if goal_cell not in came_from:
            raise PlanningError("no collision-free path")

        cells: list[GridCell] = []
        cursor: GridCell | None = goal_cell
        while cursor is not None:
            cells.append(cursor)
            cursor = came_from[cursor]
        cells.reverse()
        poses = [self.world.to_pose(cell) for cell in cells]
        if poses:
            poses[0] = start
            poses[-1] = goal
        return poses
