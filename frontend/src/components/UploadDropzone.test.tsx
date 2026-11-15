import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { MAX_UPLOAD_MB, UploadDropzone, validateFiles } from "./UploadDropzone";

const pdf = (name = "guide.pdf") => new File(["%PDF-1.7"], name, { type: "application/pdf" });

describe("validateFiles", () => {
  it("accepts PDFs and rejects other files or oversized ones", () => {
    expect(validateFiles([pdf(), pdf("AUTRE.PDF")])).toBeNull();
    expect(validateFiles([new File(["x"], "notes.txt")])).toContain("notes.txt");

    const big = pdf("gros.pdf");
    Object.defineProperty(big, "size", { value: (MAX_UPLOAD_MB + 1) * 1024 * 1024 });
    expect(validateFiles([big])).toContain(`${MAX_UPLOAD_MB} Mo`);
  });
});

describe("UploadDropzone", () => {
  it("uploads the files chosen with the file picker", async () => {
    const onUpload = vi.fn();
    render(<UploadDropzone uploading={false} onUpload={onUpload} onError={vi.fn()} />);

    await userEvent.upload(screen.getByLabelText("Importer des fichiers PDF"), [pdf(), pdf("b.pdf")]);

    expect(onUpload).toHaveBeenCalledOnce();
    expect(onUpload.mock.calls[0]![0]).toHaveLength(2);
  });

  it("uploads dropped files", () => {
    const onUpload = vi.fn();
    render(<UploadDropzone uploading={false} onUpload={onUpload} onError={vi.fn()} />);

    fireEvent.drop(screen.getByRole("button"), { dataTransfer: { files: [pdf()] } });

    expect(onUpload).toHaveBeenCalledOnce();
  });

  it("reports an error instead of uploading a non-PDF", () => {
    const onUpload = vi.fn();
    const onError = vi.fn();
    render(<UploadDropzone uploading={false} onUpload={onUpload} onError={onError} />);

    fireEvent.drop(screen.getByRole("button"), {
      dataTransfer: { files: [new File(["x"], "photo.png", { type: "image/png" })] },
    });

    expect(onUpload).not.toHaveBeenCalled();
    expect(onError).toHaveBeenCalledWith(expect.stringContaining("photo.png"));
  });

  it("is disabled while an upload is running", () => {
    render(<UploadDropzone uploading onUpload={vi.fn()} onError={vi.fn()} />);
    expect(screen.getByRole("button")).toBeDisabled();
    expect(screen.getByText("Envoi en cours…")).toBeInTheDocument();
  });
});
