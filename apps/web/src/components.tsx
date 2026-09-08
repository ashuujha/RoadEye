import { display } from "./display";
type RecordData = Record<string, any>;
export function Table({
  rows,
  columns,
}: {
  rows?: RecordData[];
  columns?: string[];
}) {
  if (!rows?.length) return <p className="empty">No records in this scope.</p>;
  const keys = columns || Object.keys(rows[0]);
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            {keys.map((k) => (
              <th key={k}>{k.replaceAll("_", " ")}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={r.id || i}>
              {keys.map((k) => (
                <td key={k}>
                  <span
                    className={
                      ["status", "state", "reason"].includes(k)
                        ? `status ${r[k]}`
                        : ""
                    }
                  >
                    {display(r[k])}
                  </span>
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
export function Json({
  value,
  label = "Inspect record",
}: {
  value: unknown;
  label?: string;
}) {
  return (
    <details>
      <summary>{label}</summary>
      <pre>{JSON.stringify(value, null, 2)}</pre>
    </details>
  );
}
export function State({
  query,
}: {
  query: {
    isPending: boolean;
    error: Error | null;
    dataUpdatedAt: number;
    isFetching: boolean;
  };
}) {
  if (query.isPending) return <p role="status">Loading backend data…</p>;
  if (query.error)
    return (
      <p role="alert" className="error">
        {query.error.message} · Last successful data may be stale.
      </p>
    );
  return (
    <p className="meta">
      {query.isFetching ? "Refreshing…" : "Backend response"} · Updated{" "}
      {new Date(query.dataUpdatedAt).toLocaleTimeString()} · Polling every 3
      seconds
    </p>
  );
}
export function Network({
  cameras,
  edges,
  links = [],
  nodes = [],
}: {
  cameras: RecordData[];
  edges: RecordData[];
  links?: RecordData[];
  nodes?: RecordData[];
}) {
  return (
    <figure>
      <svg
        viewBox="0 0 550 215"
        role="img"
        aria-label="Fictional six-camera schematic, observed nodes and inferred connections"
      >
        <defs>
          <marker
            id="arrow"
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="7"
            markerHeight="7"
            orient="auto-start-reverse"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#748499" />
          </marker>
        </defs>
        {edges.map((e) => {
          const a = cameras.find((c) => c.id === e.source),
            b = cameras.find((c) => c.id === e.target);
          if (!a || !b) return null;
          const inferred = links.some(
            (l) => l.source === a.id && l.target === b.id,
          );
          return (
            <line
              key={e.source + e.target}
              x1={a.x}
              y1={a.y}
              x2={b.x - 16}
              y2={b.y}
              stroke={inferred ? "#2459ae" : "#aab4bf"}
              strokeWidth={inferred ? 4 : 2}
              strokeDasharray={inferred ? "6 4" : ""}
              markerEnd="url(#arrow)"
            />
          );
        })}
        {cameras.map((c) => (
          <g key={c.id}>
            <circle
              cx={c.x}
              cy={c.y}
              r="17"
              fill={
                nodes.some((n) => n.camera_id === c.id) ? "#d9efe0" : "#fff"
              }
              stroke="#284661"
              strokeWidth="2"
            />
            <text x={c.x} y={c.y + 5} textAnchor="middle" fontSize="12">
              {c.id}
            </text>
            <text x={c.x} y={c.y + 35} textAnchor="middle" fontSize="11">
              {c.zone_id}
            </text>
          </g>
        ))}
      </svg>
      <figcaption>
        Fictional schematic coordinates. Circles: camera locations. Dashed blue:
        inferred links. Road distances come from the directed graph.
      </figcaption>
    </figure>
  );
}
