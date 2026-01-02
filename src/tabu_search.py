import math
import random
from copy import deepcopy
from typing import Any, Dict, List, Tuple

import numpy as np


class SSCFLPTabuSearch:
    """
    Iterated Tabu Search for the Single Source Capacitated Facility Location Problem.
    Implements key mechanisms, wit delta evaluation and dynamic tabu tenure.
    """

    def __init__(
        self,
        capacities: np.ndarray,
        demands: np.ndarray,
        fixed_costs: np.ndarray,
        assignment_costs: np.ndarray,
        max_iterations: int = 300,
        alpha: float = 1000.0,
        epsilon: float = 0.1,
        beta: float = 0.4,
        max_stagnation: int = 40,
        tabu_tenure_min: int = 10,
        tabu_tenure_max: int = 30,
        random_seed: int | None = None,
    ) -> None:
        self.m = len(capacities)
        self.n = len(demands)
        self.capacities = capacities
        self.demands = demands
        self.fixed_costs = fixed_costs
        self.assignment_costs = assignment_costs

        self.max_iterations = max_iterations
        self.alpha = alpha
        self.epsilon = epsilon
        self.beta = beta
        self.max_stagnation = max_stagnation
        self.tabu_tenure_min = tabu_tenure_min
        self.tabu_tenure_max = tabu_tenure_max
        self.rng = random.Random(random_seed)

        # Tabu structure: (customer, previous_facility) -> expiration iteration
        self.tabu_dict: Dict[Tuple[int, int], int] = {}

    # ------------------------------------------------------------------ #
    # State helpers                                                      #
    # ------------------------------------------------------------------ #
    def _build_state(self, initial_solution: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build an internal mutable state from the given solution dictionary.
        Assumes initial_solution has 'assignments' mapping customer->facility
        and 'open_facilities' list.
        """
        assignments_map = initial_solution["assignments"]
        assignments = [assignments_map[j] for j in range(self.n)]

        open_set = set(initial_solution["open_facilities"])
        # Ensure facilities with assigned customers are marked open
        for i in assignments:
            open_set.add(i)

        counts = np.zeros(self.m, dtype=int)
        load = np.zeros(self.m, dtype=float)
        for j, i in enumerate(assignments):
            counts[i] += 1
            load[i] += self.demands[j]

        fixed_cost = float(sum(self.fixed_costs[i] for i in open_set))
        assignment_cost = float(sum(self.assignment_costs[assignments[j]][j] for j in range(self.n)))
        violations = np.maximum(load - self.capacities, 0.0)
        total_violation = float(np.sum(violations))
        objective = fixed_cost + assignment_cost + self.alpha * total_violation

        capacity_violations = {
            i: float(violations[i]) for i in range(self.m) if violations[i] > 0
        }

        return {
            "assignments": assignments,  # list[int]
            "open_facilities": sorted(open_set),
            "open_set": open_set,
            "counts": counts,
            "load": load,
            "total_fixed_cost": fixed_cost,
            "total_assignment_cost": assignment_cost,
            "total_violation": total_violation,
            "objective": objective,
            "is_feasible": total_violation == 0.0,
            "capacity_violations": capacity_violations,
            "lower_bound": initial_solution.get("lower_bound"),
        }

    def _clone_solution(self, solution: Dict[str, Any]) -> Dict[str, Any]:
        """
        Lightweight clone for storing best solutions.
        """
        return {
            "open_facilities": list(solution["open_facilities"]),
            "assignments": {j: solution["assignments"][j] for j in range(self.n)},
            "total_fixed_cost": solution["total_fixed_cost"],
            "total_assignment_cost": solution["total_assignment_cost"],
            "total_cost": solution["total_fixed_cost"] + solution["total_assignment_cost"],
            "objective": solution["objective"],
            "is_feasible": solution["is_feasible"],
            "capacity_violations": dict(solution["capacity_violations"]),
            "lower_bound": solution.get("lower_bound"),
        }

    def _update_alpha(self, feasible: bool) -> None:
        """
        Simple dynamic penalty update.
        Increase alpha when infeasible, decrease when feasible.
        """
        factor = 1.0 + self.epsilon
        alpha_min, alpha_max = 1e-6, 1e9  # Clamp to avoid overflow / stagnation
        if feasible:
            self.alpha = max(alpha_min, self.alpha / factor)
        else:
            self.alpha = min(alpha_max, self.alpha * factor)

    # ------------------------------------------------------------------ #
    # Neighborhood generation                                            #
    # ------------------------------------------------------------------ #
    def _sample_customers(self) -> List[int]:
        sample_size = max(1, math.ceil(self.beta * self.n))
        return self.rng.sample(list(range(self.n)), sample_size)

    def _relocate_moves(self, solution: Dict[str, Any]) -> List[Tuple[str, Tuple[int, int, int]]]:
        moves = []
        assignments = solution["assignments"]
        sampled = self._sample_customers()
        for j in sampled:
            k = assignments[j]
            for l in range(self.m):
                if l == k:
                    continue
                moves.append(("relocate", (j, k, l)))
        return moves

    def _swap_moves(self, solution: Dict[str, Any]) -> List[Tuple[str, Tuple[int, int, int, int]]]:
        moves = []
        assignments = solution["assignments"]
        sampled = self._sample_customers()
        if len(sampled) < 2:
            return moves
        for idx1 in range(len(sampled)):
            for idx2 in range(idx1 + 1, len(sampled)):
                j1, j2 = sampled[idx1], sampled[idx2]
                k, l = assignments[j1], assignments[j2]
                if k != l:
                    moves.append(("swap", (j1, j2, k, l)))
        return moves

    # ------------------------------------------------------------------ #
    # Delta evaluation                                                   #
    # ------------------------------------------------------------------ #
    def _delta_violation(self, load_old: float, load_new: float, cap: float) -> float:
        return max(load_new - cap, 0.0) - max(load_old - cap, 0.0)

    def _evaluate_move_delta(
        self, solution: Dict[str, Any], move: Tuple[str, Tuple]
    ) -> Tuple[float, bool, float]:
        """
        Returns (new_objective, new_feasible, delta_objective)
        without modifying the solution.
        """
        move_type, data = move
        assignments = solution["assignments"]
        load = solution["load"]
        counts = solution["counts"]

        current_obj = solution["objective"]
        current_violation = solution["total_violation"]
        current_fixed = solution["total_fixed_cost"]
        current_assign_cost = solution["total_assignment_cost"]

        if move_type == "relocate":
            j, k, l = data
            demand_j = self.demands[j]

            delta_assign = float(self.assignment_costs[l][j] - self.assignment_costs[k][j])

            # Fixed cost delta (strong linking)
            delta_fixed = 0.0
            k_will_empty = counts[k] == 1
            l_closed_now = counts[l] == 0
            if l_closed_now:
                delta_fixed += float(self.fixed_costs[l])
            if k_will_empty:
                delta_fixed -= float(self.fixed_costs[k])

            # Violation delta only on k and l
            load_k_old, load_l_old = load[k], load[l]
            load_k_new = load_k_old - demand_j
            load_l_new = load_l_old + demand_j
            delta_violation = self._delta_violation(load_k_old, load_k_new, self.capacities[k])
            if l != k:
                delta_violation += self._delta_violation(load_l_old, load_l_new, self.capacities[l])
            new_violation = current_violation + delta_violation

            new_assign_cost = current_assign_cost + delta_assign
            new_fixed = current_fixed + delta_fixed
            new_obj = new_fixed + new_assign_cost + self.alpha * new_violation
            return new_obj, new_violation == 0.0, new_obj - current_obj

        elif move_type == "swap":
            j1, j2, k, l = data
            d1, d2 = self.demands[j1], self.demands[j2]

            delta_assign = float(
                (self.assignment_costs[l][j1] - self.assignment_costs[k][j1])
                + (self.assignment_costs[k][j2] - self.assignment_costs[l][j2])
            )
            delta_fixed = 0.0  # k and l stay open

            load_k_old, load_l_old = load[k], load[l]
            load_k_new = load_k_old - d1 + d2
            load_l_new = load_l_old - d2 + d1
            delta_violation = self._delta_violation(load_k_old, load_k_new, self.capacities[k])
            if l != k:
                delta_violation += self._delta_violation(load_l_old, load_l_new, self.capacities[l])
            new_violation = current_violation + delta_violation

            new_assign_cost = current_assign_cost + delta_assign
            new_fixed = current_fixed + delta_fixed
            new_obj = new_fixed + new_assign_cost + self.alpha * new_violation
            return new_obj, new_violation == 0.0, new_obj - current_obj

        return float("inf"), False, float("inf")

    # ------------------------------------------------------------------ #
    # Move application in-place                                          #
    # ------------------------------------------------------------------ #
    def _apply_move_in_place(self, solution: Dict[str, Any], move: Tuple[str, Tuple]) -> None:
        move_type, data = move
        assignments = solution["assignments"]
        load = solution["load"]
        counts = solution["counts"]

        if move_type == "relocate":
            j, k, l = data
            demand_j = self.demands[j]

            # Update assignment cost
            delta_assign = float(self.assignment_costs[l][j] - self.assignment_costs[k][j])
            solution["total_assignment_cost"] += delta_assign

            # Update fixed cost / open set
            l_closed_before = counts[l] == 0
            k_will_empty = counts[k] == 1
            if l_closed_before:
                solution["total_fixed_cost"] += float(self.fixed_costs[l])
                solution["open_set"].add(l)
                solution["open_facilities"].append(l)
            assignments[j] = l
            counts[k] -= 1
            counts[l] += 1
            if k_will_empty:
                solution["total_fixed_cost"] -= float(self.fixed_costs[k])
                solution["open_set"].discard(k)
                solution["open_facilities"] = [f for f in solution["open_facilities"] if f != k]

            # Update loads and violation
            load_k_old, load_l_old = load[k], load[l]
            load[k] -= demand_j
            load[l] += demand_j
            delta_violation = self._delta_violation(load_k_old, load[k], self.capacities[k])
            if l != k:
                delta_violation += self._delta_violation(load_l_old, load[l], self.capacities[l])
            solution["total_violation"] += delta_violation

        elif move_type == "swap":
            j1, j2, k, l = data
            d1, d2 = self.demands[j1], self.demands[j2]

            delta_assign = float(
                (self.assignment_costs[l][j1] - self.assignment_costs[k][j1])
                + (self.assignment_costs[k][j2] - self.assignment_costs[l][j2])
            )
            solution["total_assignment_cost"] += delta_assign

            # No fixed cost change; counts unchanged
            load_k_old, load_l_old = load[k], load[l]
            load[k] = load_k_old - d1 + d2
            load[l] = load_l_old - d2 + d1
            delta_violation = self._delta_violation(load_k_old, load[k], self.capacities[k])
            if l != k:
                delta_violation += self._delta_violation(load_l_old, load[l], self.capacities[l])
            solution["total_violation"] += delta_violation

            assignments[j1], assignments[j2] = l, k

        # Recompute objective and feasibility
        solution["objective"] = (
            solution["total_fixed_cost"]
            + solution["total_assignment_cost"]
            + self.alpha * solution["total_violation"]
        )
        solution["is_feasible"] = solution["total_violation"] == 0.0

        # Refresh capacity violations dictionary only for changed facilities
        viol = solution["capacity_violations"]
        if move_type == "relocate":
            for i in {k, l}:
                excess = solution["load"][i] - self.capacities[i]
                if excess > 0:
                    viol[i] = float(excess)
                elif i in viol:
                    del viol[i]
        else:
            for i in {k, l}:
                excess = solution["load"][i] - self.capacities[i]
                if excess > 0:
                    viol[i] = float(excess)
                elif i in viol:
                    del viol[i]

        solution["open_facilities"].sort()

    # ------------------------------------------------------------------ #
    # Tabu handling with dynamic tenure                                  #
    # ------------------------------------------------------------------ #
    def _is_tabu(self, move: Tuple[str, Tuple], iteration: int) -> bool:
        move_type, data = move
        if move_type == "relocate":
            j, k, _ = data
            expiry = self.tabu_dict.get((j, k), -1)
            return iteration < expiry
        elif move_type == "swap":
            j1, j2, k, l = data
            return iteration < self.tabu_dict.get((j1, k), -1) or iteration < self.tabu_dict.get((j2, l), -1)
        return False

    def _get_tabu_tenure(self) -> int:
        """
        Simple randomized static tabu tenure.
        Returns a random tenure value within the specified range.
        """
        return self.rng.randint(self.tabu_tenure_min, self.tabu_tenure_max)

    def _update_tabu(self, move: Tuple[str, Tuple], iteration: int) -> None:
        move_type, data = move
        tenure = self._get_tabu_tenure()
        if move_type == "relocate":
            j, k, l = data
            self.tabu_dict[(j, k)] = iteration + tenure
        elif move_type == "swap":
            j1, j2, k, l = data
            self.tabu_dict[(j1, k)] = iteration + tenure
            self.tabu_dict[(j2, l)] = iteration + tenure

    # ------------------------------------------------------------------ #
    # Perturbation operators (Section 3.3)                               #
    # ------------------------------------------------------------------ #
    def _reassign_all_to_open(self, solution: Dict[str, Any]) -> None:
        open_f = solution["open_facilities"]
        assignments = solution["assignments"]
        counts = solution["counts"]
        load = solution["load"]

        counts.fill(0)
        load.fill(0.0)
        assign_cost = 0.0

        for j in range(self.n):
            costs = [(self.assignment_costs[i][j], i) for i in open_f]
            _, best_i = min(costs, key=lambda x: x[0])
            assignments[j] = best_i
            counts[best_i] += 1
            load[best_i] += self.demands[j]
            assign_cost += self.assignment_costs[best_i][j]

        solution["total_assignment_cost"] = assign_cost
        violations = np.maximum(load - self.capacities, 0.0)
        solution["total_violation"] = float(np.sum(violations))
        solution["capacity_violations"] = {i: float(violations[i]) for i in range(self.m) if violations[i] > 0}
        solution["total_fixed_cost"] = float(sum(self.fixed_costs[i] for i in open_f))
        solution["objective"] = (
            solution["total_fixed_cost"] + solution["total_assignment_cost"] + self.alpha * solution["total_violation"]
        )
        solution["is_feasible"] = solution["total_violation"] == 0.0

    def _op1_close(self, new_sol: Dict[str, Any]) -> None:
        open_set = set(new_sol["open_facilities"])
        if len(open_set) > 1:
            open_set.remove(self.rng.choice(list(open_set)))
        new_sol["open_facilities"] = sorted(open_set)
        new_sol["open_set"] = set(open_set)

    def _op2_open(self, new_sol: Dict[str, Any]) -> None:
        open_set = set(new_sol["open_facilities"])
        closed = [i for i in range(self.m) if i not in open_set]
        if closed:
            open_set.add(self.rng.choice(closed))
        new_sol["open_facilities"] = sorted(open_set)
        new_sol["open_set"] = set(open_set)

    def _op3_swap_open_close(self, new_sol: Dict[str, Any]) -> None:
        open_set = set(new_sol["open_facilities"])
        closed = [i for i in range(self.m) if i not in open_set]
        if open_set and closed:
            open_set.remove(self.rng.choice(list(open_set)))
            open_set.add(self.rng.choice(closed))
        new_sol["open_facilities"] = sorted(open_set)
        new_sol["open_set"] = set(open_set)

    def _op4_shuffle_assignments(self, new_sol: Dict[str, Any]) -> None:
        # Keep open set; perform a random assignment to diversify
        open_set = set(new_sol["open_facilities"])
        assignments = new_sol["assignments"]
        counts = new_sol["counts"]
        load = new_sol["load"]

        counts.fill(0)
        load.fill(0.0)
        assign_cost = 0.0

        if not open_set:
            return
        open_list = list(open_set)
        for j in range(self.n):
            i = self.rng.choice(open_list)
            assignments[j] = i
            counts[i] += 1
            load[i] += self.demands[j]
            assign_cost += self.assignment_costs[i][j]

        new_sol["open_facilities"] = sorted(open_set)
        new_sol["open_set"] = set(open_set)
        # finalize costs/violations
        self._reassign_all_to_open(new_sol)

    def _op5_close_half(self, new_sol: Dict[str, Any]) -> None:
        open_set = set(new_sol["open_facilities"])
        if len(open_set) > 1:
            k = max(1, len(open_set) // 2)
            to_close = self.rng.sample(list(open_set), k=k)
            for f in to_close:
                if len(open_set) > 1:
                    open_set.discard(f)
        new_sol["open_facilities"] = sorted(open_set)
        new_sol["open_set"] = set(open_set)

    def _op6_close1_open2(self, new_sol: Dict[str, Any]) -> None:
        open_set = set(new_sol["open_facilities"])
        closed = [i for i in range(self.m) if i not in open_set]
        if open_set:
            open_set.discard(self.rng.choice(list(open_set)))
        if closed:
            add_count = min(2, len(closed))
            open_set.update(self.rng.sample(closed, k=add_count))
        new_sol["open_facilities"] = sorted(open_set)
        new_sol["open_set"] = set(open_set)

    def _op7_open1_close2(self, new_sol: Dict[str, Any]) -> None:
        open_set = set(new_sol["open_facilities"])
        closed = [i for i in range(self.m) if i not in open_set]
        if closed:
            open_set.add(self.rng.choice(closed))
        close_count = min(2, max(0, len(open_set) - 1))
        if close_count > 0:
            to_close = self.rng.sample(list(open_set), k=close_count)
            for f in to_close:
                if len(open_set) > 1:
                    open_set.discard(f)
        new_sol["open_facilities"] = sorted(open_set)
        new_sol["open_set"] = set(open_set)

    def perturb(self, solution: Dict[str, Any], stagnation_counter: int) -> Dict[str, Any]:
        """
        Deterministic perturbation strategy.
        - If stagnation_counter < max_stagnation: Randomly choose from Simple Operators (1-5)
        - Else (stagnation reached): FORCE Operator 7 (Open 1, Close 2) to reduce fixed costs
        Always uses sets to avoid duplicates and reassigns at the end.
        """
        new_sol = deepcopy(solution)
        new_sol["open_facilities"] = sorted(set(new_sol.get("open_facilities", [])))
        new_sol["open_set"] = set(new_sol["open_facilities"])

        simple_ops = [
            self._op1_close,
            self._op2_open,
            self._op3_swap_open_close,
            self._op4_shuffle_assignments,
            self._op5_close_half,
        ]

        if stagnation_counter < self.max_stagnation:
            # Use Simple Operators randomly
            op = self.rng.choice(simple_ops)
        else:
            op = self._op7_open1_close2

        op(new_sol)
        # Ensure full recomputation and duplicate safety
        new_sol["open_facilities"] = sorted(set(new_sol.get("open_facilities", [])))
        new_sol["open_set"] = set(new_sol["open_facilities"])
        self._reassign_all_to_open(new_sol)
        return new_sol

    def _greedy_drop(self, solution: Dict[str, Any]) -> Dict[str, Any]:
        """
        Post-optimization: iteratively try closing open facilities (high fixed
        cost first). Keep closures that remain feasible and strictly improve
        the objective. Returns a cloned best solution.
        """
        best = self._build_state(solution)
        improved = True

        while improved:
            improved = False
            candidates = list(best["open_facilities"])
            # try higher fixed-cost facilities first
            candidates.sort(key=lambda f: -self.fixed_costs[f])

            for f in candidates:
                if len(best["open_facilities"]) <= 1:
                    continue

                trial = deepcopy(best)
                open_set = set(trial["open_facilities"])
                open_set.discard(f)
                trial["open_facilities"] = sorted(open_set)
                trial["open_set"] = set(open_set)

                self._reassign_all_to_open(trial)

                if trial["is_feasible"] and trial["objective"] < best["objective"]:
                    best = trial
                    improved = True
                    break  # restart with updated best

        return self._clone_solution(best)

    # ------------------------------------------------------------------ #
    # Reporting                                                          #
    # ------------------------------------------------------------------ #
    def print_detailed_report(self, solution: Dict[str, Any]) -> None:
        """
        Print a detailed report of a (feasible or infeasible) solution.
        Shows global summary, per-facility usage, and violations.
        """
        open_facilities = solution.get("open_facilities", [])
        assignments = solution.get("assignments", {})

        # Build per-facility customer lists and loads
        facility_customers: Dict[int, List[Tuple[int, float, float]]] = {i: [] for i in open_facilities}
        load = {i: 0.0 for i in open_facilities}
        for j, i in assignments.items():
            if i not in facility_customers:
                # In case assignment references a facility not marked open
                facility_customers[i] = []
                load[i] = 0.0
            dem_j = float(self.demands[j])
            cost_ij = float(self.assignment_costs[i][j])
            facility_customers[i].append((j, dem_j, cost_ij))
            load[i] = load.get(i, 0.0) + dem_j

        total_fixed = float(solution.get("total_fixed_cost", 0.0))
        total_assign = float(solution.get("total_assignment_cost", 0.0))
        total_cost = total_fixed + total_assign
        feasible = solution.get("is_feasible", False)
        lb = solution.get("lower_bound")
        if lb is None or lb == 0:
            gap_str = "N/A (lower_bound not provided)"
        else:
            gap_abs = total_cost - lb
            gap_pct = 100.0 * gap_abs / lb
            gap_str = f"{gap_pct:.2f}% (abs: {gap_abs:.2f} vs LB={lb:.2f})"

        print("-" * 60)
        print("SSCFLP TABU SEARCH REPORT")
        print("-" * 60)
        print(f"Total Cost: {total_cost:.2f} (Fixed: {total_fixed:.2f}, Assignment: {total_assign:.2f})")
        print(f"Feasible: {feasible}")
        print(f"Open Facilities: {len(open_facilities)}")
        print(f"Lower Bound Gap: {gap_str}")
        print("-" * 60)

        for i in sorted(facility_customers.keys()):
            cap = float(self.capacities[i])
            used = load[i]
            pct = (used / cap * 100) if cap > 0 else 0.0
            custs = facility_customers[i]
            print(f"FACILITY {i} (Cap: {cap:.2f}, Fixed: {float(self.fixed_costs[i]):.2f})")
            print(f"  Status: OPEN")
            print(f"  Load: {used:.2f} / {cap:.2f} ({pct:.2f}%)")
            print(f"  Assigned Customers (Total: {len(custs)}):")
            for (cust, dem, cost) in custs:
                print(f"    - Cust {cust} (Dem: {dem:.2f}, Cost: {cost:.2f})")
            print("-" * 60)

        if not feasible:
            viols = solution.get("capacity_violations", {})
            if viols:
                print("CAPACITY VIOLATIONS:")
                for i in sorted(viols.keys()):
                    print(f"  Facility {i}: exceeds capacity by {float(viols[i]):.2f}")
            else:
                print("CAPACITY VIOLATIONS: None reported but solution marked infeasible.")
            print("-" * 60)

    # ------------------------------------------------------------------ #
    # Main loop                                                          #
    # ------------------------------------------------------------------ #
    def get_neighbors(self, solution: Dict[str, Any]) -> List[Tuple[str, Tuple]]:
        neighbors = self._relocate_moves(solution) + self._swap_moves(solution)
        self.rng.shuffle(neighbors)
        return neighbors

    def run(self, initial_solution: Dict[str, Any], lower_bound: float | None = None) -> Dict[str, Any]:
        """
        Run Iterated Tabu Search starting from an initial solution dictionary.
        Returns the best feasible solution found.
        """
        # If a manual lower bound is provided, inject it before building state
        if lower_bound is not None:
            initial_solution = dict(initial_solution)
            initial_solution["lower_bound"] = lower_bound

        current = self._build_state(initial_solution)
        best_feasible = self._clone_solution(current) if current["is_feasible"] else None
        best_feasible_obj = current["objective"] if current["is_feasible"] else float("inf")
        stagnation = 0

        for it in range(self.max_iterations):
            if it % 100 == 0:
                print(
                    f"Iter {it}: Obj={current['objective']:.2f}, "
                    f"Feasible={current['is_feasible']}, "
                    f"Open={len(current['open_facilities'])}, "
                    f"Viol={current['total_violation']:.2f}"
                )

            neighbors = self.get_neighbors(current)
            if not neighbors:
                break

            best_move = None
            best_move_obj = float("inf")
            best_move_feasible = False

            for move in neighbors:
                tabu = self._is_tabu(move, it)
                new_obj, new_feasible, _ = self._evaluate_move_delta(current, move)

                # Aspiration: allow tabu if it improves best feasible objective
                if tabu and not (new_feasible and new_obj < best_feasible_obj):
                    continue

                if new_obj < best_move_obj:
                    best_move = move
                    best_move_obj = new_obj
                    best_move_feasible = new_feasible

            if best_move is None:
                break

            # Apply selected move in place
            self._apply_move_in_place(current, best_move)
            self._update_tabu(best_move, it)
            self._update_alpha(current["is_feasible"])

            # Track best feasible
            if current["is_feasible"] and current["objective"] < best_feasible_obj:
                best_feasible = self._clone_solution(current)
                best_feasible_obj = current["objective"]
                stagnation = 0
            else:
                stagnation += 1

            # Perturbation on stagnation
            if stagnation >= self.max_stagnation:
                current = self.perturb(current, stagnation)
                stagnation = 0

        if best_feasible is None:
            return self._clone_solution(current)

        # Post-process feasible solution by greedily dropping facilities
        return self._greedy_drop(best_feasible)
