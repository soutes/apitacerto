import { HINTS, levelLabel } from "./levels";

// Etiqueta de evidencia. Mesmas palavras na aba toda (visao amigavel e
// painel "Como foi criado"); o nivel do backend (forte/fraco/acaso...) nao
// muda, so o rotulo. Cor nunca sozinha: sempre com o texto.
const slug = (level) =>
  level
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/\s+/g, "-");

export default function EvidenceChip({ level, children }) {
  if (!level) return null;
  return (
    <span className={`chip chip-${slug(level)}`} title={HINTS[level]}>
      <i className="chip-dot" aria-hidden="true" />
      {children ?? levelLabel(level)}
    </span>
  );
}
