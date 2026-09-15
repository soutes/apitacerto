const formatters = {};

function nf(digits) {
  formatters[digits] ??= new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
  return formatters[digits];
}

export const fmt = (x, digits = 2) => (x == null || Number.isNaN(x) ? "—" : nf(digits).format(x));

export const fmtSigned = (x, digits = 2) => (x == null ? "—" : `${x > 0 ? "+" : ""}${fmt(x, digits)}`);

export const fmtPct = (x, digits = 1) => (x == null ? "—" : `${fmt(x, digits)}%`);

export const fmtP = (p) => (p == null ? "—" : p < 0.001 ? "< 0,001" : fmt(p, 3));
