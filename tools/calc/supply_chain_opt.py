"""
tools/calc/supply_chain_opt.py - Logistics & Supply Chain Routing Optimizer
Employs formulation patterns from NVIDIA cuOpt Routing API (VRP, Cost Matrices, Fleet Capacities).
Enables equity/credit research analysts to quantify distribution network efficiency,
logistics cost per unit, fleet utilization, and margin sensitivity to fuel/transit inflation.
Audited and logged to ProvenanceLedger.
"""

import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from tools.ledger import ProvenanceLedger


class SupplyChainLogisticsOptimizer:
    """
    Logistics & Supply Chain Network Optimizer.
    Models Vehicle Routing Problems (VRP) for corporate distribution networks:
        Locations: Depot (index 0) + N customer / distribution nodes
        Cost Matrix: Pairwise distance or transit cost between nodes
        Demand: Delivery units required per node
        Fleet: Number of vehicles and capacity per vehicle

    Financial Outputs:
    - Total network transit cost ($ or km)
    - Fleet capacity utilization (%)
    - Cost per delivered unit
    - Operating margin elasticity to fuel/transportation inflation (+10%, +20%)
    - Provenance audit trail
    """

    def __init__(self, cost_per_distance_unit: float = 2.50, fuel_cost_share: float = 0.35):
        """
        :param cost_per_distance_unit: Operating cost per distance unit ($/km or $/mile).
        :param fuel_cost_share: Proportion of transportation cost attributable to fuel (for elasticity).
        """
        self.cost_per_dist = float(cost_per_distance_unit)
        self.fuel_cost_share = float(fuel_cost_share)

    @staticmethod
    def build_euclidean_cost_matrix(coordinates: List[Tuple[float, float]]) -> np.ndarray:
        """
        Constructs pairwise Euclidean cost matrix from 2D coordinates [(x0, y0), (x1, y1), ...].
        """
        pts = np.array(coordinates, dtype=np.float32)
        diff = pts[:, np.newaxis, :] - pts[np.newaxis, :, :]
        dist_matrix = np.sqrt(np.sum(diff ** 2, axis=-1))
        return dist_matrix

    def solve_capacitated_vrp(
        self,
        cost_matrix: np.ndarray,
        demands: List[float],
        vehicle_capacity: float,
        num_vehicles: int,
        depot_index: int = 0,
        ledger: Optional[ProvenanceLedger] = None
    ) -> Dict[str, Any]:
        """
        Solves Capacitated Vehicle Routing Problem (CVRP) via deterministic savings heuristic
        with capacity and fleet constraints.
        
        :param cost_matrix: (N x N) distance or cost matrix.
        :param demands: Demand per node. Index depot_index is 0.
        :param vehicle_capacity: Maximum load per vehicle.
        :param num_vehicles: Available fleet size.
        :param depot_index: Index of the central fulfillment center / depot.
        :param ledger: Optional ProvenanceLedger instance.
        """
        n = cost_matrix.shape[0]
        if len(demands) != n:
            raise ValueError(f"Demands length ({len(demands)}) must match cost matrix dimension ({n})")

        total_demand = sum(demands[i] for i in range(n) if i != depot_index)
        max_possible_capacity = num_vehicles * vehicle_capacity
        if total_demand > max_possible_capacity:
            raise ValueError(
                f"Infeasible demand: Total demand ({total_demand}) exceeds fleet capacity ({max_possible_capacity})"
            )

        # Clarke-Wright Savings formulation
        # Savings S(i, j) = C(depot, i) + C(depot, j) - C(i, j)
        customers = [i for i in range(n) if i != depot_index]
        savings = []
        for i in range(len(customers)):
            for j in range(i + 1, len(customers)):
                ci = customers[i]
                cj = customers[j]
                s = cost_matrix[depot_index, ci] + cost_matrix[depot_index, cj] - cost_matrix[ci, cj]
                savings.append((s, ci, cj))

        savings.sort(key=lambda x: x[0], reverse=True)

        # Initialize: each customer gets an individual route [depot, c, depot]
        routes = [[c] for c in customers]

        def find_route(node: int) -> int:
            for idx, r in enumerate(routes):
                if node in r:
                    return idx
            return -1

        for s_val, ci, cj in savings:
            if s_val <= 0:
                continue
            r_i_idx = find_route(ci)
            r_j_idx = find_route(cj)

            if r_i_idx == r_j_idx or r_i_idx == -1 or r_j_idx == -1:
                continue

            r_i = routes[r_i_idx]
            r_j = routes[r_j_idx]

            can_merge = False
            merged = []
            if r_i[-1] == ci and r_j[0] == cj:
                can_merge = True
                merged = r_i + r_j
            elif r_j[-1] == cj and r_i[0] == ci:
                can_merge = True
                merged = r_j + r_i
            elif r_i[0] == ci and r_j[0] == cj:
                can_merge = True
                merged = list(reversed(r_i)) + r_j
            elif r_i[-1] == ci and r_j[-1] == cj:
                can_merge = True
                merged = r_i + list(reversed(r_j))

            if can_merge:
                merged_demand = sum(demands[node] for node in merged)
                if merged_demand <= vehicle_capacity:
                    routes.pop(max(r_i_idx, r_j_idx))
                    routes.pop(min(r_i_idx, r_j_idx))
                    routes.append(merged)

        detailed_routes = []
        total_distance = 0.0

        for r_idx, r in enumerate(routes):
            route_dist = cost_matrix[depot_index, r[0]]
            for k in range(len(r) - 1):
                route_dist += cost_matrix[r[k], r[k + 1]]
            route_dist += cost_matrix[r[-1], depot_index]

            r_demand = sum(demands[node] for node in r)
            total_distance += route_dist

            detailed_routes.append({
                "vehicle_id": r_idx + 1,
                "stops": [depot_index] + r + [depot_index],
                "route_distance": round(float(route_dist), 2),
                "load": round(float(r_demand), 2),
                "capacity_utilization_pct": round(float(r_demand / vehicle_capacity * 100.0), 2)
            })

        total_transport_cost = total_distance * self.cost_per_dist
        cost_per_unit = total_transport_cost / total_demand if total_demand > 0 else 0.0
        avg_fleet_utilization = (total_demand / (len(routes) * vehicle_capacity)) * 100.0 if routes else 0.0

        fuel_spike_10_cost = total_transport_cost * (1.0 + self.fuel_cost_share * 0.10)
        fuel_spike_20_cost = total_transport_cost * (1.0 + self.fuel_cost_share * 0.20)

        result = {
            "num_routes": len(routes),
            "vehicles_utilized": len(routes),
            "total_network_distance": round(float(total_distance), 2),
            "total_transport_cost": round(float(total_transport_cost), 2),
            "cost_per_unit_delivered": round(float(cost_per_unit), 4),
            "fleet_capacity_utilization_pct": round(float(avg_fleet_utilization), 2),
            "routes": detailed_routes,
            "sensitivity": {
                "fuel_plus_10pct_cost": round(float(fuel_spike_10_cost), 2),
                "fuel_plus_20pct_cost": round(float(fuel_spike_20_cost), 2),
                "logistics_cost_inflation_per_unit_10pct": round(float((fuel_spike_10_cost - total_transport_cost) / total_demand), 4) if total_demand > 0 else 0.0
            }
        }

        # Provenance logging
        if ledger is not None:
            ledger_id = ledger.record(
                tool="tools.calc.supply_chain_opt",
                inputs={"num_nodes": n, "vehicle_capacity": vehicle_capacity, "num_vehicles": num_vehicles},
                output=result,
                raw_value=total_transport_cost,
                source="NVIDIA cuOpt Routing API formulation",
                notes=f"Total Cost: ${total_transport_cost:.2f}, Dist: {total_distance:.1f}, Cost/Unit: ${cost_per_unit:.4f}",
                source_tag="SUPPLY_CHAIN_OPT"
            )
            result["ledger_id"] = ledger_id

        return result
