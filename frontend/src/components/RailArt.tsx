// Original inline SVG illustrations (no external images).

export function LogoMark({ className = 'h-9 w-9' }: { className?: string }) {
  return (
    <svg viewBox="0 0 40 40" className={className} fill="none" aria-hidden="true">
      <path
        d="M20 3 6 8v10c0 9 6 16 14 19 8-3 14-10 14-19V8L20 3Z"
        stroke="#2fe58a"
        strokeWidth="1.8"
        strokeLinejoin="round"
        fill="rgba(47,229,138,0.08)"
      />
      <path d="M13 31 18 14M27 31 22 14" stroke="#2fe58a" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M15 26h10M16.5 21h7M18 16.5h4" stroke="#2fe58a" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  )
}

export function SidebarTrain() {
  return (
    <svg viewBox="0 0 220 90" className="w-full" fill="none" aria-hidden="true">
      <defs>
        <linearGradient id="st-fade" x1="0" x2="1" y1="0" y2="0">
          <stop offset="0" stopColor="#2fe58a" stopOpacity="0" />
          <stop offset="0.35" stopColor="#2fe58a" stopOpacity="0.9" />
          <stop offset="1" stopColor="#2fe58a" stopOpacity="0.5" />
        </linearGradient>
        <radialGradient id="st-glow" cx="0.5" cy="0.5" r="0.5">
          <stop offset="0" stopColor="#bfffd9" />
          <stop offset="1" stopColor="#2fe58a" stopOpacity="0" />
        </radialGradient>
      </defs>
      <path d="M0 78 L220 62" stroke="url(#st-fade)" strokeWidth="1" opacity="0.7" />
      <path d="M0 86 L220 74" stroke="url(#st-fade)" strokeWidth="1" opacity="0.5" />
      <path
        d="M40 62 L40 40 Q40 34 47 34 L150 34 Q182 34 204 52 L212 60 Q214 64 208 64 L46 64 Q40 64 40 62 Z"
        stroke="url(#st-fade)"
        strokeWidth="1.4"
        fill="rgba(47,229,138,0.05)"
      />
      <path d="M52 42 H168 Q184 42 196 50 H52 Z" stroke="#2fe58a" strokeOpacity="0.55" strokeWidth="1" />
      <path d="M44 56 H208" stroke="#2fe58a" strokeOpacity="0.5" strokeWidth="1" />
      <circle cx="206" cy="58" r="9" fill="url(#st-glow)" />
    </svg>
  )
}

export function HeroArt() {
  return (
    <svg
      viewBox="0 0 900 240"
      preserveAspectRatio="xMidYMax slice"
      className="absolute inset-0 h-full w-full"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="h-sky" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0" stopColor="#06130f" />
          <stop offset="0.55" stopColor="#10261f" />
          <stop offset="0.8" stopColor="#4a3a2a" />
          <stop offset="1" stopColor="#7a5230" />
        </linearGradient>
        <linearGradient id="h-ground" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0" stopColor="#0b1612" />
          <stop offset="1" stopColor="#040907" />
        </linearGradient>
        <linearGradient id="h-body" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0" stopColor="#d6e6e0" />
          <stop offset="0.45" stopColor="#8fa8a0" />
          <stop offset="1" stopColor="#33463f" />
        </linearGradient>
        <radialGradient id="h-light" cx="0.5" cy="0.5" r="0.5">
          <stop offset="0" stopColor="#f4fff8" />
          <stop offset="0.25" stopColor="#7dffb6" stopOpacity="0.9" />
          <stop offset="1" stopColor="#2fe58a" stopOpacity="0" />
        </radialGradient>
        <linearGradient id="h-shade" x1="0" x2="1" y1="0" y2="0">
          <stop offset="0" stopColor="#040907" stopOpacity="0.95" />
          <stop offset="0.5" stopColor="#040907" stopOpacity="0.55" />
          <stop offset="1" stopColor="#040907" stopOpacity="0" />
        </linearGradient>
      </defs>

      <rect width="900" height="240" fill="url(#h-sky)" />
      <path d="M0 150 L90 118 L170 140 L270 100 L380 142 L470 120 L580 148 L690 112 L800 140 L900 122 V190 H0 Z" fill="#0a1713" />
      <path d="M0 165 L120 148 L240 162 L380 146 L520 164 L660 150 L780 163 L900 150 V200 H0 Z" fill="#07110e" />
      <rect y="176" width="900" height="64" fill="url(#h-ground)" />

      <path d="M0 200 H900" stroke="#2c4238" strokeWidth="2" />
      <path d="M0 210 H900" stroke="#2c4238" strokeWidth="2" />
      <g stroke="#1b2c24" strokeWidth="3">
        {Array.from({ length: 30 }).map((_, i) => (
          <path key={i} d={`M${i * 32} 198 L${i * 32 - 6} 214`} />
        ))}
      </g>

      <g transform="translate(262 59) scale(0.7)">
      <path
        d="M330 198 V132 Q330 120 346 120 H640 Q760 120 830 168 L866 188 Q874 198 860 198 Z"
        fill="url(#h-body)"
      />
      <path d="M346 138 H640 Q730 138 790 168 H346 Z" fill="#0a1713" opacity="0.92" />
      <path d="M360 148 H620 Q690 148 740 166 H360 Z" fill="#2bb3a3" opacity="0.25" />
      <path d="M330 178 H862" stroke="#2fe58a" strokeWidth="3" />
      <path d="M330 184 H866" stroke="#2fe58a" strokeWidth="1" opacity="0.6" />
      <g fill="#223730">
        <rect x="360" y="196" width="60" height="8" rx="3" />
        <rect x="520" y="196" width="60" height="8" rx="3" />
        <rect x="700" y="196" width="60" height="8" rx="3" />
      </g>
      <circle cx="862" cy="184" r="34" fill="url(#h-light)" />
      <path d="M866 188 L900 200 H760 Z" fill="#7dffb6" opacity="0.08" />
      </g>

      <rect width="900" height="240" fill="url(#h-shade)" />
    </svg>
  )
}
