import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, deleteDocument, listDocuments, uploadDocuments } from "../lib/api";
import type { DocumentInfo } from "../types";

const POLL_INTERVAL_MS = 2000;

function messageOf(error: unknown): string {
  return error instanceof ApiError ? error.message : "Une erreur inattendue est survenue.";
}

export function useDocuments() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const mounted = useRef(true);

  const refresh = useCallback(async () => {
    try {
      const list = await listDocuments();
      if (mounted.current) setDocuments(list);
    } catch (e) {
      if (mounted.current) setError(messageOf(e));
    } finally {
      if (mounted.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    mounted.current = true;
    void refresh();
    return () => {
      mounted.current = false;
    };
  }, [refresh]);

  // Ingestion runs in the background on the server: while a document is "processing",
  // ask for the list again every 2 s until its status changes.
  const hasProcessing = documents.some((d) => d.status === "processing");
  useEffect(() => {
    if (!hasProcessing) return;
    const timer = setInterval(() => void refresh(), POLL_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [hasProcessing, refresh]);

  const upload = useCallback(async (files: File[]) => {
    setUploading(true);
    setError(null);
    try {
      const created = await uploadDocuments(files);
      setDocuments((current) => [...created, ...current]);
    } catch (e) {
      setError(messageOf(e));
    } finally {
      setUploading(false);
    }
  }, []);

  const remove = useCallback(async (id: string) => {
    setError(null);
    try {
      await deleteDocument(id);
      setDocuments((current) => current.filter((d) => d.id !== id));
    } catch (e) {
      setError(messageOf(e));
    }
  }, []);

  const reportError = useCallback((message: string | null) => setError(message), []);

  return { documents, loading, uploading, error, upload, remove, reportError };
}
