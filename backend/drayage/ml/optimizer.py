"""
Google OR-Tools Dispatch and Assignment Optimizer for Component 2 Drayage System.

Solves the optimal bipartite assignment of available terminal drayage trucks
to pending container transport tasks by minimizing total operational cost:
    Objective = w_empty * empty_travel_time + w_loaded * predicted_travel_time - w_priority * priority_bonus
"""
import time
from typing import Any, Dict, List, Optional, Tuple
from ortools.linear_solver import pywraplp

from backend.drayage.ml.predictor import TravelTimePredictor


# Empirical terminal zone distance matrix (in meters) derived from historical operations
DEFAULT_PORT_DISTANCE_METERS = 1200.0


class DrayageDispatchOptimizer:
    """
    Mixed-Integer Linear Programming (MILP) Dispatch Optimizer using Google OR-Tools.
    """

    def __init__(
        self,
        predictor: Optional[TravelTimePredictor] = None,
        weight_empty_travel: float = 1.0,
        weight_loaded_travel: float = 1.0,
        weight_priority: float = 3.0,
    ):
        self.predictor = predictor or TravelTimePredictor.get_instance()
        self.weight_empty = weight_empty_travel
        self.weight_loaded = weight_loaded_travel
        self.weight_priority = weight_priority

    @staticmethod
    def estimate_empty_distance(from_zone: Optional[str], to_zone: Optional[str]) -> float:
        """
        Estimate deadhead (empty) distance from truck current zone to task pickup zone.
        """
        if not from_zone or not to_zone:
            return DEFAULT_PORT_DISTANCE_METERS
        if from_zone == to_zone:
            return 50.0  # Same block repositioning
        # Standard average intra-terminal zone transfer
        return DEFAULT_PORT_DISTANCE_METERS

    def optimize_dispatch(
        self,
        available_trucks: List[Dict[str, Any]],
        pending_tasks: List[Dict[str, Any]],
        time_limit_ms: int = 5000,
    ) -> Dict[str, Any]:
        """
        Run the assignment optimization.

        Parameters:
        - available_trucks: list of dicts with keys: truck_id, driver_id, vehicle_type, current_zone
        - pending_tasks: list of dicts with keys: task_id, pickup_zone, destination_zone, priority, distance_meters, route_id
        """
        start_time = time.perf_counter()

        if not available_trucks or not pending_tasks:
            return {
                "status": "NO_WORK",
                "assignments": [],
                "unassigned_trucks": [t.get("truck_id") for t in available_trucks],
                "unassigned_tasks": [j.get("task_id") for j in pending_tasks],
                "total_cost": 0.0,
                "solver_duration_ms": round((time.perf_counter() - start_time) * 1000, 2),
            }

        num_trucks = len(available_trucks)
        num_tasks = len(pending_tasks)

        # Pre-compute loaded travel times using XGBoost
        batch_task_queries = []
        for task in pending_tasks:
            batch_task_queries.append({
                "distance_meters": task.get("distance_meters", 1200.0),
                "vehicle_type": "Internal_Drayage_Truck",
                "route_id": task.get("route_id", "RT_ECT_MAIN"),
                "start_zone": task.get("pickup_zone", "CICT_Berth_01"),
                "destination_zone": task.get("destination_zone", "Yard_Block_A"),
            })

        predicted_tasks = self.predictor.predict_batch(batch_task_queries)
        for i, task in enumerate(pending_tasks):
            task["predicted_travel_time_minutes"] = predicted_tasks[i]["predicted_travel_time_minutes"]
            task["predicted_travel_time_seconds"] = predicted_tasks[i]["predicted_travel_time_seconds"]

        # Build Cost Matrix
        # C[i][j] = cost of assigning truck i to task j
        cost_matrix = []
        TASK_REWARD = 1000.0  # Incentive to assign as many tasks as possible

        for i, truck in enumerate(available_trucks):
            truck_costs = []
            truck_zone = truck.get("current_zone", "Yard_Block_A")
            v_type = truck.get("vehicle_type", "Internal_Drayage_Truck")
            speed_mps = 5.0 if v_type == "AGV" else 6.11

            for j, task in enumerate(pending_tasks):
                pickup_zone = task.get("pickup_zone", "CICT_Berth_01")
                empty_dist = self.estimate_empty_distance(truck_zone, pickup_zone)
                empty_time_min = (empty_dist / speed_mps) / 60.0

                loaded_time_min = task["predicted_travel_time_minutes"]
                priority = task.get("priority", 1)
                # Priority 1 is high priority (bonus 3.0), Priority 2 is medium (bonus 2.0), Priority 3 is low (bonus 1.0)
                priority_bonus = (4.0 - min(max(priority, 1), 3))

                cost = (
                    (self.weight_empty * empty_time_min)
                    + (self.weight_loaded * loaded_time_min)
                    - (self.weight_priority * priority_bonus)
                    - TASK_REWARD
                )
                truck_costs.append({
                    "cost": cost,
                    "empty_distance_meters": empty_dist,
                    "empty_travel_minutes": round(empty_time_min, 2),
                    "loaded_travel_minutes": loaded_time_min,
                    "priority_bonus": priority_bonus,
                })
            cost_matrix.append(truck_costs)

        # Initialize OR-Tools Linear Solver (SCIP or CBC)
        solver = pywraplp.Solver.CreateSolver("SCIP")
        if not solver:
            solver = pywraplp.Solver.CreateSolver("CBC")
        if not solver:
            raise RuntimeError("Neither SCIP nor CBC solver available in ortools installation.")

        solver.SetTimeLimit(time_limit_ms)

        # Decision variables: x[i][j] = 1 if truck i is assigned to task j
        x = {}
        for i in range(num_trucks):
            for j in range(num_tasks):
                x[i, j] = solver.BoolVar(f"x_{i}_{j}")

        # Constraint 1: Each truck can be assigned to at most 1 task
        for i in range(num_trucks):
            solver.Add(solver.Sum([x[i, j] for j in range(num_tasks)]) <= 1)

        # Constraint 2: Each task can be assigned to at most 1 truck
        for j in range(num_tasks):
            solver.Add(solver.Sum([x[i, j] for j in range(num_trucks)]) <= 1)

        # Objective Function: Minimize total assignment cost
        objective = solver.Objective()
        for i in range(num_trucks):
            for j in range(num_tasks):
                objective.SetCoefficient(x[i, j], cost_matrix[i][j]["cost"])
        objective.SetMinimization()

        solver_status = solver.Solve()

        assignments = []
        assigned_truck_indices = set()
        assigned_task_indices = set()

        if solver_status in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
            for i in range(num_trucks):
                for j in range(num_tasks):
                    if x[i, j].solution_value() > 0.5:
                        assigned_truck_indices.add(i)
                        assigned_task_indices.add(j)
                        details = cost_matrix[i][j]
                        assignments.append({
                            "truck_id": available_trucks[i].get("truck_id"),
                            "driver_id": available_trucks[i].get("driver_id"),
                            "task_id": pending_tasks[j].get("task_id"),
                            "pickup_zone": pending_tasks[j].get("pickup_zone"),
                            "destination_zone": pending_tasks[j].get("destination_zone"),
                            "priority": pending_tasks[j].get("priority", 1),
                            "empty_distance_meters": details["empty_distance_meters"],
                            "empty_travel_minutes": details["empty_travel_minutes"],
                            "estimated_travel_minutes": details["loaded_travel_minutes"],
                            "total_estimated_cycle_minutes": round(
                                details["empty_travel_minutes"] + details["loaded_travel_minutes"], 2
                            ),
                        })

        unassigned_trucks = [
            available_trucks[i].get("truck_id")
            for i in range(num_trucks)
            if i not in assigned_truck_indices
        ]
        unassigned_tasks = [
            pending_tasks[j].get("task_id")
            for j in range(num_tasks)
            if j not in assigned_task_indices
        ]

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return {
            "status": "OPTIMAL" if solver_status == pywraplp.Solver.OPTIMAL else "FEASIBLE",
            "assignments_count": len(assignments),
            "assignments": assignments,
            "unassigned_trucks": unassigned_trucks,
            "unassigned_tasks": unassigned_tasks,
            "solver_duration_ms": duration_ms,
        }
