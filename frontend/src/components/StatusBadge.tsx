import { Database, AlertCircle, Loader2 } from "lucide-react";
import type { StatusResponse } from "../types";

interface Props {
  status: StatusResponse | null;
  loading: boolean;
}

export default function StatusBadge({ status, loading }: Props) {
  if (loading) {
    return (
      <div className="flex items-center gap-1.5 text-xs text-gray-400">
        <Loader2 className="w-3 h-3 animate-spin" />
        Checking index…
      </div>
    );
  }

  if (!status || !status.indexed) {
    return (
      <div className="flex items-center gap-1.5 text-xs text-amber-600 bg-amber-50 border border-amber-200 px-2.5 py-1 rounded-full">
        <AlertCircle className="w-3 h-3" />
        No videos indexed — run the ingest script
      </div>
    );
  }

  return (
    <div className="flex items-center gap-1.5 text-xs text-brand-700 bg-brand-50 border border-brand-200 px-2.5 py-1 rounded-full">
      <Database className="w-3 h-3" />
      {status.video_count} videos · {status.chunk_count.toLocaleString()} chunks indexed
    </div>
  );
}
