import { StockSummary } from "@/lib/types";
import FavoriteButton from "./FavoriteButton";

interface StockRowProps {
  stock: StockSummary;
  isFavorite: boolean;
  onClick: () => void;
  onToggleFavorite: () => void;
}

export default function StockRow({ stock, isFavorite, onClick, onToggleFavorite }: StockRowProps) {
  return (
    <tr className="hover:bg-gray-50 cursor-pointer" onClick={onClick}>
      <td className="px-4 py-3">
        <div className="font-medium">{stock.stock_name}</div>
        <div className="text-gray-400 text-xs">{stock.stock_code}</div>
      </td>
      <td className="px-4 py-3 text-right font-mono">{stock.current_price?.toLocaleString() ?? "-"}</td>
      <td className={`px-4 py-3 text-right font-mono ${(stock.change_rate ?? 0) >= 0 ? "text-red-500" : "text-blue-500"}`}>
        {stock.change_rate != null ? `${stock.change_rate >= 0 ? "+" : ""}${stock.change_rate.toFixed(2)}%` : "-"}
      </td>
      <td className="px-4 py-3 text-right font-mono text-gray-500">{stock.volume?.toLocaleString() ?? "-"}</td>
      <td className="px-4 py-3">
        <div className="flex gap-1 flex-wrap">
          {stock.tags.map((tag) => (
            <span key={tag} className="bg-blue-50 text-blue-700 text-xs px-2 py-0.5 rounded-full">
              {tag}
            </span>
          ))}
        </div>
      </td>
      <td className="px-4 py-3" onClick={(e) => { e.stopPropagation(); onToggleFavorite(); }}>
        <FavoriteButton isFavorite={isFavorite} />
      </td>
    </tr>
  );
}
