import { Hammer } from 'lucide-react'
import Panel from '../components/Panel'
import StatusBadge from '../components/StatusBadge'

interface Props {
  title: string
  stage: string
  willShow: string
}

export default function PlaceholderPage({ title, stage, willShow }: Props) {
  return (
    <div className="mx-auto max-w-[1280px] space-y-4">
      <h1 className="font-display text-2xl font-bold">{title}</h1>
      <Panel title="Not built yet" icon={Hammer} tag={<StatusBadge tone="idle">{stage}</StatusBadge>}>
        <p className="max-w-xl text-sm text-muted">{willShow}</p>
      </Panel>
    </div>
  )
}
