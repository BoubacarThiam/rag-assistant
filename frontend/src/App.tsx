import { Menu, Moon, Plus, Sun } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Chat } from "./components/Chat";
import { Sidebar } from "./components/Sidebar";
import { SourcesPanel } from "./components/SourcesPanel";
import { useChat } from "./hooks/useChat";
import { useDocuments } from "./hooks/useDocuments";
import { useTheme } from "./hooks/useTheme";

interface ActiveSources {
  messageId: string;
  index: number | null;
}

export default function App() {
  const { theme, toggle: toggleTheme } = useTheme();
  const docs = useDocuments();
  const chat = useChat();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [activeSources, setActiveSources] = useState<ActiveSources | null>(null);

  const readyIds = useMemo(
    () => new Set(docs.documents.filter((d) => d.status === "ready").map((d) => d.id)),
    [docs.documents],
  );
  // A deleted document must not stay in the filter.
  const documentFilter = useMemo(
    () => [...selectedIds].filter((id) => readyIds.has(id)),
    [selectedIds, readyIds],
  );

  const toggleSelected = useCallback((id: string) => {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const openSources = useCallback((messageId: string, index: number | null) => {
    setActiveSources({ messageId, index });
  }, []);

  const sourcesMessage = activeSources
    ? chat.messages.find((m) => m.id === activeSources.messageId)
    : undefined;

  // Escape closes whichever overlay is open.
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      setActiveSources(null);
      setSidebarOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const iconButton =
    "flex size-11 cursor-pointer items-center justify-center rounded-lg text-muted transition-colors duration-150 hover:bg-surface-2 hover:text-text";

  return (
    <div className="flex h-full overflow-hidden">
      {/* Sidebar: fixed column on desktop, slide-over drawer on mobile */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/40 md:hidden"
          onClick={() => setSidebarOpen(false)}
          aria-hidden
        />
      )}
      <aside
        aria-label="Documents"
        className={`fixed inset-y-0 left-0 z-40 w-80 max-w-[85vw] border-r border-border bg-surface transition-transform duration-200 md:static md:z-auto md:w-72 md:translate-x-0 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <Sidebar
          documents={docs.documents}
          loading={docs.loading}
          uploading={docs.uploading}
          error={docs.error}
          selectedIds={selectedIds}
          onToggleSelected={toggleSelected}
          onUpload={docs.upload}
          onDelete={docs.remove}
          onError={docs.reportError}
          onClose={() => setSidebarOpen(false)}
        />
      </aside>

      <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-2 border-b border-border bg-surface px-3 py-2">
          <button
            type="button"
            onClick={() => setSidebarOpen(true)}
            aria-label="Ouvrir la liste des documents"
            className={`${iconButton} md:hidden`}
          >
            <Menu className="size-5" aria-hidden />
          </button>
          <p className="flex-1 truncate px-1 font-semibold">Assistant RAG</p>
          <button
            type="button"
            onClick={() => {
              chat.reset();
              setActiveSources(null);
            }}
            disabled={chat.messages.length === 0}
            className="flex h-11 cursor-pointer items-center gap-1.5 rounded-lg px-3 text-sm font-medium text-muted transition-colors duration-150 hover:bg-surface-2 hover:text-text disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Plus className="size-4" aria-hidden />
            <span className="hidden sm:inline">Nouvelle conversation</span>
            <span className="sm:hidden">Nouveau</span>
          </button>
          <button
            type="button"
            onClick={toggleTheme}
            aria-label={theme === "dark" ? "Passer en mode clair" : "Passer en mode sombre"}
            className={iconButton}
          >
            {theme === "dark" ? (
              <Sun className="size-5" aria-hidden />
            ) : (
              <Moon className="size-5" aria-hidden />
            )}
          </button>
        </header>

        <Chat
          messages={chat.messages}
          isStreaming={chat.isStreaming}
          hasReadyDocuments={readyIds.size > 0}
          mode={chat.mode}
          onModeChange={chat.setMode}
          onSend={(question) => void chat.send(question, documentFilter, chat.mode)}
          onStop={chat.stop}
          onOpenSources={openSources}
        />
      </main>

      {/* Sources: side column on large screens, slide-over panel below */}
      {sourcesMessage && activeSources && (
        <>
          <div
            className="fixed inset-0 z-30 bg-black/40 lg:hidden"
            onClick={() => setActiveSources(null)}
            aria-hidden
          />
          <aside
            aria-label="Sources de la réponse"
            className="animate-in fixed inset-y-0 right-0 z-40 w-96 max-w-[92vw] border-l border-border bg-bg lg:static lg:z-auto"
          >
            <SourcesPanel
              sources={sourcesMessage.sources}
              activeIndex={activeSources.index}
              onSelect={(index) => setActiveSources({ ...activeSources, index })}
              onClose={() => setActiveSources(null)}
            />
          </aside>
        </>
      )}
    </div>
  );
}
