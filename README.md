# SSCFLP Modelling Toolkit

Heuristics and relaxations for the Single Source Capacitated Facility Location Problem (SSCFLP). The repository contains reusable Python components plus three example notebooks that reproduce experiments on benchmark instances with 51, 55, and 63 facilities/customers.

## What’s inside
- `src/initial_solution.py` – greedy construction heuristic that opens facilities by fixed-cost efficiency and assigns customers to the cheapest open facility.
- `src/relaxation.py` – LP relaxation using PuLP to provide a lower bound and fractional assignments/open decisions.
- `src/tabu_search.py` – iterated tabu search with relocate/swap moves, dynamic tabu tenure, adaptive penalty on capacity violation, and simple perturbation.
- `51-instance.ipynb`, `55-instance.ipynb`, `63-instance.ipynb` – end-to-end runs (load data → LP lower bound → greedy start → tabu search report) for the three benchmark instances.
- `Datasets/SSCFLP{51,55,63}/` – text files for capacities (`cap`), demands (`dem`), fixed opening costs (`fix`), and assignment costs (`cost`).
- `Docs/` – problem statement and reference figures used during the project.

## Prerequisites
- Python 3.10+ (tested with the bundled virtual environment).
- Packages: `numpy`, `pulp`, `jupyter` (or `ipykernel`), `matplotlib` (if you add plots).  
  Install with:
  ```bash
  python -m venv modelling-venv
  modelling-venv\Scripts\activate  # Windows PowerShell
  pip install numpy pulp jupyter
  ```
  You can also reuse the provided `modelling-venv/` by activating it as above.

## Dataset layout
Each instance lives under `Datasets/SSCFLPXX/` and mirrors the paper format:
- `cap XX.txt` and `dem XX.txt`: two-column files where the second column holds capacities/demands (loaded with `usecols=1`).
- `fix XX.txt`: fixed opening costs (second column is used).
- `cost XX.txt`: full assignment cost matrix; the notebooks skip the first column (`skiprows=1` and `[:, 1:]`) to remove row indices.

If you move the project, update the dataset paths in the notebooks to use relative paths, e.g.:
```python
base = Path(__file__).resolve().parent.parent / "Datasets" / "SSCFLP51"
capacities = np.loadtxt(base / "cap 51.txt", usecols=1, dtype=int)
```

## Running the notebooks
1. Activate the environment (see above) and start Jupyter:
   ```bash
   modelling-venv\Scripts\activate
   jupyter notebook
   ```
2. Open one of `51-instance.ipynb`, `55-instance.ipynb`, or `63-instance.ipynb`.
3. Adjust the dataset paths if your checkout location differs from `C:\Users\talha.yilmaz\Desktop\Modelling`.
4. Run all cells. Each notebook will:
   - Load the matching dataset.
   - Solve the LP relaxation (`SSCFLPLowerBound`) and print a detailed bound/assignment summary.
   - Build a greedy initial solution (`SSCFLPInitialSolution`) and report feasibility/violations.
   - Launch iterated tabu search (`SSCFLPTabuSearch.run`) using the lower bound for gap reporting and emit a detailed final report.

## Using the components in your own scripts
```python
import numpy as np
from pathlib import Path
from src.initial_solution import SSCFLPInitialSolution
from src.relaxation import SSCFLPLowerBound
from src.tabu_search import SSCFLPTabuSearch

base = Path("Datasets/SSCFLP51")
capacities = np.loadtxt(base / "cap 51.txt", usecols=1, dtype=int)
demands = np.loadtxt(base / "dem 51.txt", usecols=1, dtype=int)
fixed_costs = np.loadtxt(base / "fix 51.txt", usecols=1, dtype=int)
assignment_costs = np.loadtxt(base / "cost 51.txt", skiprows=1, dtype=int)[:, 1:]

lb_solver = SSCFLPLowerBound(51, 51, capacities, demands, fixed_costs, assignment_costs)
lower_bound = lb_solver.solve()

init = SSCFLPInitialSolution(51, 51, capacities, demands, fixed_costs, assignment_costs).construct()
tabu = SSCFLPTabuSearch(capacities, demands, fixed_costs, assignment_costs, random_seed=61)
best = tabu.run(init, lower_bound=lower_bound)
tabu.print_detailed_report(best)
```

## Parameter notes (tabu search)
- `max_iterations`: outer loop limit (default 300 in code, notebooks use 1000).
- `alpha`: penalty on total capacity violation (adaptive via `_update_alpha`).
- `epsilon`: rate for adapting `alpha`.
- `beta`: fraction of customers sampled per iteration for neighborhood generation.
- `max_stagnation`: perturbation trigger after consecutive non-improving steps.
- `random_seed`: keep runs reproducible.



