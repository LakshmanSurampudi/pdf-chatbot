"use client";

import { useEffect, useState } from "react";

import { deleteDocument, DocumentItem, listDocuments, uploadDocument } from "@/lib/api";

interface Props {
  selectedIds: string[];
  onSelectionChange: (ids: string[]) => void;
}

export default function DocumentSidebar({ selectedIds, onSelectionChange }: Props) {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    setDocuments(await listDocuments());
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- one-time fetch of document list on mount
    refresh();
  }, []);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 50 * 1024 * 1024) {
      setError("File exceeds 50MB limit");
      return;
    }
    setUploading(true);
    setError(null);
    try {
      const doc = await uploadDocument(file);
      setDocuments((prev) => [doc, ...prev]);
      onSelectionChange([...selectedIds, doc.id]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  }

  async function handleDelete(id: string) {
    await deleteDocument(id);
    setDocuments((prev) => prev.filter((d) => d.id !== id));
    onSelectionChange(selectedIds.filter((s) => s !== id));
  }

  function toggle(id: string) {
    onSelectionChange(
      selectedIds.includes(id) ? selectedIds.filter((s) => s !== id) : [...selectedIds, id]
    );
  }

  return (
    <aside className="flex w-80 flex-col gap-3 border-r bg-gray-50 p-4">
      <h2 className="font-semibold">Documents</h2>
      <label className="cursor-pointer rounded border border-dashed border-gray-400 p-4 text-center text-sm text-gray-600 hover:bg-gray-100">
        {uploading ? "Uploading..." : "Click to upload a PDF (max 50MB)"}
        <input type="file" accept="application/pdf" className="hidden" onChange={handleUpload} disabled={uploading} />
      </label>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <ul className="flex-1 space-y-2 overflow-y-auto">
        {documents.map((doc) => (
          <li
            key={doc.id}
            className={`flex items-center justify-between rounded border p-2 text-sm ${
              selectedIds.includes(doc.id) ? "border-black bg-white" : "border-gray-200"
            }`}
          >
            <label className="flex flex-1 cursor-pointer items-center gap-2 overflow-hidden">
              <input
                type="checkbox"
                checked={selectedIds.includes(doc.id)}
                onChange={() => toggle(doc.id)}
              />
              <span className="truncate" title={doc.filename}>
                {doc.filename}
              </span>
              <span className="text-xs text-gray-500">{doc.page_count}p</span>
            </label>
            <button
              onClick={() => handleDelete(doc.id)}
              className="ml-2 text-xs text-red-500 hover:underline"
            >
              delete
            </button>
          </li>
        ))}
      </ul>
    </aside>
  );
}
