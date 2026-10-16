import { TrainTrack } from 'lucide-react'
import type { TimelineBlock, TimelineKind } from '../types'

const TICKS = [0, 4, 8, 12, 16, 20, 24]

const KIND: Record<TimelineKind, string> = {
  occupancy: 'bg-neon/80 shadow-[0_0_10px_rgba(47,229,138,0.35)]',
  recommended: 'bg-warn shadow-[0_0_10px_rgba(233,182,74,0.3)]',
  pending: 'bg-muted/60',
  conflict: 'hatch-crit',
}

const LEGEND: { kind: TimelineKind; label: string }[] = [
  { kind: 'occupancy', label: 'Train Occupancy' },
  { kind: 'recommended', label: 'Recommended Block' },
  { kind: 'pending', label: 'Pending' },
  { kind: 'conflict', label: 'Conflict' },
]

const hh = (h: number) => `${String(h).padStart(2, '0')}:00`

export default function TrackTimeline({ tracks, blocks }: { tracks: string[]; blocks: TimelineBlock[] }) {
  return (
    <div>
      <div className="relative ml-20 h-5 font-mono text-[10px] text-muted">
        {TICKS.map((h) => (
          <span
            key={h}
            className={`absolute ${h === 0 ? '' : h === 24 ? '-translate-x-full' : '-translate-x-1/2'}`}
            style={{ left: `${(h / 24) * 100}%` }}
          >
            {hh(h)}
          </span>
        ))}
      </div>

      <div>
        {tracks.map((track) => (
          <div key={track} className="flex items-center">
            <div className="flex w-20 shrink-0 items-center gap-2 font-mono text-xs text-ink">
              <TrainTrack className="h-3.5 w-3.5 text-muted" />
              {track}
            </div>
            <div className="relative h-11 flex-1">
              {TICKS.map((h) => (
                <div
                  key={h}
                  className="absolute top-0 h-full border-l border-dashed border-line"
                  style={{ left: `${(h / 24) * 100}%` }}
                />
              ))}
              <div className="absolute left-0 right-0 top-1/2 h-px bg-line" />
              {blocks
                .filter((b) => b.track === track)
                .map((b) => (
                  <div
                    key={b.id}
                    title={b.label}
                    className={`absolute top-1/2 h-3.5 -translate-y-1/2 rounded-full ${KIND[b.kind]}`}
                    style={{
                      left: `${(b.startHour / 24) * 100}%`,
                      width: `${((b.endHour - b.startHour) / 24) * 100}%`,
                      minWidth: 10,
                    }}
                  />
                ))}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 flex flex-wrap gap-x-6 gap-y-2">
        {LEGEND.map((l) => (
          <div key={l.kind} className="flex items-center gap-2 text-xs text-muted">
            <span className={`inline-block h-3 w-5 rounded-sm ${KIND[l.kind]}`} />
            {l.label}
          </div>
        ))}
      </div>
    </div>
  )
}
