type MetricCardProps = {
  label: string;
  value: string;
  detail?: string;
};

export function MetricCard({ label, value, detail }: MetricCardProps) {
  return (
    <div className="border-b border-lead/55 py-6">
      <p className="text-caption uppercase tracking-[0.24px] text-silver">{label}</p>
      <p className="mt-3 font-display text-heading-sm font-[360] leading-tight text-starlight">
        {value}
      </p>
      {detail ? <p className="mt-2 text-body-sm text-silver">{detail}</p> : null}
    </div>
  );
}
