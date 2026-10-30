# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only

from typing import NamedTuple
MAX_DP_STATES = 10000
MAX_DP_TRANSITIONS = 200_000

class KnapsackBudgetExceeded(RuntimeError):
    """Raised when Knapsack exceeds its computational budget"""
    pass

class StateKey(NamedTuple):
    used_space: int
    file_count: int

class StateValue(NamedTuple):
    total_read_rate: float
    selected_indices: tuple[int, ...]

def prune_dominated_states(states):
    """An example:for set(Used Space, Total Read Rate) suppose state A:(3GB, 10), B(5GB, 8), C(4GB, 12). Then A dominates B
       The propose of this function then is:Remove dominated states with the same file count."""
    pruned = {}
    best_read_rate_by_count = {}

    sorted_states = sorted(states.items(), key=lambda item:(item[0].file_count, item[0].used_space)) #let us start from least used space

    for key, value in sorted_states:
        best_rate = best_read_rate_by_count.get(key.file_count, float("-inf"))

        if value.total_read_rate <= best_rate: # Dominate!
            continue

        pruned[key] = value
        best_read_rate_by_count[key.file_count] = value.total_read_rate

    return pruned

def select_files_knapsack(candidates, capacity, max_recommendations, warnings):
    """
    Select files to maximize total read rate. (背包问题+DP)

    Constraints:
        - Total selected size <= capacity
        - Number selected <= max_recommendations
    
    Returns:
        - List of selected candidate rows
    """
    states = {StateKey(used_space=0, file_count=0): StateValue(total_read_rate=0.0, selected_indices=())}
    transition_count = 0

    for index, row in enumerate(candidates): #iterate thru candidates
        next_states = states.copy() # start from last time states, avoiding choosing file repeatedly

        for key, value in states.items(): # try add this file to every DP state
            transition_count += 1

            if transition_count > MAX_DP_TRANSITIONS:
                raise KnapsackBudgetExceeded("DP transition budget exceeded")
            
            new_space = key.used_space + row["size"]
            new_count = key.file_count + 1
            new_value = value.total_read_rate + row["read_rate"]

            if new_space > capacity or new_count > max_recommendations:
                continue

            new_key = StateKey(used_space=new_space, file_count=new_count)

            new_state = StateValue(total_read_rate=new_value, selected_indices=value.selected_indices + (index,))

            existing = next_states.get(new_key)

            if existing is None or new_state.total_read_rate > existing.total_read_rate: # if no same StateKey in saved States or curr read rate value is higher
                next_states[new_key] = new_state

                if len(next_states) > MAX_DP_STATES:
                    raise KnapsackBudgetExceeded("DP state budget exceeded")

        states = prune_dominated_states(next_states)

    # Select the best state: maximize read rate, then minimize used space and file count.
    _, best_state = max(states.items(), key=lambda item: (item[1].total_read_rate, -item[0].used_space, -item[0].file_count)) 
    selected = [candidates[index] for index in best_state.selected_indices]

    return selected
