export interface ChipOption<T> {
  value: T
  label: string
  colour?: string
  title?: string
}

interface ChipGroupProps<T extends string | number> {
  label: string
  options: ChipOption<T>[]
  value: T
  onChange: (value: T) => void
}

export function ChipGroup<T extends string | number>({ label, options, value, onChange }: ChipGroupProps<T>) {
  return (
    <div className="chips" role="radiogroup" aria-label={label}>
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          role="radio"
          aria-checked={o.value === value}
          className="chip"
          title={o.title}
          onClick={() => onChange(o.value)}
        >
          {o.colour && <span className="swatch" style={{ background: o.colour }} />}
          {o.label}
        </button>
      ))}
    </div>
  )
}
