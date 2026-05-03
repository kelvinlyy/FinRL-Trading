"use client";

import { useCallback, useMemo, useState } from "react";
import type { DrawdownPoint, EquityPoint, GroupActivation, VisualizationData } from "@/lib/types";

type Props = {
  data: VisualizationData;
};

type SeriesKey = "strategy" | "SPY" | "QQQ";

const width = 1120;
const equityHeight = 360;
const drawdownHeight = 120;
const groupsHeight = 180;
/** Room for Y-axis tick labels (multiplier + $); keep text inside viewBox. */
const margin = { top: 24, right: 32, bottom: 34, left: 118 };
/** Group timeline: reserve left column for row titles so labels sit clear of bar tracks. */
const GROUP_LABEL_GUTTER = 172;

const regimeColors: Record<string, string> = {
  risk_on: "rgba(205, 221, 255, 0.08)",
  neutral: "rgba(205, 195, 120, 0.12)",
  risk_off: "rgba(205, 120, 120, 0.12)",
  fast_risk_off: "rgba(205, 120, 160, 0.16)",
};

const LINE_COLORS: Record<SeriesKey, string> = {
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

/** Nice tick values between domainMin and domainMax (for equity multiplier domain). */
function equityTickValues(domainMin: number, domainMax: number, count = 5): number[] {
  const span = domainMax - domainMin || 1;
  const roughStep = span / Math.max(1, count - 1);
  const pow10 = 10 ** Math.floor(Math.log10(roughStep));
  const candidates = [1, 2, 5, 10].map((m) => m * pow10);
  const step = candidates.find((s) => span / s <= count + 2) ?? roughStep;
  const start = Math.ceil(domainMin / step) * step;
  const ticks: number[] = [];
  for (let v = start; v <= domainMax + step * 0.01; v += step) {
    ticks.push(Number(v.toPrecision(6)));
    if (ticks.length > 12) break;
  }
  if (ticks.length === 0 || ticks[0] > domainMin + step * 0.01) {
    const floorStart = Math.floor(domainMin / step) * step;
    if (!ticks.includes(floorStart)) ticks.unshift(floorStart);
  }
  return ticks.filter((t) => t >= domainMin - 1e-9 && t <= domainMax + 1e-9).slice(0, 8);
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
  const sign = value > 0 ? "+" : "";
  return `${sign}${(value * 100).toFixed(2)}%`;
}

function formatUsd(value: number) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(value);
}

/** Shorter axis labels so two-value ticks stay on one line within the left margin. */
function formatUsdAxis(value: number) {
  const abs = Math.abs(value);
  if (abs >= 1_000_000) return `$${(value / 1_000_000).toFixed(2)}M`;
  if (abs >= 10_000) return `$${Math.round(value / 1000)}k`;
  if (abs >= 1000) return `$${(value / 1000).toFixed(1)}k`;
  return formatUsd(value);
}

function seriesValue(point: EquityPoint, key: SeriesKey): number | null {
  if (key === "strategy") return point.strategy;
  const v = point[key];
  return v === undefined || v === null ? null : v;
}

/** Same formula as backend when API omits or short-changes drawdown vs equity. */
function drawdownFromEquity(equity: EquityPoint[]): DrawdownPoint[] {
  let peak = -Infinity;
  return equity.map((p) => {
    const v = p.strategy;
    if (!Number.isFinite(v)) {
      return { date: p.date, value: 0 };
    }
    peak = Math.max(peak, v);
    const val = peak > 0 ? (v - peak) / peak : 0;
    return { date: p.date, value: val };
  });
}

type GroupSegment = { start: string; end: string; held_stocks: string[] };

function sameHeldStocks(a: string[], b: string[]) {
  return JSON.stringify([...a].sort()) === JSON.stringify([...b].sort());
}

const DEFAULT_MAX_ACTIVE_GROUPS = 2;

/** Hard cap: never show more than `maxAllowed` groups with holdings on the same date (strategy rule). */
function enforceTimelineMaxGroups(timeline: GroupActivation[], maxAllowed: number): GroupActivation[] {
  const cap = Math.max(1, Math.floor(maxAllowed));
  const byDate = new Map<string, GroupActivation[]>();
  for (const row of timeline) {
    const list = byDate.get(row.date) ?? [];
    list.push(row);
    byDate.set(row.date, list);
  }

  const out: GroupActivation[] = [];
  for (const [, rows] of [...byDate.entries()].sort((a, b) => toDateValue(a[0]) - toDateValue(b[0]))) {
    const withHoldings = rows.filter((r) => r.held_stocks.length > 0);
    if (withHoldings.length <= cap) {
      out.push(...rows);
      continue;
    }
    const ranked = [...withHoldings].sort((a, b) => {
      const wa = a.group_weight_total ?? 0;
      const wb = b.group_weight_total ?? 0;
      if (wb !== wa) return wb - wa;
      return a.group.localeCompare(b.group);
    });
    const keep = new Set(ranked.slice(0, cap).map((r) => r.group));
    for (const row of rows) {
      if (row.held_stocks.length === 0) {
        out.push(row);
      } else if (keep.has(row.group)) {
        out.push(row);
      } else {
        out.push({
          ...row,
          active: false,
          held_stocks: [],
        });
      }
    }
  }
  return out;
}

/**
 * Merge rebalance rows into contiguous runs along the **equity** date index (same cadence as
 * the portfolio weights CSV). Uses consecutive equity rows, not sparse timeline dates.
 *
 * Segment bounds stay on actual rebalance dates only — do not stretch first segment to chart
 * start or last to chart end (that falsely showed three lanes active at the edges).
 */
function buildGroupActivationSegments(
  timeline: GroupActivation[],
  groupName: string,
  equityDates: string[],
): GroupSegment[] {
  const equityIndex = new Map(equityDates.map((d, i) => [d, i]));
  const rows = timeline
    .filter((r) => r.group === groupName && r.held_stocks.length > 0)
    .sort((a, b) => toDateValue(a.date) - toDateValue(b.date));
  if (!rows.length) return [];

  const segments: GroupSegment[] = [];
  let runStart = rows[0].date;
  let runEnd = rows[0].date;
  let runHeld = [...rows[0].held_stocks];

  const flushRun = () => {
    segments.push({ start: runStart, end: runEnd, held_stocks: runHeld });
  };

  for (let i = 1; i < rows.length; i++) {
    const prev = rows[i - 1];
    const cur = rows[i];
    const ri = equityIndex.get(prev.date);
    const rj = equityIndex.get(cur.date);
    const consecutive =
      ri !== undefined &&
      rj !== undefined &&
      rj === ri + 1 &&
      sameHeldStocks(prev.held_stocks, cur.held_stocks);

    if (consecutive) {
      runEnd = cur.date;
    } else {
      flushRun();
      runStart = cur.date;
      runEnd = cur.date;
      runHeld = [...cur.held_stocks];
    }
  }
  flushRun();

  // Do **not** extend `start` to `chartStart`. Doing so made every group's first bar begin at
  // the chart's left edge even when that group had no holdings until a later rebalance — so up
  // to three lanes looked "on" from day one. Segment start stays the first date this group has
  // holdings in the capped timeline.
  return segments;
}

/** Right edge of a bar for segment ending at `endDate` (cover until next equity sample). */
function timelineBarRightX(
  endDate: string,
  equity: { date: string }[],
  groupX: (date: string) => number,
): number {
  const i = equity.findIndex((e) => e.date === endDate);
  if (i >= 0 && i < equity.length - 1) {
    return groupX(equity[i + 1].date);
  }
  if (i === equity.length - 1) {
    const xEnd = groupX(endDate);
    const xPrev = i > 0 ? groupX(equity[i - 1].date) : xEnd - 40;
    return xEnd + Math.max(4, xEnd - xPrev);
  }
  return groupX(endDate) + 8;
}

export function InteractiveBacktestChart({ data }: Props) {
  const initialCapital = data.initial_capital ?? 1000;
  const maxTimelineGroups = data.max_timeline_active_groups ?? DEFAULT_MAX_ACTIVE_GROUPS;
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);
  const [enabled, setEnabled] = useState<Record<SeriesKey, boolean>>({
    strategy: true,
    SPY: true,
    QQQ: true,
  });

  const groupTimeline = useMemo(
    () => enforceTimelineMaxGroups(data.group_timeline, maxTimelineGroups),
    [data.group_timeline, maxTimelineGroups],
  );

  const drawdownSeries = useMemo((): DrawdownPoint[] => {
    const eq = data.equity;
    if (!eq.length) return [];
    const aligned =
      data.drawdown.length === eq.length &&
      data.drawdown.every((d, i) => d.date === eq[i]?.date);
    if (aligned) {
      return data.drawdown;
    }
    return drawdownFromEquity(eq);
  }, [data.equity, data.drawdown]);

  const geometry = useMemo(() => {
    if (!data.equity.length) {
      const noop = (v: number) => v;
      return {
        x: noop,
        y: noop,
        ddY: noop,
        times: [] as number[],
        xDomain: [0, 1] as [number, number],
        yTicks: [] as number[],
        groupX: () => GROUP_LABEL_GUTTER,
        empty: true as const,
      };
    }
    const times = data.equity.map((point) => toDateValue(point.date));
    const tMin = Math.min(...times);
    const tMax = Math.max(...times);
    const x = makeScaler(tMin, tMax, margin.left, width - margin.right);
    const yValues = data.equity.flatMap((point) => [
      point.strategy,
      point.SPY ?? point.strategy,
      point.QQQ ?? point.strategy,
    ]).filter((v) => Number.isFinite(v));
    const yMin = yValues.length ? Math.min(...yValues) * 0.96 : 0;
    const yMax = yValues.length ? Math.max(...yValues) * 1.04 : 1;
    const y = makeScaler(yMin, yMax, equityHeight - margin.bottom, margin.top);
    const ddVals = drawdownSeries.map((p) => p.value).filter((v) => Number.isFinite(v));
    const ddMin = ddVals.length ? Math.min(...ddVals) : 0;
    const ddY = makeScaler(ddMin * 1.05, 0, drawdownHeight - margin.bottom, margin.top);
    const yTicks = equityTickValues(yMin, yMax);
    const equityPlotWidth = width - margin.right - margin.left;
    const groupPlotWidth = width - margin.right - GROUP_LABEL_GUTTER;
    const groupX = (date: string) => {
      const px = x(toDateValue(date));
      const frac = (px - margin.left) / equityPlotWidth;
      return GROUP_LABEL_GUTTER + frac * groupPlotWidth;
    };
    return {
      x,
      y,
      ddY,
      times,
      xDomain: [tMin, tMax] as [number, number],
      yDomain: [yMin, yMax] as [number, number],
      yTicks,
      groupX,
      empty: false as const,
    };
  }, [data, drawdownSeries]);

  const firstPoint = data.equity[0];
  const hovered = hoverIndex !== null && hoverIndex >= 0 ? data.equity[hoverIndex] : null;
  const prevPoint = hoverIndex !== null && hoverIndex > 0 ? data.equity[hoverIndex - 1] : null;

  const resolveHoverIndex = useCallback(
    (svgX: number) => {
      if (!data.equity.length || !geometry.times.length) return null;
      let best = 0;
      let bestDist = Infinity;
      for (let i = 0; i < data.equity.length; i++) {
        const cx = geometry.x(geometry.times[i]);
        const d = Math.abs(cx - svgX);
        if (d < bestDist) {
          bestDist = d;
          best = i;
        }
      }
      return best;
    },
    [data.equity, geometry],
  );

  const onOverlayMove = useCallback(
    (clientX: number, svgEl: SVGSVGElement | null) => {
      if (!svgEl || !data.equity.length) return;
      const rect = svgEl.getBoundingClientRect();
      const vb = svgEl.viewBox.baseVal;
      const ratio = (clientX - rect.left) / rect.width;
      const svgX = ratio * vb.width;
      setHoverIndex(resolveHoverIndex(svgX));
    },
    [data.equity.length, resolveHoverIndex],
  );

  const totalHeight = equityHeight + drawdownHeight + groupsHeight;
  const xTicks = data.equity.filter((_, index) => index % Math.ceil(data.equity.length / 6) === 0);

  const equityDatesOrdered = useMemo(() => data.equity.map((p) => p.date), [data.equity]);

  const groupActivationSegments = useMemo(() => {
    if (!equityDatesOrdered.length) return {} as Record<string, GroupSegment[]>;
    return Object.fromEntries(
      groups.map((g) => [
        g,
        buildGroupActivationSegments(groupTimeline, g, equityDatesOrdered),
      ]),
    ) as Record<string, GroupSegment[]>;
  }, [groupTimeline, equityDatesOrdered]);

  /** Earliest rebalance row where any group shows holdings (after max-groups cap). */
  const firstGroupActivationDate = useMemo(() => {
    let best: string | null = null;
    for (const row of groupTimeline) {
      if (row.held_stocks.length === 0) continue;
      if (!best || toDateValue(row.date) < toDateValue(best)) best = row.date;
    }
    return best;
  }, [groupTimeline]);

  /** End of grey band: API "meaningful" deployment date, else first capped lane date. */
  const meaningfulActivationEnd = useMemo(
    () => data.first_meaningful_group_holdings_date ?? firstGroupActivationDate,
    [data.first_meaningful_group_holdings_date, firstGroupActivationDate],
  );

  const MIN_PRE_ACTIVATION_PX = 72;

  /**
   * Period before meaningful group deployment (top-2 groups hold enough weight — see API).
   * Also uses run.start when before first equity date.
   */
  const preActivationBand = useMemo(() => {
    if (geometry.empty || !data.equity.length) return null;

    const eq0 = data.equity[0].date;
    const runStart = data.run?.start;
    const bandStartDate =
      runStart && toDateValue(runStart) < toDateValue(eq0) ? runStart : eq0;

    const xRightEq = width - margin.right;
    const xRightGrp = width - margin.right;

    if (!meaningfulActivationEnd) {
      const wEq = xRightEq - margin.left;
      const wGrp = xRightGrp - GROUP_LABEL_GUTTER;
      if (wEq < 2 && wGrp < 2) return null;
      return {
        equity: { x: margin.left, width: Math.max(0, wEq) },
        drawdown: { x: margin.left, width: Math.max(0, wEq) },
        groups: { x: GROUP_LABEL_GUTTER, width: Math.max(0, wGrp) },
        caption: "No meaningful group deployment in weights export for this run.",
        title:
          "Grey: no date where top groups hold a meaningful fraction of the book. Equity may still plot.",
      };
    }

    const tAct = toDateValue(meaningfulActivationEnd);
    const tStart = toDateValue(bandStartDate);
    if (tAct <= tStart) return null;

    let xEndEq = geometry.x(toDateValue(meaningfulActivationEnd));
    let xEndGrp = geometry.groupX(meaningfulActivationEnd);

    let x0EqRaw = geometry.x(toDateValue(bandStartDate));
    let x0GrpRaw = geometry.groupX(bandStartDate);
    let x0Eq = Math.max(margin.left, x0EqRaw);
    let x0Grp = Math.max(GROUP_LABEL_GUTTER, x0GrpRaw);

    let wEq = Math.max(0, xEndEq - x0Eq);
    let wGrp = Math.max(0, xEndGrp - x0Grp);
    if (wEq < MIN_PRE_ACTIVATION_PX && xEndEq > margin.left) {
      x0Eq = Math.max(margin.left, xEndEq - MIN_PRE_ACTIVATION_PX);
      wEq = xEndEq - x0Eq;
    }
    if (wGrp < MIN_PRE_ACTIVATION_PX && xEndGrp > GROUP_LABEL_GUTTER) {
      x0Grp = Math.max(GROUP_LABEL_GUTTER, xEndGrp - MIN_PRE_ACTIVATION_PX);
      wGrp = xEndGrp - x0Grp;
    }
    if (wEq < 2 && wGrp < 2) return null;

    const runLabel = runStart ? formatDate(runStart) : "—";
    const wfd = data.weights_first_date;
    const wfdNote = wfd ? ` Weights CSV starts ${formatDate(wfd)}.` : "";
    return {
      equity: { x: x0Eq, width: wEq },
      drawdown: { x: x0Eq, width: wEq },
      groups: { x: x0Grp, width: wGrp },
      caption: `Grey: before meaningful group deployment (${formatDate(meaningfulActivationEnd)}). Chart from ${formatDate(eq0)}; run ${runLabel}.${wfdNote}`,
      title: `Shaded until top-two groups hold meaningful weight (${formatDate(meaningfulActivationEnd)}). First lane tickers may appear earlier on dust rows.${wfdNote}`,
    };
  }, [geometry, data.equity, data.run?.start, data.weights_first_date, meaningfulActivationEnd]);

  const detailRows = useMemo(() => {
    if (!hovered || !firstPoint) return [];
    const rows: { key: SeriesKey; label: string; color: string; enabled: boolean }[] = [
      { key: "strategy", label: "Strategy", color: LINE_COLORS.strategy, enabled: enabled.strategy },
      { key: "SPY", label: "SPY", color: LINE_COLORS.SPY, enabled: enabled.SPY },
      { key: "QQQ", label: "QQQ", color: LINE_COLORS.QQQ, enabled: enabled.QQQ },
    ];
    return rows.map(({ key, label, color, enabled: on }) => {
      const mult = seriesValue(hovered, key);
      const mult0 = seriesValue(firstPoint, key);
      const prevMult = prevPoint ? seriesValue(prevPoint, key) : null;
      if (mult === null || mult0 === null) {
        return { key, label, color, on, dollars: null as string | null, sinceStart: null as string | null, daily: null as string | null };
      }
      const dollars = mult * initialCapital;
      const sinceStart = (mult / mult0 - 1);
      const daily =
        prevMult !== null && prevMult !== 0 && prevPoint ? (mult / prevMult - 1) : null;
      return {
        key,
        label,
        color,
        on,
        dollars: formatUsd(dollars),
        sinceStart: formatPct(sinceStart),
        daily: daily !== null ? formatPct(daily) : "—",
      };
    });
  }, [hovered, firstPoint, prevPoint, enabled, initialCapital]);

  return (
    <div className="panel overflow-hidden rounded-md">
      <div className="border-b border-lead/35 p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-caption uppercase tracking-[0.24em] text-silver">Interactive report</p>
            <h2 className="mt-2 text-[28px] font-[360] text-starlight">Equity, regimes, group rotation, trades.</h2>
            <p className="mt-2 text-body-sm text-silver">
              Portfolio scaled from {formatUsd(initialCapital)} initial funding (growth curve matches backtest normalization).
            </p>
            {preActivationBand ? (
              <p className="mt-3 max-w-3xl text-body-sm text-silver/90" title={preActivationBand.title}>
                <span className="mr-2 inline-block h-3 w-3 rounded-sm align-middle bg-[rgba(90,92,110,0.55)] ring-1 ring-lead/40" aria-hidden />
                {preActivationBand.caption}
              </p>
            ) : null}
          </div>
        </div>

        {/* Legend row sits above the plot so it never overlaps series data */}
        <div className="mt-6 flex flex-wrap items-center gap-3 border-t border-lead/25 pt-5">
          <span className="text-caption uppercase tracking-[0.2em] text-silver">Legend</span>
          {(["strategy", "SPY", "QQQ"] as const).map((key) => {
            const active = enabled[key];
            const hex = LINE_COLORS[key];
            return (
              <button
                key={key}
                type="button"
                onClick={() => setEnabled((prev) => ({ ...prev, [key]: !prev[key] }))}
                className={`rounded-[32px] border-2 px-4 py-2 text-caption uppercase tracking-[0.18em] transition-colors`}
                style={{
                  borderColor: active ? hex : "rgba(156, 163, 175, 0.45)",
                  backgroundColor: active ? `${hex}26` : "rgba(24, 26, 36, 0.5)",
                  color: active ? "#ededf3" : "#9ca3af",
                }}
              >
                <span className="mr-2 inline-block h-2 w-2 rounded-full align-middle" style={{ backgroundColor: active ? hex : "#6b7280" }} />
                {key === "strategy" ? "Strategy" : key}
              </button>
            );
          })}
        </div>
      </div>

      <div className="relative overflow-x-auto p-4">
        <svg
          viewBox={`0 0 ${width} ${totalHeight}`}
          className="min-w-[980px]"
          onMouseLeave={() => setHoverIndex(null)}
        >
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
            {preActivationBand && preActivationBand.equity.width >= 2 ? (
              <rect
                x={preActivationBand.equity.x}
                y={margin.top}
                width={preActivationBand.equity.width}
                height={equityHeight - margin.top - margin.bottom}
                fill="rgba(65, 67, 88, 0.42)"
                stroke="rgba(140, 140, 155, 0.35)"
                strokeWidth={1}
              >
                <title>{preActivationBand.title}</title>
              </rect>
            ) : null}

            {/* Y-axis value labels (multiplier + dollar notionals) */}
            {!geometry.empty &&
              geometry.yTicks.map((tick) => (
                <g key={`yt-${tick}`}>
                  <line
                    x1={margin.left}
                    x2={width - margin.right}
                    y1={geometry.y(tick)}
                    y2={geometry.y(tick)}
                    stroke="#ededf3"
                    strokeOpacity="0.06"
                  />
                  <text
                    x={margin.left - 10}
                    y={geometry.y(tick) + 4}
                    textAnchor="end"
                    className="fill-silver text-[10px] leading-tight"
                  >
                    <tspan x={margin.left - 10} dy="0">
                      {tick.toFixed(2)}×
                    </tspan>
                    <tspan x={margin.left - 10} dy="11" fill="#a8a8b8">
                      {formatUsdAxis(tick * initialCapital)}
                    </tspan>
                  </text>
                </g>
              ))}

            {enabled.strategy ? (
              <path
                d={pathFor(data.equity.map((p) => ({ date: p.date, value: p.strategy })), geometry.x, geometry.y)}
                fill="none"
                stroke={LINE_COLORS.strategy}
                strokeWidth="3"
              />
            ) : null}
            {enabled.SPY ? (
              <path
                d={pathFor(data.equity.map((p) => ({ date: p.date, value: p.SPY ?? null })), geometry.x, geometry.y)}
                fill="none"
                stroke={LINE_COLORS.SPY}
                strokeWidth="1.5"
                opacity="0.85"
              />
            ) : null}
            {enabled.QQQ ? (
              <path
                d={pathFor(data.equity.map((p) => ({ date: p.date, value: p.QQQ ?? null })), geometry.x, geometry.y)}
                fill="none"
                stroke={LINE_COLORS.QQQ}
                strokeWidth="1.5"
                opacity="0.95"
              />
            ) : null}

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
                {enabled.strategy ? (
                  <circle cx={geometry.x(toDateValue(hovered.date))} cy={geometry.y(hovered.strategy)} r="5" fill={LINE_COLORS.strategy} stroke="#0c0e14" strokeWidth="1" />
                ) : null}
                {enabled.SPY && hovered.SPY != null ? (
                  <circle cx={geometry.x(toDateValue(hovered.date))} cy={geometry.y(hovered.SPY)} r="4" fill={LINE_COLORS.SPY} stroke="#0c0e14" strokeWidth="1" />
                ) : null}
                {enabled.QQQ && hovered.QQQ != null ? (
                  <circle cx={geometry.x(toDateValue(hovered.date))} cy={geometry.y(hovered.QQQ)} r="4" fill={LINE_COLORS.QQQ} stroke="#0c0e14" strokeWidth="1" />
                ) : null}
              </g>
            ) : null}

            {/* Interaction overlay — on top of series for accurate scrubbing */}
            <rect
              x={margin.left}
              y={margin.top}
              width={width - margin.left - margin.right}
              height={equityHeight - margin.top - margin.bottom}
              fill="transparent"
              style={{ cursor: "crosshair" }}
              onMouseMove={(e) => onOverlayMove(e.clientX, e.currentTarget.ownerSVGElement)}
            />

            {xTicks.map((tick) => (
              <text key={tick.date} x={geometry.x(toDateValue(tick.date))} y={equityHeight - 8} textAnchor="middle" className="fill-silver text-[11px]">
                {tick.date.slice(0, 7)}
              </text>
            ))}
            <text x={margin.left} y="28" className="fill-silver text-[12px]">
              Growth ({formatUsd(initialCapital)} base)
            </text>
          </g>

          <g transform={`translate(0 ${equityHeight})`}>
            {preActivationBand && preActivationBand.drawdown.width >= 2 ? (
              <rect
                x={preActivationBand.drawdown.x}
                y={margin.top}
                width={preActivationBand.drawdown.width}
                height={drawdownHeight - margin.top - margin.bottom}
                fill="rgba(65, 67, 88, 0.42)"
                stroke="rgba(140, 140, 155, 0.35)"
                strokeWidth={1}
              >
                <title>{preActivationBand.title}</title>
              </rect>
            ) : null}
            {drawdownSeries.length > 0 ? (
              <>
                <path
                  d={`${pathFor(drawdownSeries.map((p) => ({ date: p.date, value: p.value })), geometry.x, geometry.ddY)} L ${geometry.x(toDateValue(drawdownSeries[drawdownSeries.length - 1].date))} ${geometry.ddY(0)} L ${geometry.x(toDateValue(drawdownSeries[0].date))} ${geometry.ddY(0)} Z`}
                  fill="rgba(239, 68, 68, 0.22)"
                  stroke="#ef7777"
                  strokeWidth="1"
                />
                <line x1={margin.left} x2={width - margin.right} y1={geometry.ddY(0)} y2={geometry.ddY(0)} stroke="#70707d" opacity="0.4" />
              </>
            ) : null}
            <text x="12" y="24" className="fill-silver text-[12px]">
              Drawdown
            </text>
          </g>

          <g transform={`translate(0 ${equityHeight + drawdownHeight})`}>
            {preActivationBand && preActivationBand.groups.width >= 2 ? (
              <g>
                <rect
                  x={preActivationBand.groups.x}
                  y={10}
                  width={preActivationBand.groups.width}
                  height={groupsHeight - 28}
                  fill="rgba(65, 67, 88, 0.42)"
                  stroke="rgba(140, 140, 155, 0.35)"
                  strokeWidth={1}
                >
                  <title>{preActivationBand.title}</title>
                </rect>
                <text
                  x={preActivationBand.groups.x + 8}
                  y={26}
                  className="fill-starlight text-[11px] font-[480]"
                  opacity={0.95}
                >
                  Before first group activation
                </text>
              </g>
            ) : null}
            {!geometry.empty ? (
              <line
                x1={GROUP_LABEL_GUTTER}
                x2={GROUP_LABEL_GUTTER}
                y1={12}
                y2={groupsHeight - 18}
                stroke="#ededf3"
                strokeOpacity="0.08"
              />
            ) : null}
            {groups.map((group, groupIndex) => {
              const y = 30 + groupIndex * 45;
              const segments = groupActivationSegments[group] ?? [];
              return (
                <g key={group}>
                  <text
                    x={14}
                    y={y + 12}
                    className="fill-silver text-[12px]"
                    textAnchor="start"
                  >
                    {group}
                  </text>
                  {segments.map((seg) => {
                    const x0 = geometry.groupX(seg.start);
                    const x1 = timelineBarRightX(seg.end, data.equity, geometry.groupX);
                    return (
                      <rect
                        key={`${group}-${seg.start}-${seg.end}`}
                        x={x0}
                        y={y}
                        width={Math.max(4, x1 - x0)}
                        height="18"
                        fill={groupIndex === 0 ? "#5266eb" : groupIndex === 1 ? "#8b7654" : "#5fa58c"}
                        opacity="0.75"
                      >
                        <title>{`${formatDate(seg.start)} → ${formatDate(seg.end)} · ${group}: ${seg.held_stocks.join(", ")}`}</title>
                      </rect>
                    );
                  })}
                </g>
              );
            })}
            <text x={GROUP_LABEL_GUTTER + 4} y="166" className="fill-silver text-[12px]">
              Hover bars for selected stocks
            </text>
          </g>
        </svg>
      </div>

      <div className="border-t border-lead/35 p-5">
        {hovered ? (
          <div className="space-y-4">
            <div className="flex flex-wrap items-baseline gap-3">
              <span className="text-caption uppercase tracking-[0.2em] text-silver">Snapshot</span>
              <b className="text-lg text-starlight">{formatDate(hovered.date)}</b>
              {prevPoint ? (
                <span className="text-body-sm text-silver">vs prior row · daily return shown per series</span>
              ) : (
                <span className="text-body-sm text-silver">First row · no prior daily change</span>
              )}
            </div>
            <div className="grid gap-4 md:grid-cols-3">
              {detailRows.map((row) => (
                <div
                  key={row.key}
                  className="rounded-lg border border-lead/40 bg-graphite/40 px-4 py-3"
                  style={{ borderLeftWidth: 3, borderLeftColor: row.color }}
                >
                  <div className="flex items-center gap-2 text-caption uppercase tracking-[0.18em] text-silver">
                    <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: row.color }} />
                    {row.label}
                    {!row.on ? <span className="normal-case text-silver/70">(hidden)</span> : null}
                  </div>
                  <p className="mt-2 font-display text-xl font-[480] text-starlight">{row.dollars ?? "—"}</p>
                  <p className="mt-1 text-body-sm text-silver">
                    Since start: <span className="text-starlight">{row.sinceStart ?? "—"}</span>
                  </p>
                  <p className="text-body-sm text-silver">
                    Row-to-row: <span className="text-starlight">{row.daily ?? "—"}</span>
                  </p>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <p className="text-body-sm text-silver">Move over the chart for dollar balance, return since start of series, and row-to-row change.</p>
        )}
      </div>
    </div>
  );
}
