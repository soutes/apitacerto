// Explicacao que fica embaixo de cada grafico (pedido do usuario): como o
// dado foi construido, metodo, quem criou, por que usamos, como ler.
const ROWS = [
  ["built", "Como foi construído"],
  ["method", "Método"],
  ["origin", "Quem criou / referência"],
  ["why", "Por que usamos"],
  ["read", "Como ler (e limites)"],
];

export default function MethodNote(copy) {
  return (
    <dl className="method-note">
      {ROWS.filter(([key]) => copy[key]).map(([key, label]) => (
        <div className="method-note-row" key={key}>
          <dt>{label}</dt>
          <dd>{copy[key]}</dd>
        </div>
      ))}
    </dl>
  );
}
