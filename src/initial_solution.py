import numpy as np


class SSCFLPInitialSolution:
    """
    Class to generate an initial solution for the Single Source Capacitated 
    Facility Location Problem (SSCFLP) using a greedy construction heuristic.
    """
    
    def __init__(self, num_facilities, num_customers, capacities, demands, 
                 fixed_costs, assignment_costs):
        """
        Initialize the SSCFLP Initial Solution constructor.
        
        Parameters:
        -----------
        num_facilities : int
            Number of facilities (m)
        num_customers : int
            Number of customers (n)
        capacities : np.ndarray
            1D array of facility capacities (shape: m)
        demands : np.ndarray
            1D array of customer demands (shape: n)
        fixed_costs : np.ndarray
            1D array of fixed costs for opening facilities (shape: m)
        assignment_costs : np.ndarray
            2D array of assignment costs (shape: m x n)
        """
        self.num_facilities = num_facilities
        self.num_customers = num_customers
        self.capacities = capacities
        self.demands = demands
        self.fixed_costs = fixed_costs
        self.assignment_costs = assignment_costs
        
        # Solution variables (will be set after construct)
        self.open_facilities = None
        self.assignments = None
        self.total_fixed_cost = None
        self.total_assignment_cost = None
        self.total_cost = None
        self.is_feasible = None
        self.capacity_violations = None
        
    def construct(self):
        """
        Execute the greedy construction heuristic.
        
        Algorithm:
        1. Sort facilities by ratio R_i = f_i / b_i (fixed cost / capacity)
        2. Open facilities until total capacity >= total demand
        3. Assign each customer to the nearest (cheapest) open facility
        
        Returns:
        --------
        dict
            Dictionary containing solution details:
            - open_facilities: List of facility indices that are open
            - assignments: Dictionary mapping customer j to facility i
            - total_fixed_cost: Sum of fixed costs for open facilities
            - total_assignment_cost: Sum of assignment costs
            - total_cost: Total cost (fixed + assignment)
            - is_feasible: Boolean indicating if solution is feasible
            - capacity_violations: Dictionary of facility overloads
        """
        # Step 1: Calculate efficiency ratio R_i = f_i / b_i for each facility
        efficiency_ratios = self.fixed_costs / self.capacities
        
        # Step 2: Sort facilities by efficiency ratio (ascending order)
        sorted_facilities = np.argsort(efficiency_ratios)
        
        # Step 3: Open facilities until total capacity >= total demand
        total_demand = np.sum(self.demands)
        self.open_facilities = []
        total_capacity_opened = 0
        
        for facility_idx in sorted_facilities:
            if total_capacity_opened >= total_demand:
                break
            self.open_facilities.append(int(facility_idx))
            total_capacity_opened += self.capacities[facility_idx]
        
        # Convert to set for faster lookup
        open_facilities_set = set(self.open_facilities)
        
        # Step 4: Assign each customer to the nearest (cheapest) open facility
        self.assignments = {}
        facility_demand = np.zeros(self.num_facilities)  # Track demand assigned to each facility
        
        for j in range(self.num_customers):
            # Find the cheapest assignment cost among open facilities
            min_cost = float('inf')
            best_facility = None
            
            for i in self.open_facilities:
                if self.assignment_costs[i][j] < min_cost:
                    min_cost = self.assignment_costs[i][j]
                    best_facility = i
            
            # Assign customer j to best_facility
            if best_facility is not None:
                self.assignments[j] = best_facility
                facility_demand[best_facility] += self.demands[j]
        
        # Step 5: Calculate costs
        self.total_fixed_cost = sum(self.fixed_costs[i] for i in self.open_facilities)
        self.total_assignment_cost = sum(
            self.assignment_costs[self.assignments[j]][j] 
            for j in range(self.num_customers)
        )
        self.total_cost = self.total_fixed_cost + self.total_assignment_cost
        
        # Step 6: Check feasibility and capacity violations
        self.capacity_violations = {}
        for i in self.open_facilities:
            if facility_demand[i] > self.capacities[i]:
                violation = facility_demand[i] - self.capacities[i]
                self.capacity_violations[i] = violation
        
        self.is_feasible = len(self.capacity_violations) == 0
        
        # Return solution summary
        return {
            'open_facilities': self.open_facilities,
            'assignments': self.assignments,
            'total_fixed_cost': self.total_fixed_cost,
            'total_assignment_cost': self.total_assignment_cost,
            'total_cost': self.total_cost,
            'is_feasible': self.is_feasible,
            'capacity_violations': self.capacity_violations
        }
    
    def print_solution_summary(self):
        """
        Print a comprehensive summary of the initial solution.
        """
        if self.open_facilities is None:
            raise ValueError("Solution not constructed yet. Call construct() first.")
        
        print("=" * 60)
        print("SSCFLP INITIAL SOLUTION SUMMARY")
        print("=" * 60)
        print(f"\nTotal Cost: {self.total_cost:.2f}")
        print(f"  - Fixed Costs: {self.total_fixed_cost:.2f}")
        print(f"  - Assignment Costs: {self.total_assignment_cost:.2f}")
        
        print(f"\nFeasibility: {'FEASIBLE' if self.is_feasible else 'INFEASIBLE'}")
        
        if not self.is_feasible:
            print(f"\nCapacity Violations: {len(self.capacity_violations)} facility(ies) overloaded")
            for facility, violation in self.capacity_violations.items():
                print(f"  Facility {facility}: Exceeds capacity by {violation:.2f}")
        
        print(f"\nOpen Facilities: {len(self.open_facilities)}")
        print(f"Facility Indices: {self.open_facilities}")
        
        # Calculate capacity utilization
        facility_demand = np.zeros(self.num_facilities)
        for j, i in self.assignments.items():
            facility_demand[i] += self.demands[j]
        
        print(f"\nFacility Capacity Utilization:")
        for i in self.open_facilities:
            used = facility_demand[i]
            total = self.capacities[i]
            pct = (used / total * 100) if total > 0 else 0
            status = "OVERLOADED" if i in self.capacity_violations else "OK"
            print(f"  Facility {i}: {used:.2f} / {total:.2f} ({pct:.2f}%) - {status}")
        
        print("=" * 60)