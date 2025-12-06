import numpy as np
import pulp


class SSCFLPLowerBound:
    """
    Class to calculate the Lower Bound of the Single Source Capacitated 
    Facility Location Problem (SSCFLP) using LP Relaxation.
    """
    
    def __init__(self, num_facilities, num_customers, capacities, demands, 
                 fixed_costs, assignment_costs):
        """
        Initialize the SSCFLP Lower Bound solver.
        
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
        
        # Solution variables (will be set after solve)
        self.x = None
        self.y = None
        self.prob = None
        self.objective_value = None
        
    def solve(self):
        """
        Solve the LP relaxation of the SSCFLP problem.
        
        Returns:
        --------
        float
            The optimized objective function value (lower bound)
        """
        # Initialize the problem
        self.prob = pulp.LpProblem("SSCFLP_LowerBound", pulp.LpMinimize)
        
        # Decision variables
        # x[i][j]: Fraction of customer j served by facility i (continuous, 0 <= x <= 1)
        self.x = [[pulp.LpVariable(f"x_{i}_{j}", lowBound=0, upBound=1, cat='Continuous')
              for j in range(self.num_customers)]
             for i in range(self.num_facilities)]
        
        # y[i]: Fraction of facility i being open (continuous, 0 <= y <= 1)
        self.y = [pulp.LpVariable(f"y_{i}", lowBound=0, upBound=1, cat='Continuous')
             for i in range(self.num_facilities)]
        
        # Objective function: Minimize Fixed Costs + Assignment Costs
        self.prob += (pulp.lpSum([self.fixed_costs[i] * self.y[i] for i in range(self.num_facilities)]) +
                 pulp.lpSum([self.assignment_costs[i][j] * self.x[i][j] 
                            for i in range(self.num_facilities)
                            for j in range(self.num_customers)]))
        
        # Constraint 1: Assignment - Each customer must be fully served
        for j in range(self.num_customers):
            self.prob += pulp.lpSum([self.x[i][j] for i in range(self.num_facilities)]) == 1
        
        # Constraint 2: Capacity - Total demand served by facility i cannot exceed capacity * y_i
        for i in range(self.num_facilities):
            self.prob += (pulp.lpSum([self.demands[j] * self.x[i][j] for j in range(self.num_customers)]) 
                    <= self.capacities[i] * self.y[i])
        
        # Constraint 3: Strong Linking - x[i][j] <= y[i] for all i, j
        for i in range(self.num_facilities):
            for j in range(self.num_customers):
                self.prob += self.x[i][j] <= self.y[i]
        
        # Solve the problem (suppress output)
        self.prob.solve(pulp.PULP_CBC_CMD(msg=0))
        
        # Store the objective value
        self.objective_value = pulp.value(self.prob.objective)
        
        # Return the objective value
        return self.objective_value
    
    def get_open_facilities(self, threshold=1e-6):
        """
        Get list of open facilities (y[i] > threshold).
        
        Parameters:
        -----------
        threshold : float
            Minimum value of y[i] to consider facility as open (default: 1e-6)
        
        Returns:
        --------
        list
            List of facility indices that are open
        """
        if self.y is None:
            raise ValueError("Problem not solved yet. Call solve() first.")
        
        open_facilities = []
        for i in range(self.num_facilities):
            y_value = pulp.value(self.y[i])
            if y_value is not None and y_value > threshold:
                open_facilities.append(i)
        return open_facilities
    
    def get_customer_assignments(self, threshold=1e-6):
        """
        Get customer assignments to facilities.
        
        Parameters:
        -----------
        threshold : float
            Minimum value of x[i][j] to consider as assignment (default: 1e-6)
        
        Returns:
        --------
        dict
            Dictionary mapping customer index to list of (facility_index, assignment_fraction) tuples
        """
        if self.x is None:
            raise ValueError("Problem not solved yet. Call solve() first.")
        
        assignments = {}
        for j in range(self.num_customers):
            customer_assignments = []
            for i in range(self.num_facilities):
                x_value = pulp.value(self.x[i][j])
                if x_value is not None and x_value > threshold:
                    customer_assignments.append((i, x_value))
            assignments[j] = customer_assignments
        return assignments
    
    def get_facility_utilization(self):
        """
        Get capacity utilization for each facility.
        
        Returns:
        --------
        dict
            Dictionary mapping facility index to (used_capacity, total_capacity, utilization_percentage)
        """
        if self.x is None:
            raise ValueError("Problem not solved yet. Call solve() first.")
        
        utilization = {}
        for i in range(self.num_facilities):
            used_capacity = sum(pulp.value(self.x[i][j]) * self.demands[j] 
                               for j in range(self.num_customers)
                               if pulp.value(self.x[i][j]) is not None)
            total_capacity = self.capacities[i]
            util_pct = (used_capacity / total_capacity * 100) if total_capacity > 0 else 0
            utilization[i] = (used_capacity, total_capacity, util_pct)
        return utilization
    
    def get_total_demand_satisfied(self):
        """
        Get total demand satisfied.
        
        Returns:
        --------
        float
            Total demand satisfied
        """
        return sum(self.demands)
    
    def get_total_capacity_used(self):
        """
        Get total capacity used across all facilities.
        
        Returns:
        --------
        float
            Total capacity used
        """
        if self.x is None:
            raise ValueError("Problem not solved yet. Call solve() first.")
        
        total_used = 0
        for i in range(self.num_facilities):
            for j in range(self.num_customers):
                x_value = pulp.value(self.x[i][j])
                if x_value is not None:
                    total_used += x_value * self.demands[j]
        return total_used
    
    def print_solution_summary(self, threshold=1e-6):
        """
        Print a comprehensive summary of the solution.
        
        Parameters:
        -----------
        threshold : float
            Minimum value to consider as significant (default: 1e-6)
        """
        if self.objective_value is None:
            raise ValueError("Problem not solved yet. Call solve() first.")
        
        print("=" * 60)
        print("SSCFLP LP RELAXATION SOLUTION SUMMARY")
        print("=" * 60)
        print(f"\nObjective Value (Lower Bound): {self.objective_value:.2f}")
        
        # Open facilities
        open_facilities = self.get_open_facilities(threshold)
        print(f"\nOpen Facilities: {len(open_facilities)}")
        print(f"Facility Indices: {open_facilities}")
        
        # Total demand and capacity
        total_demand = self.get_total_demand_satisfied()
        total_capacity_used = self.get_total_capacity_used()
        total_capacity_available = sum(self.capacities)
        
        print(f"\nTotal Demand: {total_demand:.2f}")
        print(f"Total Capacity Used: {total_capacity_used:.2f}")
        print(f"Total Capacity Available: {total_capacity_available:.2f}")
        print(f"Capacity Utilization Rate: {total_capacity_used/total_capacity_available*100:.2f}%")
        
        # Facility utilization
        print(f"\nFacility Capacity Utilization:")
        utilization = self.get_facility_utilization()
        for i in open_facilities:
            used, total, pct = utilization[i]
            print(f"  Facility {i}: {used:.2f} / {total:.2f} ({pct:.2f}%)")
        
        # Customer assignments
        print(f"\nCustomer Assignments:")
        assignments = self.get_customer_assignments(threshold)
        for j in range(self.num_customers):
            customer_assigns = assignments[j]
            if customer_assigns:
                assign_str = ", ".join([f"Facility {i} ({frac:.3f})" for i, frac in customer_assigns])
                print(f"  Customer {j}: {assign_str}")
        
        print("=" * 60)

