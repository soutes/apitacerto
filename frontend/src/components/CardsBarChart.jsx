import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

export default function CardsBarChart({ data }) {
  return (
    <div className="chart-box">
      <h3>Cartoes por rodada</h3>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="round" label={{ value: "Rodada", position: "insideBottom", offset: -5 }} />
          <YAxis allowDecimals={false} />
          <Tooltip />
          <Legend />
          <Bar dataKey="yellow" fill="#e0b400" name="Amarelos" />
          <Bar dataKey="red" fill="#c0392b" name="Vermelhos" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
