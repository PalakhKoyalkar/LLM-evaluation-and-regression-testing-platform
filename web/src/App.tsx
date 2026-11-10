import { useEffect, useState } from 'react'

type Option = { id: string; label: string }
type Score = { scorer: string; value: number }
type Result = {
  id: string
  output: string | null
  error: string | null
  latency_ms: number | null
  cost_usd: number
  scores: Score[]
  test_case: { input: Record<string, unknown>; expected_output: string | null }
}
type Run = {
  id: string
  status: string
  total_cases: number
  completed_cases: number
  error_count: number
  avg_score: number | null
  total_cost_usd: number
  created_at: string
  results?: Result[]
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, { headers: { 'Content-Type': 'application/json' }, ...init })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

function Picker(props: { label: string; options: Option[]; value: string; onChange: (v: string) => void }) {
  return (
    <label>
      {props.label}
      <select value={props.value} onChange={(e) => props.onChange(e.target.value)}>
        <option value="">Select…</option>
        {props.options.map((o) => (
          <option key={o.id} value={o.id}>{o.label}</option>
        ))}
      </select>
    </label>
  )
}

export default function App() {
  const [datasets, setDatasets] = useState<Option[]>([])
  const [prompts, setPrompts] = useState<Option[]>([])
  const [models, setModels] = useState<Option[]>([])
  const [sel, setSel] = useState({ dataset_id: '', prompt_version_id: '', model_config_id: '' })
  const [runs, setRuns] = useState<Run[]>([])
  const [active, setActive] = useState<Run | null>(null)
  const [error, setError] = useState<string | null>(null)

  const loadRuns = () => api<Run[]>('/runs').then(setRuns).catch((e) => setError(String(e)))

  useEffect(() => {
    api<{ id: string; name: string; case_count: number }[]>('/datasets').then((d) =>
      setDatasets(d.map((x) => ({ id: x.id, label: `${x.name} (${x.case_count})` }))))
    api<{ id: string; name: string; version: number }[]>('/prompts').then((d) =>
      setPrompts(d.map((x) => ({ id: x.id, label: `${x.name} v${x.version}` }))))
    api<{ id: string; provider: string; model: string }[]>('/model-configs').then((d) =>
      setModels(d.map((x) => ({ id: x.id, label: `${x.provider}/${x.model}` }))))
    loadRuns()
  }, [])

  // Poll the open run while it's still in progress.
  useEffect(() => {
    if (!active || !['queued', 'running'].includes(active.status)) return
    const t = setTimeout(() => {
      api<Run>(`/runs/${active.id}`).then(setActive)
      loadRuns()
    }, 1500)
    return () => clearTimeout(t)
  }, [active])

  const start = async () => {
    setError(null)
    try {
      const run = await api<Run>('/runs', { method: 'POST', body: JSON.stringify(sel) })
      setActive(run)
      loadRuns()
    } catch (e) {
      setError(String(e))
    }
  }

  const ready = sel.dataset_id && sel.prompt_version_id && sel.model_config_id

  return (
    <main>
      <h1>LLM Eval</h1>

      <section className="controls">
        <Picker label="Dataset" options={datasets} value={sel.dataset_id}
          onChange={(v) => setSel({ ...sel, dataset_id: v })} />
        <Picker label="Prompt" options={prompts} value={sel.prompt_version_id}
          onChange={(v) => setSel({ ...sel, prompt_version_id: v })} />
        <Picker label="Model" options={models} value={sel.model_config_id}
          onChange={(v) => setSel({ ...sel, model_config_id: v })} />
        <button disabled={!ready} onClick={start}>Start run</button>
      </section>
      {error && <p className="error">{error}</p>}

      <h2>Runs</h2>
      <div className="scroll">
        <table>
          <thead>
            <tr><th>Created</th><th>Status</th><th>Progress</th><th>Avg score</th><th>Errors</th><th>Cost</th></tr>
          </thead>
          <tbody>
            {runs.map((r) => (
              <tr key={r.id} className={active?.id === r.id ? 'selected clickable' : 'clickable'}
                onClick={() => api<Run>(`/runs/${r.id}`).then(setActive)}>
                <td>{new Date(r.created_at).toLocaleString()}</td>
                <td><span className={`status ${r.status}`}>{r.status}</span></td>
                <td>{r.completed_cases}/{r.total_cases}</td>
                <td>{r.avg_score?.toFixed(2) ?? '—'}</td>
                <td>{r.error_count}</td>
                <td>${r.total_cost_usd.toFixed(5)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {active && (
        <>
          <h2>Run {active.id.slice(0, 8)} <span className={`status ${active.status}`}>{active.status}</span></h2>
          <div className="scroll">
            <table>
              <thead>
                <tr><th>Input</th><th>Expected</th><th>Output</th><th>Score</th><th>Latency</th><th>Cost</th></tr>
              </thead>
              <tbody>
                {(active.results ?? []).map((res) => (
                  <tr key={res.id}>
                    <td><code>{JSON.stringify(res.test_case.input)}</code></td>
                    <td>{res.test_case.expected_output}</td>
                    <td>{res.error ? <span className="error">{res.error}</span> : res.output}</td>
                    <td>{res.scores.map((s) => `${s.scorer}: ${s.value}`).join(', ') || '—'}</td>
                    <td>{res.latency_ms ?? '—'} ms</td>
                    <td>${res.cost_usd.toFixed(5)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </main>
  )
}
