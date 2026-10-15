import type { BlockSummary } from '../../api/types'
import { zoneStyle } from '../../theme'

const CODE: Record<string, string> = {
  Yard_Block_A: 'A', Yard_Block_B: 'B', Yard_Block_C: 'C', Yard_Block_D: 'D',
  Yard_Block_E: 'E', Reefer_Yard_01: 'R', Hazardous_Yard_01: 'H',
}

/** One yard block: every stack is a cell, coloured by how many tiers are filled (0-4). */
export default function BlockGrid({ block }: { block: BlockSummary }) {
  const color = zoneStyle[block.zone].color
  const code = CODE[block.block] ?? block.block
  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between text-xs">
        <span className="font-medium">{block.block.replace(/_/g, ' ')}</span>
        <span className="text-muted">{block.used} / {block.capacity} · {block.utilization_pct}%</span>
      </div>
      <div className="grid gap-[3px]" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(10px, 1fr))' }}>
        {block.stack_heights.map((h, i) => (
          <div
            key={i}
            title={`${code}-${String(i + 1).padStart(3, '0')}: ${h}/${block.tier_height} tiers`}
            className="aspect-square rounded-[2px]"
            style={h === 0
              ? { border: '1px dashed #2b3c5a' }
              : { background: color, opacity: 0.3 + (0.7 * h) / block.tier_height }}
          />
        ))}
      </div>
    </div>
  )
}
