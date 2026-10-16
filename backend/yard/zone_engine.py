"""
Zone recommendation engine for Component 3 (Smart Container Yard Allocation).

Models ONE yard block (Yard Block 01) - the scope of the proposal. The block is a grid of
bays x rows x tiers; each zone is a range of bays (a section of the block):

    gate end -> Fast-Access | Medium-Access | Long-Term | Reefer (powered bays) | buffer | Hazardous

Used by the notebook (zone demo + stacking simulation) and by the Flask API, so all three
apply exactly the same rules:

1. Dwell-time classification   (FR04): Short-stay < 3 days, Medium-stay 3-7 days, Long-stay > 7 days
2. Yard-type compatibility     (FR05): REEFER -> powered reefer bays, HAZMAT -> isolated hazardous bays
3. Zone recommendation         (FR06): Fast-Access / Medium-Access / Long-Term zone by dwell class
4. Slot assignment (capacity)  (FR06): a free slot in the zone; other general zones only when full
"""
import random

BLOCK_ID = 'B01'
BLOCK_NAME = 'Yard Block 01'
TIER_HEIGHT = 4
ROWS_PER_BAY = 6
HAZARD_BUFFER_BAYS = 2                 # empty bays that separate hazardous cargo from the rest

# Zones of the block, in bay order from the gate end, and the section that holds each one
ZONES = {
    'Fast-Access':   {'section': 'YB01_FAST',   'description': 'Bays nearest the gate, for short-stay containers'},
    'Medium-Access': {'section': 'YB01_MEDIUM', 'description': 'Middle bays, for medium-stay containers'},
    'Long-Term':     {'section': 'YB01_LONG',   'description': 'Far bays, for long-stay containers'},
    'Reefer':        {'section': 'YB01_REEFER', 'description': 'Powered bays for refrigerated containers'},
    'Hazardous':     {'section': 'YB01_HAZARD', 'description': 'Isolated bays for dangerous cargo, behind a buffer'},
}
DWELL_CLASS_ZONE = {'Short-stay': 'Fast-Access', 'Medium-stay': 'Medium-Access', 'Long-stay': 'Long-Term'}
SPECIAL_TYPE_ZONE = {'REEFER': 'Reefer', 'HAZMAT': 'Hazardous'}
GENERAL_ZONES = ['Fast-Access', 'Medium-Access', 'Long-Term']
SECTION_ZONE = {info['section']: zone for zone, info in ZONES.items()}
GENERAL_SECTIONS = [ZONES[z]['section'] for z in GENERAL_ZONES]


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
    return {'zone': zone, 'section': ZONES[zone]['section'], 'dwell_class': dwell_class,
            'compatibility': check_compatibility(container_type), 'reason': reason}


def block_layout(stacks_per_zone, rows=ROWS_PER_BAY):
    """Turn the number of stacks each zone needs into bay ranges of one block.
    stacks_per_zone: {zone name: stacks}. Returns {section: {'first_bay', 'bays', 'rows'}}."""
    layout, bay = {}, 1
    for zone in ZONES:
        if zone == 'Hazardous':
            bay += HAZARD_BUFFER_BAYS
        bays = max(1, -(-int(stacks_per_zone[zone]) // rows))       # ceil, at least one bay
        layout[ZONES[zone]['section']] = {'first_bay': bay, 'bays': bays, 'rows': rows}
        bay += bays
    return layout


class YardState:
    """Stacks of Yard Block 01, with capacity-aware slot assignment.

    layout: {section: {'first_bay', 'bays', 'rows'}} - every (bay, row) is one stack.
    Placement rule (selected on a validation period in the notebook, Cell 9):
    use an empty stack in the recommended zone first; otherwise stack only on a container
    predicted to leave at least `margin_h` hours later, choosing the lowest such stack.
    Other general zones are used only when the recommended zone is full.
    """

    def __init__(self, layout, tier_height=TIER_HEIGHT, rule='empty_first', margin_h=24):
        self.layout = layout
        self.tier_height = tier_height
        self.rule = rule
        self.margin_h = margin_h
        self.stacks, self.stack_section, self.stack_bay, self.stack_row = [], [], [], []
        for section, spec in layout.items():
            for bay in range(spec['first_bay'], spec['first_bay'] + spec['bays']):
                for row in range(1, spec['rows'] + 1):
                    self.stacks.append([])
                    self.stack_section.append(section)
                    self.stack_bay.append(bay)
                    self.stack_row.append(row)
        self.section_stacks = {s: [i for i, ss in enumerate(self.stack_section) if ss == s] for s in layout}
        self.location = {}                        # container id -> stack index
        self.predicted_departure_h = {}           # container id -> predicted departure (hours)
        self.container_type = {}

    @property
    def bay_count(self):
        return max(spec['first_bay'] + spec['bays'] - 1 for spec in self.layout.values())

    def slot_id(self, stack_index, tier):
        """Block-bay-row-tier, e.g. B01-07-3-T2."""
        return f"{BLOCK_ID}-{self.stack_bay[stack_index]:02d}-{self.stack_row[stack_index]}-T{tier}"

    def _best_stack(self, sections, pred_dep_h):
        best, best_score = None, None
        for section in sections:
            for i in self.section_stacks.get(section, []):
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
        """Return the stack index for a container, or None if the block is full."""
        if strategy == 'random':                  # current practice: any free slot, no prediction
            free = [i for i, s in enumerate(self.stacks) if len(s) < self.tier_height]
            return (rng or random).choice(free) if free else None
        preferred = [recommend_zone(container_type, predicted_dwell_days)['section']]
        fallback = [s for s in GENERAL_SECTIONS if s not in preferred]
        for sections in (preferred, fallback):
            i = self._best_stack(sections, pred_dep_h)
            if i is not None:
                return i
        return None

    def _put(self, container_id, container_type, pred_dep_h, i):
        self.predicted_departure_h[container_id] = pred_dep_h
        self.container_type[container_id] = (container_type or 'DRY').upper()
        self.stacks[i].append(container_id)
        self.location[container_id] = i
        return self.slot_id(i, len(self.stacks[i]))

    def place(self, container_id, container_type, predicted_dwell_days, pred_dep_h, strategy='ai', rng=None):
        """Put a container in the block. Returns its slot id (e.g. 'B01-07-3-T2') or None if full."""
        i = self.choose_stack(container_type, predicted_dwell_days, pred_dep_h, strategy, rng)
        return None if i is None else self._put(container_id, container_type, pred_dep_h, i)

    def place_at(self, container_id, container_type, pred_dep_h, section):
        """Manual override: put a container in a chosen zone section."""
        i = self._best_stack([section], pred_dep_h)
        return None if i is None else self._put(container_id, container_type, pred_dep_h, i)

    def place_exact(self, container_id, container_type, pred_dep_h, section, stack_number):
        """Restore a saved allocation into its exact stack (used when loading from the database)."""
        i = self.section_stacks[section][stack_number - 1]
        if len(self.stacks[i]) >= self.tier_height:
            return None
        return self._put(container_id, container_type, pred_dep_h, i)

    def position(self, container_id):
        """(section, stack number within the section, tier) of a container."""
        i = self.location[container_id]
        section = self.stack_section[i]
        return section, self.section_stacks[section].index(i) + 1, self.stacks[i].index(container_id) + 1

    def retrieve(self, container_id):
        """Remove a container. Returns the containers that were on top of it (to be relocated)."""
        stack = self.stacks[self.location.pop(container_id)]
        pos = stack.index(container_id)
        above = stack[pos + 1:]
        del stack[pos:]
        for moved in above:
            self.location.pop(moved, None)
        return above

    def section_of(self, container_id):
        return self.stack_section[self.location[container_id]]

    def zone_occupancy(self):
        """Occupied / total slots per zone."""
        result = {}
        for zone, info in ZONES.items():
            idx = self.section_stacks.get(info['section'], [])
            capacity = len(idx) * self.tier_height
            used = sum(len(self.stacks[i]) for i in idx)
            result[zone] = {'used': used, 'capacity': capacity,
                            'utilization_pct': round(used / capacity * 100, 1) if capacity else 0.0}
        return result
