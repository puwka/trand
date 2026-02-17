import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { API_BASE } from "@/lib/utils";
import { Play, ExternalLink, FileSpreadsheet, Trash2 } from "lucide-react";

interface Video {
  id: string;
  source_id: string;
  external_id: string;
  title: string;
  description: string | null;
  ai_summary: string | null;
  virality_score: number;
  is_viral: boolean;
  storage_path: string | null;
  created_at: string;
}

function getVideoUrl(v: Video): string {
  if (v.storage_path && (v.storage_path.startsWith("http") || v.storage_path.startsWith("https"))) {
    return v.storage_path;
  }
  if (v.external_id.includes(":")) {
    const [platform, id] = v.external_id.split(":", 2);
    if (platform === "youtube" && id?.length === 11) {
      return `https://www.youtube.com/watch?v=${id}`;
    }
    if (platform === "tiktok") {
      return `https://www.tiktok.com/@_/video/${id}`;
    }
  }
  if (v.external_id?.length === 11) {
    return `https://www.youtube.com/watch?v=${v.external_id}`;
  }
  return v.storage_path || "#";
}

export default function Dashboard() {
  const [videos, setVideos] = useState<Video[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [parsing, setParsing] = useState(false);
  const [parseResult, setParseResult] = useState<string | null>(null);
  const [autoParsing, setAutoParsing] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exportResult, setExportResult] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const loadVideos = () => {
    setLoading(true);
    setError(null);
    fetch(`${API_BASE}/videos/all`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error("Ошибка загрузки"))))
      .then(setVideos)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(loadVideos, []);

  useEffect(() => {
    const check = () => {
      fetch(`${API_BASE}/parse-now/status`)
        .then((r) => (r.ok ? r.json() : {}))
        .then((data) => setAutoParsing(data.running === true))
        .catch(() => {});
    };
    check();
    const id = setInterval(check, 2000);
    return () => clearInterval(id);
  }, []);

  const handleParseNow = () => {
    setParsing(true);
    setParseResult(null);
    setError(null);
    fetch(`${API_BASE}/parse-now`, { method: "POST" })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error("Ошибка парсинга"))))
      .then((data) => {
        if (data.ok === false) {
          setError(data.message || "Ошибка парсинга");
          setParseResult(null);
        } else {
          setError(null);
          setParseResult(data.message || "Готово");
          loadVideos();
        }
      })
      .catch((e) => setError(e.message))
      .finally(() => setParsing(false));
  };

  const handleDeleteVideo = (id: string) => {
    if (!confirm("Удалить это видео из списка?")) return;
    setDeletingId(id);
    fetch(`${API_BASE}/videos/${id}`, { method: "DELETE" })
      .then((r) => (r.ok ? undefined : Promise.reject(new Error("Ошибка удаления"))))
      .then(() => loadVideos())
      .catch((e) => setError(e.message))
      .finally(() => setDeletingId(null));
  };

  const handleExportToSheets = () => {
    setExporting(true);
    setExportResult(null);
    setError(null);
    fetch(`${API_BASE}/export/google-sheets`, { method: "POST" })
      .then((r) => r.json().then((data) => ({ ok: r.ok, data })))
      .then(({ ok, data }) => {
        if (ok) setExportResult(data.message || "Выгружено");
        else throw new Error(data.detail || data.message || "Ошибка выгрузки");
      })
      .catch((e) => setError(e.message))
      .finally(() => setExporting(false));
  };

  if (loading && videos.length === 0) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-muted-foreground">Загрузка видео…</div>
      </div>
    );
  }

  if (error && videos.length === 0) {
    return (
      <Card className="border-destructive">
        <CardContent className="pt-6">
          <p className="text-destructive">Ошибка: {error}</p>
          <p className="text-sm text-muted-foreground mt-2">
            Убедитесь, что бэкенд запущен на порту 8000.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Видео</h2>
          <p className="text-muted-foreground">
            Собрано из источников. Ссылки ведут на оригинал.
          </p>
        </div>
        <div className="flex gap-2 shrink-0">
          <Button
            variant="outline"
            onClick={handleExportToSheets}
            disabled={exporting || videos.length === 0}
          >
            <FileSpreadsheet className="h-4 w-4 mr-2" />
            {exporting ? "Выгрузка…" : "В Google Таблицы"}
          </Button>
          <Button onClick={handleParseNow} disabled={parsing || autoParsing}>
            <Play className="h-4 w-4 mr-2" />
            {parsing ? "Парсинг…" : autoParsing ? "Автопарсинг…" : "Парсить сейчас"}
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 px-4 py-2 text-sm text-destructive">
          {error}
        </div>
      )}

      {(parseResult || exportResult) && (
        <div className="rounded-lg border border-border bg-muted/50 px-4 py-2 text-sm text-muted-foreground">
          {[parseResult, exportResult].filter(Boolean).join(" | ")}
        </div>
      )}

      {videos.length === 0 ? (
        <Card>
          <CardContent className="py-16 text-center">
            <p className="text-muted-foreground">
              Пока нет видео. Добавьте <strong>источники</strong> и <strong>темы</strong> в
              Настройках, затем нажмите «Парсить сейчас».
            </p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>Список видео</CardTitle>
            <CardDescription>Ссылка, название, описание, оценка</CardDescription>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="min-w-[180px]">Ссылка</TableHead>
                  <TableHead className="min-w-[280px]">Название</TableHead>
                  <TableHead className="min-w-[300px]">Описание</TableHead>
                <TableHead className="w-[100px]">Оценка</TableHead>
                <TableHead className="w-[150px]">Дата</TableHead>
                <TableHead className="w-[60px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {videos.map((v) => {
                  const url = getVideoUrl(v);
                  const urlShort =
                    url.length > 50 ? url.slice(0, 47) + "…" : url;
                  return (
                    <TableRow key={v.id}>
                      <TableCell className="align-top">
                        <a
                          href={url}
                          target="_blank"
                          rel="noreferrer"
                          title={url}
                          className="inline-flex items-center gap-1.5 text-primary hover:underline break-all font-mono text-sm"
                        >
                          <ExternalLink className="h-3.5 w-3.5 shrink-0" />
                          {urlShort}
                        </a>
                      </TableCell>
                      <TableCell className="align-top font-medium">
                        <span
                          className="block line-clamp-2"
                          title={v.title || undefined}
                        >
                          {v.title || "—"}
                        </span>
                      </TableCell>
                      <TableCell className="align-top text-muted-foreground text-sm">
                        <span
                          className="block line-clamp-3"
                          title={(v.description || v.ai_summary) || undefined}
                        >
                          {v.description || v.ai_summary || "—"}
                        </span>
                      </TableCell>
                      <TableCell className="align-top">
                        <div className="flex flex-wrap items-center gap-1.5">
                          <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-medium">
                            {v.virality_score}/10
                          </span>
                          {v.is_viral && (
                            <span className="rounded-full bg-primary/20 text-primary px-2 py-0.5 text-xs">
                              вирусное
                            </span>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="align-top text-muted-foreground text-sm whitespace-nowrap">
                        {new Date(v.created_at).toLocaleString("ru-RU")}
                      </TableCell>
                      <TableCell className="align-top">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDeleteVideo(v.id)}
                          disabled={deletingId === v.id}
                          className="text-destructive hover:text-destructive hover:bg-destructive/10"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
