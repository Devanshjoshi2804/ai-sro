/**
 * Console palette, from the design.
 *
 * Kept as tokens rather than scattered hex: the console is one continuous
 * surface, and a warehouse floor screen that is nearly-but-not-quite consistent
 * reads as broken.
 */
export const ink = {
  bar: "#1B1C1E",
  barText: "#B9BABC",
  barMuted: "#6C6E71",
  page: "#F6F6F4",
  panel: "#FFFFFF",
  line: "#E3E3E0",
  lineSoft: "#EDEDEA",
  text: "#232528",
  textSoft: "#5A5C60",
  textMuted: "#9A9C9F",
  accent: "#F47B20",
  accentDeep: "#D9640D",
  accentWash: "#FDF0E6",
  good: "#2C5731",
  goodDot: "#4F8F58",
  goodWash: "#E9F1EA",
  info: "#3A5A78",
  infoWash: "#EFF3F7",
  danger: "#E5484D",
} as const;

export const mono = "'JetBrains Mono', ui-monospace, SFMono-Regular, monospace";
