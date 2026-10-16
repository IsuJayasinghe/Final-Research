import type { YardZones } from '../../api/types'
import { zoneStyle } from '../../theme'

const CELL = 14 // px per stack
const GAP = 2
const SHORT: Record<string, string> = { 'Fast-Access': 'FA', 'Medium-Access': 'MA', 'Long-Term': 'LT', Reefer: 'RF', Hazardous: 'HZ' }

/**
 * Yard Block 01 seen from above: one column per bay (gate end on the left), one cell per row.
 * Each cell is a stack, shaded by how many tiers are filled; bays without a zone are the
 * empty buffer in front of the hazardous bays.
 */
export default function BlockMap({ yard }: { yard: YardZones }) {
  const { bays, rows, tier_height: tiers } = yard.block

  // stack height and zone for every (bay, row)
  const cell = new Map<string, { height: number; zone: keyof typeof zoneStyle }>()
  for (const s of yard.sections) {
    s.stack_heights.forEach((height, i) => {
      const bay = s.first_bay + Math.floor(i / s.rows)
      const row = (i % s.rows) + 1
      cell.set(`${bay}-${row}`, { height, zone: s.zone })
    })
  }
  const bayNumbers = Array.from({ length: bays }, (_, i) => i + 1)
  const width = bays * (CELL + GAP)

  return (
    <div className="overflow-x-auto pb-2">
      <div style={{ width: width + 80 }}>
        {/* zone labels over their bay ranges */}
        <div className="relative mb-2 ml-[80px] h-9" style={{ width }}>
          {yard.sections.map((s) => (
            <div key={s.section} className="absolute top-0 flex flex-col items-center"
                 style={{ left: (s.first_bay - 1) * (CELL + GAP), width: s.bays * (CELL + GAP) - GAP }}>
              <span className={`text-center text-[10px] font-semibold uppercase tracking-wide ${s.bays >= 3 ? 'w-full truncate' : 'whitespace-nowrap'}`}
                    style={{ color: zoneStyle[s.zone].color }} title={`${s.zone}: bays ${s.first_bay}-${s.first_bay + s.bays - 1}`}>
                {s.bays >= 3 ? s.zone : SHORT[s.zone]}
              </span>
              <span className="mt-1 h-2 w-full rounded-t border-x border-t" style={{ borderColor: zoneStyle[s.zone].color }} />
            </div>
          ))}
        </div>

        <div className="flex">
          <div className="flex w-[80px] shrink-0 flex-col justify-between py-1 pr-2 text-right text-[10px] text-muted">
            {Array.from({ length: rows }, (_, r) => <span key={r} style={{ height: CELL }}>Row {r + 1}</span>)}
          </div>
          <div className="grid" style={{ gridTemplateColumns: `repeat(${bays}, ${CELL}px)`, gap: GAP }}>
            {Array.from({ length: rows }, (_, r) => r + 1).flatMap((row) =>
              bayNumbers.map((bay) => {
                const c = cell.get(`${bay}-${row}`)
                if (!c) {
                  return <div key={`${bay}-${row}`} title={`Bay ${bay}: buffer (kept empty)`}
                              style={{ width: CELL, height: CELL, background: 'repeating-linear-gradient(45deg,#1b2a44 0 3px,transparent 3px 6px)' }} />
                }
                return (
                  <div key={`${bay}-${row}`} className="rounded-[2px]"
                       title={`B01-${String(bay).padStart(2, '0')}-${row}: ${c.height}/${tiers} tiers (${c.zone})`}
                       style={c.height === 0
                         ? { width: CELL, height: CELL, border: `1px dashed ${zoneStyle[c.zone].color}55` }
                         : { width: CELL, height: CELL, background: zoneStyle[c.zone].color, opacity: 0.3 + (0.7 * c.height) / tiers }} />
                )
              }),
            )}
          </div>
        </div>

        {/* bay numbers */}
        <div className="ml-[80px] mt-1 grid text-[9px] text-muted" style={{ gridTemplateColumns: `repeat(${bays}, ${CELL}px)`, gap: GAP }}>
          {bayNumbers.map((b) => <span key={b} className="text-center">{b === 1 || b % 5 === 0 ? b : ''}</span>)}
        </div>
      </div>
    </div>
  )
}
