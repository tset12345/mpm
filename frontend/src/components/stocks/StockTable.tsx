import { StockSummary } from "@/lib/types";
import StockRow from "./StockRow";

interface StockTableProps {
  stocks: StockSummary[];
  onRowClick: (code: string) => void;
  isFavorite: (code: string) => boolean;
  onToggleFavorite: (code: string) => void;
}

export default function StockTable({ stocks, onRowClick, isFavorite, onToggleFavorite }: StockTableProps) {
  return (
    <div className="border rounded-lg overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
          <tr>
            <th className="px-4 py-3 text-left">종목명</th>
            <th className="px-4 py-3 text-right">현재가</th>
            <th className="px-4 py-3 text-right">등락률</th>
            <th className="px-4 py-3 text-right">거래량</th>
            <th className="px-4 py-3 text-left">태그</th>
            <th className="px-4 py-3"></th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {stocks.map((s) => (
            <StockRow
              key={s.stock_code}
              stock={s}
              isFavorite={isFavorite(s.stock_code)}
              onClick={() => onRowClick(s.stock_code)}
              onToggleFavorite={() => onToggleFavorite(s.stock_code)}
            />
          ))}
          {stocks.length === 0 && (
            <tr>
              <td colSpan={6} className="px-4 py-12 text-center text-gray-400">
                표시할 종목이 없습니다.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
