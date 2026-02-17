import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { API_BASE } from "@/lib/utils";
import { Plus, Trash2, Pencil } from "lucide-react";

interface Source {
  id: string;
  platform: string;
  url: string;
  status: string;
}

interface Topic {
  id: string;
  keyword: string;
  description: string | null;
}

function StatusBadge({
  label,
  ok,
  hint = "",
}: {
  label: string;
  ok: boolean;
  hint?: string;
}) {
  return (
    <div className="flex items-center gap-2">
      <span
        className={`inline-flex h-2 w-2 rounded-full ${ok ? "bg-green-500" : "bg-muted"}`}
        title={hint || (ok ? "OK" : "Выкл")}
      />
      <span className="text-sm">{label}</span>
      {hint && <span className="text-xs text-muted-foreground">({hint})</span>}
    </div>
  );
}

const PLATFORMS: { value: string; label: string }[] = [
  { value: "tiktok", label: "TikTok" },
  { value: "reels", label: "Reels (Instagram)" },
  { value: "shorts", label: "Shorts (YouTube)" },
];

export default function SettingsPage() {
  const [sources, setSources] = useState<Source[]>([]);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [configStatus, setConfigStatus] = useState<Record<string, boolean> | null>(null);
  const [parserConfig, setParserConfig] = useState<Record<string, number> | null>(null);
  const [loading, setLoading] = useState(true);

  const loadData = () => {
    Promise.all([
      fetch(`${API_BASE}/sources`).then((r) => r.json()),
      fetch(`${API_BASE}/topics`).then((r) => r.json()),
      fetch(`${API_BASE}/config/status`).then((r) => r.json()),
      fetch(`${API_BASE}/config/parser`).then((r) => r.json()),
    ])
      .then(([s, t, cfg, parser]) => {
        setSources(s);
        setTopics(t);
        setConfigStatus(cfg);
        setParserConfig(parser);
      })
      .finally(() => setLoading(false));
  };

  useEffect(loadData, []);

  const deleteSource = (id: string) => {
    fetch(`${API_BASE}/sources/${id}`, { method: "DELETE" }).then(() => loadData());
  };

  const deleteTopic = (id: string) => {
    fetch(`${API_BASE}/topics/${id}`, { method: "DELETE" }).then(() => loadData());
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-muted-foreground">Загрузка настроек…</div>
      </div>
    );
  }

  return (
    <div className="space-y-10">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Настройки</h2>
        <p className="text-muted-foreground">
          Управление источниками и темами для отслеживания трендов.
        </p>
      </div>

      {/* Parser settings */}
      {parserConfig && (
        <Card>
          <CardHeader>
            <CardTitle>Парсер</CardTitle>
            <CardDescription>
              Лимиты и таймауты. Меняются в .env: MAX_RESULTS_PER_PLATFORM, REQUEST_TIMEOUT, RETRY_COUNT, APIFY_TIMEOUT_SECS
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="text-muted-foreground">Лимит на платформу</span>
                <p className="font-medium">{parserConfig.max_results_per_platform ?? 20}</p>
              </div>
              <div>
                <span className="text-muted-foreground">Таймаут (сек)</span>
                <p className="font-medium">{parserConfig.request_timeout ?? 30}</p>
              </div>
              <div>
                <span className="text-muted-foreground">Повторов</span>
                <p className="font-medium">{parserConfig.retry_count ?? 3}</p>
              </div>
              <div>
                <span className="text-muted-foreground">Apify таймаут (сек)</span>
                <p className="font-medium">{parserConfig.apify_timeout_secs ?? 60}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Config status */}
      {configStatus && (
        <Card>
          <CardHeader>
            <CardTitle>Статус интеграций</CardTitle>
            <CardDescription>Текущие настройки приложения (меняются в .env)</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-4">
              <StatusBadge label="YouTube" ok={configStatus.youtube} />
              <StatusBadge label="Apify (TikTok, Reels)" ok={configStatus.apify} />
              <StatusBadge label="Google Таблицы" ok={configStatus.google_sheets} />
              <StatusBadge label="DRY_RUN" ok={!configStatus.dry_run} hint={configStatus.dry_run ? "запись отключена" : ""} />
              <StatusBadge label="DEBUG" ok={configStatus.debug} hint={configStatus.debug ? "включён" : ""} />
            </div>
          </CardContent>
        </Card>
      )}

      {/* Sources */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Источники</CardTitle>
            <CardDescription>Каналы или профили для мониторинга коротких видео.</CardDescription>
          </div>
          <AddSourceDialog onAdded={loadData} />
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Платформа</TableHead>
                <TableHead>URL</TableHead>
                <TableHead>Статус</TableHead>
                <TableHead className="w-[120px]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sources.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={4} className="text-center text-muted-foreground py-8">
                    Нет источников. Добавьте первый.
                  </TableCell>
                </TableRow>
              ) : (
                sources.map((s) => (
                  <TableRow key={s.id}>
                    <TableCell className="font-medium">
                      {PLATFORMS.find((p) => p.value === s.platform)?.label ?? s.platform}
                    </TableCell>
                    <TableCell className="max-w-[300px] truncate">{s.url}</TableCell>
                    <TableCell>
                      <Button
                        variant={s.status === "active" ? "default" : "outline"}
                        size="sm"
                        onClick={() =>
                          fetch(`${API_BASE}/sources/${s.id}`, {
                            method: "PATCH",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({ status: s.status === "active" ? "inactive" : "active" }),
                          }).then(() => loadData())
                        }
                      >
                        {s.status === "active" ? "Активен" : "Неактивен"}
                      </Button>
                    </TableCell>
                    <TableCell className="flex gap-1">
                      <EditSourceDialog source={s} onSaved={loadData} />
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => deleteSource(s.id)}
                        className="text-destructive hover:text-destructive"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Topics */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Темы</CardTitle>
            <CardDescription>Ключевые слова и темы для поиска вирусного контента ИИ.</CardDescription>
          </div>
          <AddTopicDialog onAdded={loadData} />
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Ключевое слово</TableHead>
                <TableHead>Описание</TableHead>
                <TableHead className="w-[120px]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {topics.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={3} className="text-center text-muted-foreground py-8">
                    Нет тем. Добавьте хотя бы одну для анализа видео.
                  </TableCell>
                </TableRow>
              ) : (
                topics.map((t) => (
                  <TableRow key={t.id}>
                    <TableCell className="font-medium">{t.keyword}</TableCell>
                    <TableCell className="max-w-[400px] truncate">
                      {t.description || "—"}
                    </TableCell>
                    <TableCell className="flex gap-1">
                      <EditTopicDialog topic={t} onSaved={loadData} />
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => deleteTopic(t.id)}
                        className="text-destructive hover:text-destructive"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}

function EditSourceDialog({ source, onSaved }: { source: Source; onSaved: () => void }) {
  const [open, setOpen] = useState(false);
  const [platform, setPlatform] = useState(source.platform);
  const [url, setUrl] = useState(source.url);
  const [submitting, setSubmitting] = useState(false);
  useEffect(() => {
    if (open) {
      setPlatform(source.platform);
      setUrl(source.url);
    }
  }, [open, source.platform, source.url]);

  const submit = () => {
    if (!url.trim()) return;
    setSubmitting(true);
    fetch(`${API_BASE}/sources/${source.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ platform, url: url.trim() }),
    })
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then(() => {
        setOpen(false);
        onSaved();
      })
      .finally(() => setSubmitting(false));
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="icon">
          <Pencil className="h-4 w-4" />
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Редактировать источник</DialogTitle>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <Label>Платформа</Label>
            <Select value={platform} onValueChange={setPlatform}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PLATFORMS.map((p) => (
                  <SelectItem key={p.value} value={p.value}>
                    {p.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-2">
            <Label>URL</Label>
            <Input value={url} onChange={(e) => setUrl(e.target.value)} />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Отмена
          </Button>
          <Button onClick={submit} disabled={submitting || !url.trim()}>
            Сохранить
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function EditTopicDialog({ topic, onSaved }: { topic: Topic; onSaved: () => void }) {
  const [open, setOpen] = useState(false);
  const [keyword, setKeyword] = useState(topic.keyword);
  const [description, setDescription] = useState(topic.description || "");
  const [submitting, setSubmitting] = useState(false);
  useEffect(() => {
    if (open) {
      setKeyword(topic.keyword);
      setDescription(topic.description || "");
    }
  }, [open, topic.keyword, topic.description]);

  const submit = () => {
    if (!keyword.trim()) return;
    setSubmitting(true);
    fetch(`${API_BASE}/topics/${topic.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        keyword: keyword.trim(),
        description: description.trim() || null,
      }),
    })
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then(() => {
        setOpen(false);
        onSaved();
      })
      .finally(() => setSubmitting(false));
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="icon">
          <Pencil className="h-4 w-4" />
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Редактировать тему</DialogTitle>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <Label>Ключевое слово</Label>
            <Input value={keyword} onChange={(e) => setKeyword(e.target.value)} />
          </div>
          <div className="grid gap-2">
            <Label>Описание (необязательно)</Label>
            <Input value={description} onChange={(e) => setDescription(e.target.value)} />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Отмена
          </Button>
          <Button onClick={submit} disabled={submitting || !keyword.trim()}>
            Сохранить
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function AddSourceDialog({ onAdded }: { onAdded: () => void }) {
  const [open, setOpen] = useState(false);
  const [platform, setPlatform] = useState("shorts");
  const [url, setUrl] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const submit = () => {
    if (!url.trim()) return;
    setSubmitting(true);
    fetch(`${API_BASE}/sources`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ platform, url: url.trim(), status: "active" }),
    })
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then(() => {
        setOpen(false);
        setUrl("");
        onAdded();
      })
      .finally(() => setSubmitting(false));
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm">
          <Plus className="h-4 w-4 mr-2" />
          Добавить источник
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Добавить источник</DialogTitle>
          <DialogDescription>
            URL канала или профиля для мониторинга коротких видео.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <Label>Платформа</Label>
            <Select value={platform} onValueChange={setPlatform}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PLATFORMS.map((p) => (
                  <SelectItem key={p.value} value={p.value}>
                    {p.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-2">
            <Label>URL</Label>
            <Input
              placeholder={
                platform === "shorts"
                  ? "https://youtube.com/@username или /channel/UC..."
                  : platform === "tiktok"
                    ? "https://tiktok.com/@username"
                    : platform === "reels"
                      ? "https://instagram.com/username"
                      : "https://..."
              }
              value={url}
              onChange={(e) => setUrl(e.target.value)}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Отмена
          </Button>
          <Button onClick={submit} disabled={submitting || !url.trim()}>
            Добавить
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function AddTopicDialog({ onAdded }: { onAdded: () => void }) {
  const [open, setOpen] = useState(false);
  const [keyword, setKeyword] = useState("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const submit = () => {
    if (!keyword.trim()) return;
    setSubmitting(true);
    fetch(`${API_BASE}/topics`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        keyword: keyword.trim(),
        description: description.trim() || null,
      }),
    })
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then(() => {
        setOpen(false);
        setKeyword("");
        setDescription("");
        onAdded();
      })
      .finally(() => setSubmitting(false));
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm">
          <Plus className="h-4 w-4 mr-2" />
          Добавить тему
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Добавить тему</DialogTitle>
          <DialogDescription>
            Ключевое слово и описание для поиска подходящих видео ИИ.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <Label>Ключевое слово</Label>
            <Input
              placeholder="например: Технологии, Юмор"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
            />
          </div>
          <div className="grid gap-2">
            <Label>Описание (необязательно)</Label>
            <Input
              placeholder="например: Технологии и гаджеты"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Отмена
          </Button>
          <Button onClick={submit} disabled={submitting || !keyword.trim()}>
            Добавить
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
