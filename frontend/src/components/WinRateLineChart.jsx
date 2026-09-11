import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

export default function WinRateLineChart({ data }) {
  return (
    <div className="chart-box">
      <h3>Aproveitamento % por rodada</h3>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="round" label={{ value: "Rodada", position: "insideBottom", offset: -5 }} />
          <YAxis unit="%" />
          <Tooltip formatter={(v) => `${v}%`} labelFormatter={(r) => `Rodada ${r}`} />
          <Line type="monotone" dataKey="winRatePct" stroke="#2f6f4f" strokeWidth={2} dot={false} name="Aproveitamento" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
