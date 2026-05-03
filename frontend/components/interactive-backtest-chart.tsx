"use client";

import { useMemo, useState } from "react";
import type { VisualizationData } from "@/lib/types";

type Props = {
  data: VisualizationData;
};

const width = 1120;
const equityHeight = 360;
const drawdownHeight = 120;
const groupsHeight = 180;
const margin = { top: 24, right: 32, bottom: 34, left: 56 };

const regimeColors: Record<string, string> = {
  risk_on: "rgba(205, 221, 255, 0.08)",
  neutral: "rgba(205, 195, 120, 0.12)",
  risk_off: "rgba(205, 120, 120, 0.12)",
  fast_risk_off: "rgba(205, 120, 160, 0.16)",
};

const lineColors = {
  strategy: "#5266eb",
  SPY: "#c3c3cc",
  QQQ: "#f0b95b",
};

const groups = ["Growth Tech", "Real Assets", "Defensive"];

function toDateValue(date: string) {
  return new Date(date).getTime();
}

function makeScaler(domainMin: number, domainMax: number, rangeMin: number, rangeMax: number) {
  const span = domainMax - domainMin || 1;
  return (value: number) => rangeMin + ((value - domainMin) / span) * (rangeMax - rangeMin);
}

function pathFor(
  points: { date: string; value: number | null }[],
  x: (value: number) => number,
  y: (value: number) => number,
) {
  return points
    .filter((point): point is { date: string; value: number } => point.value !== null && Number.isFinite(point.value))
    .map((point, index) => `${index === 0 ? "M" : "L"} ${x(toDateValue(point.date))} ${y(point.value)}`)
    .join(" ");
}

function formatDate(date: string) {
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric", year: "numeric" }).format(new Date(date));
}

function formatPct(value: number) {
  return `${(value * 100).toFixed(2)}%`;
}

export function InteractiveBacktestChart({ data }: Props) {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);
  const [enabled, setEnabled] = useState({ strategy: true, SPY: true, QQQ: true });

  const geometry = useMemo(() => {
    const times = data.equity.map((point) => toDateValue(point.date));
    const x = makeScaler(Math.min(...times), Math.max(...times), margin.left, width - margin.right);
    const yValues = data.equity.flatMap((point) => [
      point.strategy,
      point.SPY ?? point.strategy,
      point.QQQ ?? point.strategy,
    ]);
    const y = makeScaler(Math.min(...yValues) * 0.96, Math.max(...yValues) * 1.04, equityHeight - margin.bottom, margin.top);
    const ddY = makeScaler(
      Math.min(...data.drawdown.map((point) => point.value)) * 1.05,
      0,
      drawdownHeight - margin.bottom,
      margin.top,
    );
    return { x, y, ddY };
  }, [data]);

  const hovered = hoverIndex === null ? null : data.equity[hoverIndex];
  const totalHeight = equityHeight + drawdownHeight + groupsHeight;
  const xTicks = data.equity.filter((_, index) => index % Math.ceil(data.equity.length / 6) === 0);

  return (
    <div className="panel overflow-hidden rounded-md">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-lead/35 p-5">
        <div>
          <p className="text-caption uppercase tracking-[0.24em] text-silver">Interactive report</p>
          <h2 className="mt-2 text-[28px] font-[360] text-starlight">Equity, regimes, group rotation, trades.</h2>
        </div>
        <div className="flex flex-wrap gap-2">
          {(["strategy", "SPY", "QQQ"] as const).map((key) => (
            <button
              key={key}
              onClick={() => setEnabled((prev) => ({ ...prev, [key]: !prev[key] }))}
              className={`rounded-[32px] border px-4 py-2 text-caption uppercase tracking-[0.18em] ${
                enabled[key]
                  ? "border-mercury-blue bg-mercury-blue text-pure-white"
                  : "border-lead bg-graphite/50 text-silver"
              }`}
            >
              {key === "strategy" ? "Strategy" : key}
            </button>
          ))}
        </div>
      </div>

      <div className="overflow-x-auto p-4">
        <svg viewBox={`0 0 ${width} ${totalHeight}`} className="min-w-[980px]">
          <g>
            {data.regimes.map((regime) => {
              const x0 = geometry.x(toDateValue(regime.start));
              const x1 = geometry.x(toDateValue(regime.end));
              return (
                <rect
                  key={`${regime.start}-${regime.end}-${regime.regime}`}
                  x={x0}
                  y={margin.top}
                  width={Math.max(1, x1 - x0)}
                  height={equityHeight - margin.top - margin.bottom}
                  fill={regimeColors[regime.regime] ?? "rgba(255,255,255,0.03)"}
                />
              );
            })}

            {enabled.strategy ? (
              <path d={pathFor(data.equity.map((p) => ({ date: p.date, value: p.strategy })), geometry.x, geometry.y)} fill="none" stroke={lineColors.strategy} strokeWidth="3" />
            ) : null}
            {enabled.SPY ? (
              <path d={pathFor(data.equity.map((p) => ({ date: p.date, value: p.SPY ?? null })), geometry.x, geometry.y)} fill="none" stroke={lineColors.SPY} strokeWidth="1.5" opacity="0.75" />
            ) : null}
            {enabled.QQQ ? (
              <path d={pathFor(data.equity.map((p) => ({ date: p.date, value: p.QQQ ?? null })), geometry.x, geometry.y)} fill="none" stroke={lineColors.QQQ} strokeWidth="1.5" opacity="0.9" />
            ) : null}

            {data.equity.map((point, index) => (
              <rect
                key={point.date}
                x={geometry.x(toDateValue(point.date)) - 5}
                y={margin.top}
                width="10"
                height={equityHeight - margin.top - margin.bottom}
                fill="transparent"
                onMouseEnter={() => setHoverIndex(index)}
              />
            ))}

            {hovered ? (
              <g>
                <line
                  x1={geometry.x(toDateValue(hovered.date))}
                  x2={geometry.x(toDateValue(hovered.date))}
                  y1={margin.top}
                  y2={totalHeight - 36}
                  stroke="#ededf3"
                  strokeOpacity="0.35"
                  strokeDasharray="4 4"
                />
                <circle cx={geometry.x(toDateValue(hovered.date))} cy={geometry.y(hovered.strategy)} r="4" fill="#5266eb" />
              </g>
            ) : null}

            {xTicks.map((tick) => (
              <text key={tick.date} x={geometry.x(toDateValue(tick.date))} y={equityHeight - 8} textAnchor="middle" className="fill-silver text-[11px]">
                {tick.date.slice(0, 7)}
              </text>
            ))}
            <text x="12" y="28" className="fill-silver text-[12px]">Growth of $1</text>
          </g>

          <g transform={`translate(0 ${equityHeight})`}>
            <path
              d={`${pathFor(data.drawdown.map((p) => ({ date: p.date, value: p.value })), geometry.x, geometry.ddY)} L ${geometry.x(toDateValue(data.drawdown[data.drawdown.length - 1].date))} ${geometry.ddY(0)} L ${geometry.x(toDateValue(data.drawdown[0].date))} ${geometry.ddY(0)} Z`}
              fill="rgba(239, 68, 68, 0.22)"
              stroke="#ef7777"
              strokeWidth="1"
            />
            <line x1={margin.left} x2={width - margin.right} y1={geometry.ddY(0)} y2={geometry.ddY(0)} stroke="#70707d" opacity="0.4" />
            <text x="12" y="24" className="fill-silver text-[12px]">Drawdown</text>
          </g>

          <g transform={`translate(0 ${equityHeight + drawdownHeight})`}>
            {groups.map((group, groupIndex) => {
              const y = 30 + groupIndex * 45;
              const rows = data.group_timeline.filter((item) => item.group === group && item.held_stocks.length > 0);
              return (
                <g key={group}>
                  <text x="12" y={y + 12} className="fill-silver text-[12px]">{group}</text>
                  {rows.map((row) => {
                    const x0 = geometry.x(toDateValue(row.date));
                    const next = data.group_timeline.find(
                      (candidate) => candidate.group === group && toDateValue(candidate.date) > toDateValue(row.date),
                    );
                    const x1 = next ? geometry.x(toDateValue(next.date)) : x0 + 6;
                    return (
                      <rect
                        key={`${group}-${row.date}`}
                        x={x0}
                        y={y}
                        width={Math.max(4, x1 - x0)}
                        height="18"
                        fill={groupIndex === 0 ? "#5266eb" : groupIndex === 1 ? "#8b7654" : "#5fa58c"}
                        opacity="0.75"
                      >
                        <title>{`${formatDate(row.date)} · ${group}: ${row.held_stocks.join(", ")}`}</title>
                      </rect>
                    );
                  })}
                </g>
              );
            })}
            <text x="12" y="166" className="fill-silver text-[12px]">Hover bars for selected stocks</text>
          </g>
        </svg>
      </div>

      <div className="border-t border-lead/35 p-5">
        {hovered ? (
          <div className="grid gap-3 text-body-sm text-silver md:grid-cols-4">
            <span><b className="text-starlight">{formatDate(hovered.date)}</b></span>
            <span>Strategy: <b className="text-starlight">{hovered.strategy.toFixed(2)}x</b></span>
            <span>SPY: <b className="text-starlight">{hovered.SPY?.toFixed(2) ?? "—"}x</b></span>
            <span>QQQ: <b className="text-starlight">{hovered.QQQ?.toFixed(2) ?? "—"}x</b></span>
          </div>
        ) : (
          <p className="text-body-sm text-silver">Hover over the chart for point-in-time values. Use the pills to toggle lines.</p>
        )}
      </div>
    </div>
  );
}
