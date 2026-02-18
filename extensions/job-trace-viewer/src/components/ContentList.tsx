import { useEffect, useState } from "react";

import { fetchContent, type ContentItem } from "../api";

interface ContentListProps {
  onSelect: (item: ContentItem) => void;
}

export function ContentList({ onSelect }: ContentListProps) {
  const [items, setItems] = useState<ContentItem[]>([]);
  const [filtered, setFiltered] = useState<ContentItem[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchContent()
      .then((data) => {
        setItems(data);
        setFiltered(data);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Failed to load content");
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    const q = search.toLowerCase();
    setFiltered(
      items.filter(
        (item) =>
          item.title.toLowerCase().includes(q) ||
          item.name.toLowerCase().includes(q) ||
          item.guid.toLowerCase().includes(q),
      ),
    );
  }, [search, items]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-agentprism-muted-foreground">
          Loading content...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 rounded border border-agentprism-error text-agentprism-error">
        {error}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-semibold text-agentprism-foreground mb-1">
          Job Trace Viewer
        </h1>
        <p className="text-sm text-agentprism-muted-foreground">
          Select a content item to view its job traces.
        </p>
      </div>

      <input
        type="text"
        placeholder="Search content..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="w-full px-3 py-2 rounded border border-agentprism-border bg-agentprism-background text-agentprism-foreground placeholder:text-agentprism-muted-foreground focus:outline-none focus:ring-2 focus:ring-agentprism-primary"
      />

      {filtered.length === 0 ? (
        <div className="text-agentprism-muted-foreground text-sm py-8 text-center">
          No content found.
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {filtered.map((item) => (
            <button
              key={item.guid}
              onClick={() => onSelect(item)}
              className="text-left px-4 py-3 rounded border border-agentprism-border bg-agentprism-background hover:bg-agentprism-accent hover:border-agentprism-primary transition-colors cursor-pointer"
            >
              <div className="font-medium text-agentprism-foreground">
                {item.title}
              </div>
              <div className="text-xs text-agentprism-muted-foreground mt-0.5">
                {item.guid}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
