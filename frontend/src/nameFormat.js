// Regra do design handoff: nome de arbitro chega a 50 caracteres
// ("Fernando Antonio Mendes de Salles Nascimento Filho"). Em UI apertada
// mostra primeiro nome + ultimo(s) sobrenome(s), nome completo sempre no
// title/tooltip.
// sobrenome composto (Nascimento Filho, Silva Junior...) -- se o ultimo
// token for um desses, o penultimo faz parte do mesmo sobrenome e nao pode
// ser cortado sozinho (ver exemplo do handoff: "Fernando ... Nascimento Filho").
const COMPOUND_SUFFIXES = new Set(["filho", "junior", "júnior", "neto", "sobrinho"]);

export function displayRefereeName(fullName) {
  if (!fullName) return "";
  const parts = fullName.trim().split(/\s+/);
  if (parts.length <= 2) return fullName;
  const last = parts[parts.length - 1];
  if (parts.length > 2 && COMPOUND_SUFFIXES.has(last.toLowerCase())) {
    return `${parts[0]} ${parts[parts.length - 2]} ${last}`;
  }
  return `${parts[0]} ${last}`;
}

// Clube com forma abreviada conhecida (nome oficial passa de 23 caracteres
// em alguns casos, ex. "Fortaleza Esporte Clube"). Fora daqui, o nome
// completo com text-overflow:ellipsis + title da conta.
const CLUB_ABBREVIATIONS = {
  "Fortaleza Esporte Clube": "Fortaleza EC",
  "Athletico Paranaense": "Athletico-PR",
  "Atlético Goianiense": "Atlético-GO",
  "Atlético Mineiro": "Atlético-MG",
  "Red Bull Bragantino": "Bragantino",
};

export function displayClubName(fullName) {
  return CLUB_ABBREVIATIONS[fullName] || fullName;
}

// Crachá = monograma (iniciais + cor de uma paleta fixa, ciclada por indice
// -- nao e a cor do clube). Ver handoff secao "Assets" / edge case 4: sem
// imagem externa de escudo.
const CREST_PALETTE = [
  "oklch(52% 0.1 25)", "oklch(50% 0.1 145)", "oklch(50% 0.1 235)",
  "oklch(55% 0.1 80)", "oklch(50% 0.1 300)", "oklch(48% 0.1 170)",
];

export function crestFor(name, index) {
  const initials = name
    .split(/\s+/)
    .filter((w) => w.length > 2 || w === w.toUpperCase())
    .slice(0, 3)
    .map((w) => w[0])
    .join("")
    .toUpperCase()
    .slice(0, 3) || name.slice(0, 2).toUpperCase();
  return { initials, background: CREST_PALETTE[index % CREST_PALETTE.length] };
}
