// Zonas continentais por posicao (regra mais comum da Serie A recente:
// 20 clubes). Aproximado -- a CBF ajusta detalhe de ano a ano (vagas por
// desempenho na Libertadores/Sul-Americana do ano anterior), mas a faixa
// de posicoes abaixo e a que vale pra maioria das temporadas 2023+.
export const ZONES = [
  { key: "lib-grupos", label: "Libertadores (grupos)", from: 1, to: 4,
    color: "oklch(58% 0.13 145)", bg: "oklch(94% 0.05 145)", text: "oklch(35% 0.1 145)" },
  { key: "lib-playoff", label: "Libertadores (playoff)", from: 5, to: 6,
    color: "oklch(72% 0.13 80)", bg: "oklch(94% 0.07 80)", text: "oklch(42% 0.1 70)" },
  { key: "sul-americana", label: "Sul-Americana", from: 7, to: 12,
    color: "oklch(60% 0.11 235)", bg: "oklch(94% 0.04 235)", text: "oklch(38% 0.1 235)" },
  { key: "rebaixamento", label: "Rebaixamento", from: 17, to: 20,
    color: "oklch(55% 0.16 25)", bg: "oklch(94% 0.06 25)", text: "oklch(40% 0.14 25)" },
];

export function zoneColorForPosition(pos) {
  const zone = ZONES.find((z) => pos >= z.from && pos <= z.to);
  return zone ? zone.color : "transparent";
}
