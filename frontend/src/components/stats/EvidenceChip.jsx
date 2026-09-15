const LABELS = {
  forte: "Sinal forte",
  fraco: "Sinal fraco",
  acaso: "Compatível com o acaso",
  "sem comparação": "Sem comparação",
  apoia: "Apoia a hipótese",
  contraria: "Contraria a hipótese",
  "sem evidência": "Sem evidência",
  "sem dado": "Sem dado",
};

const slug = (level) =>
  level
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/\s+/g, "-");

export default function EvidenceChip({ level }) {
  if (!level) return null;
  return <span className={`chip chip-${slug(level)}`}>{LABELS[level] ?? level}</span>;
}
