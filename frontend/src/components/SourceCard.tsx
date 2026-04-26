import { ExternalLink, Play } from "lucide-react";
import type { Source } from "../types";

interface Props {
  source: Source;
  index: number;
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export default function SourceCard({ source, index }: Props) {
  const thumbnailUrl = `https://img.youtube.com/vi/${source.video_id}/mqdefault.jpg`;

  return (
    <a
      href={source.url}
      target="_blank"
      rel="noopener noreferrer"
      className="group flex items-start gap-3 p-3 rounded-xl border border-gray-100 bg-white hover:border-brand-200 hover:bg-brand-50/50 transition-all duration-200 shadow-sm hover:shadow-md"
    >
      {/* Thumbnail */}
      <div className="relative flex-shrink-0 w-24 h-[54px] rounded-lg overflow-hidden bg-gray-100">
        <img
          src={thumbnailUrl}
          alt={source.title}
          className="w-full h-full object-cover"
          onError={(e) => {
            (e.target as HTMLImageElement).style.display = "none";
          }}
        />
        <div className="absolute inset-0 flex items-center justify-center bg-black/20 opacity-0 group-hover:opacity-100 transition-opacity">
          <Play className="w-5 h-5 text-white fill-white" />
        </div>
        <div className="absolute bottom-1 right-1 bg-black/70 text-white text-[10px] font-medium px-1 py-0.5 rounded">
          {formatTime(source.start_time)}
        </div>
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <p className="text-xs font-medium text-brand-600 mb-0.5">Source {index}</p>
        <p className="text-sm font-medium text-gray-800 leading-snug line-clamp-2 group-hover:text-brand-700 transition-colors">
          {source.title}
        </p>
        <div className="flex items-center gap-1 mt-1">
          <ExternalLink className="w-3 h-3 text-gray-400 flex-shrink-0" />
          <span className="text-[11px] text-gray-400 truncate">youtube.com</span>
        </div>
      </div>
    </a>
  );
}
