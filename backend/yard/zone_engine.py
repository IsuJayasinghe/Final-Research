"""
Zone recommendation engine for Component 3 (Smart Container Yard Allocation).

Used by the notebook (zone demo + stacking simulation) and by the Flask API, so all three
apply exactly the same rules:

1. Dwell-time classification   (FR04): Short-stay < 3 days, Medium-stay 3-7 days, Long-stay > 7 days
2. Yard-type compatibility     (FR05): REEFER -> powered reefer yard, HAZMAT -> isolated hazardous yard
3. Zone recommendation         (FR06): Fast-Access / Medium-Access / Long-Term zone by dwell class
4. Slot assignment (capacity)  (FR06): a free slot in the zone; other general blocks only when full
"""
import random

TIER_HEIGHT = 4

# Access zones from the proposal, mapped to the Colombo yard blocks
ZONES = {
    'Fast-Access':   {'blocks': ['Yard_Block_A', 'Yard_Block_B'], 'description': 'Near the gate, for short-stay containers'},
    'Medium-Access': {'blocks': ['Yard_Block_C', 'Yard_Block_D'], 'description': 'Middle of the yard, for medium-stay containers'},
    'Long-Term':     {'blocks': ['Yard_Block_E'],                 'description': 'Back of the yard, for long-stay containers'},
    'Reefer':        {'blocks': ['Reefer_Yard_01'],               'description': 'Powered slots for refrigerated containers'},
    'Hazardous':     {'blocks': ['Hazardous_Yard_01'],            'description': 'Isolated storage for dangerous cargo'},
}
DWELL_CLASS_ZONE = {'Short-stay': 'Fast-Access', 'Medium-stay': 'Medium-Access', 'Long-stay': 'Long-Term'}
SPECIAL_TYPE_ZONE = {'REEFER': 'Reefer', 'HAZMAT': 'Hazardous'}
GENERAL_BLOCKS = [b for z in ('Fast-Access', 'Medium-Access', 'Long-Term') for b in ZONES[z]['blocks']]
BLOCK_ZONE = {b: z for z, info in ZONES.items() for b in info['blocks']}
BLOCK_CODE = {'Yard_Block_A': 'A', 'Yard_Block_B': 'B', 'Yard_Block_C': 'C', 'Yard_Block_D': 'D',
              'Yard_Block_E': 'E', 'Reefer_Yard_01': 'R', 'Hazardous_Yard_01': 'H'}


def classify_dwell(days):
    """FR04: dwell-time category."""
    if days < 3:
        return 'Short-stay'
    if days <= 7:
        return 'Medium-stay'
    return 'Long-stay'


def check_compatibility(container_type):
    """FR05: which special yard type the container needs."""
    container_type = (container_type or 'DRY').upper()
    return {'reefer': container_type == 'REEFER',
            'hazardous': container_type == 'HAZMAT',
            'oversized': container_type == 'OVERSIZED'}


def recommend_zone(container_type, predicted_dwell_days):
    """FR05 + FR06: yard-type compatibility first, then the access zone by dwell class."""
    container_type = (container_type or 'DRY').upper()
    dwell_class = classify_dwell(predicted_dwell_days)
    if container_type in SPECIAL_TYPE_ZONE:
        zone = SPECIAL_TYPE_ZONE[container_type]
        reason = (f"{container_type.title()} container - {ZONES[zone]['description'].lower()} "
                  f"(yard-type rule applies regardless of the {predicted_dwell_days:.1f}-day dwell)")
    else:
        zone = DWELL_CLASS_ZONE[dwell_class]
        reason = f"Predicted dwell {predicted_dwell_days:.1f} days ({dwell_class}) - {ZONES[zone]['description'].lower()}"
        if container_type == 'OVERSIZED':
            reason += '; oversized container'
    return {'zone': zone, 'blocks': ZONES[zone]['blocks'], 'dwell_class': dwell_class,
            'compatibility': check_compatibility(container_type), 'reason': reason}


class YardState:
    """Stacks of containers per yard block, with capacity-aware slot assignment.

    Placement rule (selected on a validation period in the notebook, Cell 9):
    use an empty stack in the recommended zone first; otherwise stack only on a container
    predicted to leave at least `margin_h` hours later, choosing the lowest such stack.
    Other general blocks are used only when the recommended zone is full.
    """

    def __init__(self, stacks_per_block, tier_height=TIER_HEIGHT, rule='empty_first', margin_h=24):
        self.tier_height = tier_height
        self.rule = rule
        self.margin_h = margin_h
        self.stacks, self.stack_block, self.stack_number = [], [], []
        for block, n in stacks_per_block.items():
            for k in range(n):
                self.stacks.append([])
                self.stack_block.append(block)
                self.stack_number.append(k + 1)
        self.block_stacks = {b: [i for i, sb in enumerate(self.stack_block) if sb == b] for b in stacks_per_block}
        self.location = {}                        # container id -> stack index
        self.predicted_departure_h = {}           # container id -> predicted departure (hours)
        self.container_type = {}

    def slot_id(self, stack_index, tier):
        block = self.stack_block[stack_index]
        return f"{BLOCK_CODE.get(block, block)}-{self.stack_number[stack_index]:03d}-T{tier}"

    def _best_stack(self, blocks, pred_dep_h):
        best, best_score = None, None
        for block in blocks:
            for i in self.block_stacks.get(block, []):
                stack = self.stacks[i]
                height = len(stack)
                if height >= self.tier_height:
                    continue
                gap = self.predicted_departure_h[stack[-1]] - pred_dep_h if height else 0
                if self.rule == 'best_fit':       # stack on the closest non-blocking container
                    score = (1, 0) if height == 0 else ((0, gap) if gap >= self.margin_h else (2, -gap))
                else:                             # empty stacks first, then lowest non-blocking stack
                    score = (0, 0, 0) if height == 0 else ((1, height, gap) if gap >= self.margin_h else (2, height, -gap))
                if best_score is None or score < best_score:
                    best, best_score = i, score
        return best

    def choose_stack(self, container_type, predicted_dwell_days, pred_dep_h, strategy='ai', rng=None):
        """Return the stack index for a container, or None if the yard is full."""
        if strategy == 'random':                  # current practice: any free slot, no prediction
            free = [i for i, s in enumerate(self.stacks) if len(s) < self.tier_height]
            return (rng or random).choice(free) if free else None
        preferred = recommend_zone(container_type, predicted_dwell_days)['blocks']
        fallback = [b for b in GENERAL_BLOCKS if b not in preferred]
        for blocks in (preferred, fallback):
            i = self._best_stack(blocks, pred_dep_h)
            if i is not None:
                return i
        return None

    def place(self, container_id, container_type, predicted_dwell_days, pred_dep_h, strategy='ai', rng=None):
        """Put a container in the yard. Returns its slot id (e.g. 'A-012-T2') or None if full."""
        self.predicted_departure_h[container_id] = pred_dep_h
        self.container_type[container_id] = (container_type or 'DRY').upper()
        i = self.choose_stack(container_type, predicted_dwell_days, pred_dep_h, strategy, rng)
        if i is None:
            return None
        self.stacks[i].append(container_id)
        self.location[container_id] = i
        return self.slot_id(i, len(self.stacks[i]))

    def place_at(self, container_id, container_type, pred_dep_h, block):
        """Manual override: put a container in a chosen block (lowest free stack)."""
        self.predicted_departure_h[container_id] = pred_dep_h
        self.container_type[container_id] = (container_type or 'DRY').upper()
        i = self._best_stack([block], pred_dep_h)
        if i is None:
            return None
        self.stacks[i].append(container_id)
        self.location[container_id] = i
        return self.slot_id(i, len(self.stacks[i]))

    def retrieve(self, container_id):
        """Remove a container. Returns the containers that were on top of it (to be relocated)."""
        stack = self.stacks[self.location.pop(container_id)]
        pos = stack.index(container_id)
        above = stack[pos + 1:]
        del stack[pos:]
        for moved in above:
            self.location.pop(moved, None)
        return above

    def block_of(self, container_id):
        return self.stack_block[self.location[container_id]]

    def zone_occupancy(self):
        """Occupied / total slots per zone."""
        result = {}
        for zone, info in ZONES.items():
            idx = [i for b in info['blocks'] for i in self.block_stacks.get(b, [])]
            capacity = len(idx) * self.tier_height
            used = sum(len(self.stacks[i]) for i in idx)
            result[zone] = {'used': used, 'capacity': capacity,
                            'utilization_pct': round(used / capacity * 100, 1) if capacity else 0.0}
        return result
