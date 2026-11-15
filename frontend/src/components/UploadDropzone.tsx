import { Loader2, UploadCloud } from "lucide-react";
import { useRef, useState, type DragEvent } from "react";

export const MAX_UPLOAD_MB = 20;

interface Props {
  uploading: boolean;
  onUpload: (files: File[]) => void;
  onError: (message: string) => void;
}

/** Client-side checks give instant feedback; the server validates again (it is the authority). */
export function validateFiles(files: File[]): string | null {
  for (const file of files) {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      return `« ${file.name} » n'est pas un PDF.`;
    }
    if (file.size > MAX_UPLOAD_MB * 1024 * 1024) {
      return `« ${file.name} » dépasse ${MAX_UPLOAD_MB} Mo.`;
    }
  }
  return null;
}

export function UploadDropzone({ uploading, onUpload, onError }: Props) {
  const [dragging, setDragging] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  function handleFiles(list: FileList | null) {
    const files = Array.from(list ?? []);
    if (files.length === 0) return;
    const problem = validateFiles(files);
    if (problem) onError(problem);
    else onUpload(files);
  }

  function onDrop(event: DragEvent) {
    event.preventDefault();
    setDragging(false);
    if (!uploading) handleFiles(event.dataTransfer.files);
  }

  return (
    <div
      onDragOver={(event) => {
        event.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
    >
      <button
        type="button"
        disabled={uploading}
        onClick={() => input.current?.click()}
        className={`flex w-full cursor-pointer flex-col items-center gap-1.5 rounded-xl border-2 border-dashed px-4 py-5 text-center transition-colors duration-200 disabled:cursor-wait ${
          dragging
            ? "border-primary bg-primary-soft text-on-primary-soft"
            : "border-border text-muted hover:border-primary hover:text-text"
        }`}
      >
        {uploading ? (
          <Loader2 className="size-6 animate-spin" aria-hidden />
        ) : (
          <UploadCloud className="size-6" aria-hidden />
        )}
        <span className="text-sm font-medium text-text">
          {uploading ? "Envoi en cours…" : "Glissez vos PDF ici"}
        </span>
        <span className="text-xs">ou cliquez pour parcourir · {MAX_UPLOAD_MB} Mo max</span>
      </button>
      <input
        ref={input}
        type="file"
        accept="application/pdf,.pdf"
        multiple
        hidden
        aria-label="Importer des fichiers PDF"
        onChange={(event) => {
          handleFiles(event.target.files);
          event.target.value = ""; // allow re-selecting the same file
        }}
      />
    </div>
  );
}
