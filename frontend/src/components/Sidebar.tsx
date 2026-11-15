import { AlertCircle, FileText, Loader2, Trash2, X } from "lucide-react";
import { formatSize, pluralize } from "../lib/format";
import type { DocumentInfo } from "../types";
import { UploadDropzone } from "./UploadDropzone";

interface Props {
  documents: DocumentInfo[];
  loading: boolean;
  uploading: boolean;
  error: string | null;
  selectedIds: Set<string>;
  onToggleSelected: (id: string) => void;
  onUpload: (files: File[]) => void;
  onDelete: (id: string) => void;
  onError: (message: string | null) => void;
  onClose: () => void;
}

function DocumentRow({
  document,
  selected,
  onToggle,
  onDelete,
}: {
  document: DocumentInfo;
  selected: boolean;
  onToggle: () => void;
  onDelete: () => void;
}) {
  const ready = document.status === "ready";
  return (
    <li className="group flex items-start gap-2.5 rounded-lg px-2 py-2 transition-colors duration-150 hover:bg-surface-2">
      {ready ? (
        <input
          type="checkbox"
          checked={selected}
          onChange={onToggle}
          aria-label={`Limiter la recherche à ${document.filename}`}
          className="mt-1 size-4 cursor-pointer accent-primary"
        />
      ) : document.status === "processing" ? (
        <Loader2 className="mt-0.5 size-4 shrink-0 animate-spin text-primary" aria-hidden />
      ) : (
        <AlertCircle className="mt-0.5 size-4 shrink-0 text-danger" aria-hidden />
      )}

      <div className="min-w-0 flex-1">
        <p className="flex items-center gap-1.5 truncate text-sm font-medium" title={document.filename}>
          <FileText className="size-3.5 shrink-0 text-muted" aria-hidden />
          <span className="truncate">{document.filename}</span>
        </p>
        {ready && (
          <p className="text-xs text-muted">
            {pluralize(document.page_count ?? 0, "page")} · {formatSize(document.size_bytes)}
          </p>
        )}
        {document.status === "processing" && (
          <p className="text-xs text-primary">Traitement en cours…</p>
        )}
        {document.status === "error" && (
          <p className="text-xs text-danger">{document.error_message ?? "Échec du traitement."}</p>
        )}
      </div>

      <button
        type="button"
        onClick={() => {
          if (window.confirm(`Supprimer « ${document.filename} » ?`)) onDelete();
        }}
        aria-label={`Supprimer ${document.filename}`}
        className="cursor-pointer rounded-md p-1.5 text-muted transition-colors duration-150 hover:bg-danger-soft hover:text-danger md:opacity-0 md:group-hover:opacity-100 md:focus-visible:opacity-100"
      >
        <Trash2 className="size-4" aria-hidden />
      </button>
    </li>
  );
}

export function Sidebar({
  documents,
  loading,
  uploading,
  error,
  selectedIds,
  onToggleSelected,
  onUpload,
  onDelete,
  onError,
  onClose,
}: Props) {
  const selectedCount = documents.filter((d) => selectedIds.has(d.id)).length;

  return (
    <div className="flex h-full flex-col gap-4 p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">Documents</h2>
        <button
          type="button"
          onClick={onClose}
          aria-label="Fermer le menu"
          className="cursor-pointer rounded-md p-2 text-muted hover:bg-surface-2 md:hidden"
        >
          <X className="size-5" aria-hidden />
        </button>
      </div>

      <UploadDropzone uploading={uploading} onUpload={onUpload} onError={onError} />

      {error && (
        <div
          role="alert"
          className="flex items-start gap-2 rounded-lg bg-danger-soft px-3 py-2 text-sm text-danger"
        >
          <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden />
          <p className="flex-1">{error}</p>
          <button
            type="button"
            onClick={() => onError(null)}
            aria-label="Fermer le message d'erreur"
            className="cursor-pointer rounded p-0.5 hover:opacity-70"
          >
            <X className="size-4" aria-hidden />
          </button>
        </div>
      )}

      <div className="min-h-0 flex-1 overflow-y-auto">
        {loading ? (
          <p className="px-2 text-sm text-muted">Chargement…</p>
        ) : documents.length === 0 ? (
          <p className="px-2 text-sm text-muted">
            Aucun document pour l'instant. Importez un PDF pour commencer à poser des questions.
          </p>
        ) : (
          <ul className="flex flex-col gap-0.5">
            {documents.map((document) => (
              <DocumentRow
                key={document.id}
                document={document}
                selected={selectedIds.has(document.id)}
                onToggle={() => onToggleSelected(document.id)}
                onDelete={() => onDelete(document.id)}
              />
            ))}
          </ul>
        )}
      </div>

      {documents.length > 0 && (
        <p className="border-t border-border pt-3 text-xs text-muted">
          {selectedCount === 0
            ? "La recherche porte sur tous les documents. Cochez-en pour la restreindre."
            : `Recherche limitée à ${pluralize(selectedCount, "document")}.`}
        </p>
      )}
    </div>
  );
}
