import { Star } from "lucide-react";

interface FavoriteButtonProps {
  isFavorite: boolean;
}

export default function FavoriteButton({ isFavorite }: FavoriteButtonProps) {
  return (
    <Star
      className={`w-4 h-4 ${isFavorite ? "fill-yellow-400 text-yellow-400" : "text-gray-300"}`}
    />
  );
}
