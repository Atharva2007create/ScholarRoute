export function fitPercent(score: string) {
  const value = Number(score);
  return Number.isFinite(value) ? Math.max(0, Math.min(100, Math.round(value * 1000) / 10)) : 0;
}

export function humanize(value: string) {
  return value.toLowerCase().split("_").map((word) => word.charAt(0).toUpperCase() + word.slice(1)).join(" ");
}
